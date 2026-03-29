"""
Adaptive Runner — Hardware-aware execution engine for the War Room analysis pipeline.

Supports two execution modes controlled by src.config.EXECUTION_MODE:

  cloud (default): Calls OpenAI GPT-4o. First three analysts run in PARALLEL via
                   asyncio.gather — no GPU constraints, no thermal pauses.

  dgx:             Runs local Ollama on the DGX Spark. Three execution tiers
                   selected based on real-time GPU telemetry:

    Tier 2 (Sequential): 1 model at a time via Ollama with cooling pauses.
                          Uses qwen3:32b. Default for healthy DGX Spark.
    Tier 3 (Micro):       Ultra-conservative — halved context, llama3.1:8b, 60s cooling.
                          Used when GPU temp >= 65°C or RAM >= 60%.

Key safety properties (DGX mode only):
  - All models are unloaded before starting (ollama_stop_all)
  - GPU temp is checked before every round; execution blocks until THERMAL_RESUME_C
  - Context is trimmed to MAX_CONTEXT_CHARS before any inference call

Universal:
  - Deliverable is persisted to disk before returning
  - Execution metadata (mode, model, timing, GPU temps) embedded in deliverable.json

Env vars:
  WAR_ROOM_MODE            — "cloud" (default) or "dgx"
  OPENAI_API_KEY           — Required in cloud mode
  OLLAMA_URL               — Ollama completions endpoint (default: localhost:11434/v1/...)
  WAR_ROOM_MODEL           — DGX Tier 2 model tag (default: qwen3:32b)
  WAR_ROOM_FALLBACK_MODEL  — DGX Tier 3 model tag (default: llama3.1:8b)
  THERMAL_CEILING          — Block inference above this °C (default: 70)
  THERMAL_RESUME           — Resume inference below this °C (default: 55)
  COOLDOWN_SECONDS         — Inter-round pause in seconds (default: 30)
  MAX_CONTEXT_CHARS        — Max chars per evidence block (default: 8000)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import aiohttp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://localhost:11434/v1/chat/completions"
)
PREFERRED_MODEL = os.environ.get("WAR_ROOM_MODEL", "qwen3:32b")
FALLBACK_MODEL = os.environ.get("WAR_ROOM_FALLBACK_MODEL", "llama3.1:8b")
THERMAL_CEILING = int(os.environ.get("THERMAL_CEILING", "70"))
THERMAL_RESUME = int(os.environ.get("THERMAL_RESUME", "55"))
COOLDOWN_SECONDS = int(os.environ.get("COOLDOWN_SECONDS", "30"))
MAX_CONTEXT_CHARS = int(os.environ.get("MAX_CONTEXT_CHARS", "8000"))

# Models that may be loaded by other parts of the system — unload all before
# starting to prevent cumulative VRAM pressure.
_KNOWN_MODELS = [
    "llama3.3:70b",
    "qwen3:32b",
    "mistral-small:24b",
    "llama3.1:8b",
    "llava:7b",
    "llama3.2-vision:11b",
    "llama3.3:60b",
]


# ---------------------------------------------------------------------------
# Output normalizers — map model field names to frontend schema
# ---------------------------------------------------------------------------


def normalize_strategist(output: dict[str, Any]) -> dict[str, Any]:
    """Remap alternate field names the model may use to the canonical schema."""
    mapping = {
        "market_position": "competitive_positioning",
        "key_risks": "top_risks",
        "key_strengths": "top_strengths",
        "competitive_gaps": "top_opportunities",
        "strategic_summary": "strategist_summary",
        "market_readiness_score": "strategist_score",
        "top_3_priorities": "priorities",
    }
    for old, new in mapping.items():
        if old in output and new not in output:
            output[new] = output.pop(old)
    if (
        "strategist_score" in output
        and isinstance(output["strategist_score"], (int, float))
        and output["strategist_score"] > 10
    ):
        output["strategist_score"] = round(output["strategist_score"] / 10, 1)
    return output


def normalize_ux_analyst(output: dict[str, Any]) -> dict[str, Any]:
    """Remap alternate field names and coerce severity strings."""
    mapping = {
        "ux_score": "ux_analyst_score",
        "critical_friction_points": "friction_map",
        "quick_wins": "quick_wins",
        "ux_summary": "ux_analyst_summary",
    }
    for old, new in mapping.items():
        if old in output and new not in output:
            output[new] = output.pop(old)
    if (
        "ux_analyst_score" in output
        and isinstance(output["ux_analyst_score"], (int, float))
        and output["ux_analyst_score"] > 10
    ):
        output["ux_analyst_score"] = round(output["ux_analyst_score"] / 10, 1)
    if "friction_map" in output and isinstance(output["friction_map"], list):
        _sevmap = {
            1: "MINOR", 2: "MINOR", 3: "MINOR",
            4: "MODERATE", 5: "MODERATE",
            6: "MAJOR", 7: "MAJOR",
            8: "BLOCKER", 9: "BLOCKER", 10: "BLOCKER",
        }
        for item in output["friction_map"]:
            if "issue" in item and "friction_point" not in item:
                item["friction_point"] = item.pop("issue")
            if "frame" in item and "screen" not in item:
                item["screen"] = f"Frame {item.pop('frame')}"
            if "severity" in item and isinstance(item["severity"], (int, float)):
                item["severity"] = _sevmap.get(int(item["severity"]), "MODERATE")
    return output


def normalize_market_researcher(output: dict[str, Any]) -> dict[str, Any]:
    """Remap alternate field names to the canonical market researcher schema."""
    mapping = {
        "user_sentiment_summary": "market_researcher_summary",
        "competitive_threats": "sentiment_by_competitor",
        "top_unmet_needs": "unmet_needs",
        "market_summary": "market_researcher_summary",
        "pricing_signal": "pricing_insight",
    }
    for old, new in mapping.items():
        if old in output and new not in output:
            output[new] = output.pop(old)
    if (
        "market_researcher_score" in output
        and isinstance(output["market_researcher_score"], (int, float))
        and output["market_researcher_score"] > 10
    ):
        output["market_researcher_score"] = round(output["market_researcher_score"] / 10, 1)
    return output


def normalize_challenge(output: dict[str, Any]) -> dict[str, Any]:
    """Clamp final_score to 0–10 in case the model returned a 0–100 value."""
    if (
        "final_score" in output
        and isinstance(output["final_score"], (int, float))
        and output["final_score"] > 10
    ):
        output["final_score"] = round(output["final_score"] / 10, 1)
    return output


# ---------------------------------------------------------------------------
# Hardware monitor
# ---------------------------------------------------------------------------


class HardwareMonitor:
    """Real-time GPU, RAM, and model-state telemetry for adaptive execution."""

    @staticmethod
    def get_gpu_temp() -> int:
        """Return GPU temperature in °C, or -1 if unreadable."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return int(result.stdout.strip().split("\n")[0])
        except Exception:
            return -1

    @staticmethod
    def get_gpu_memory() -> dict[str, int]:
        """Return GPU memory stats in MiB via nvidia-smi."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total,memory.free",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            parts = [int(x.strip()) for x in result.stdout.strip().split(",")]
            return {"used_mib": parts[0], "total_mib": parts[1], "free_mib": parts[2]}
        except Exception:
            return {"used_mib": -1, "total_mib": -1, "free_mib": -1}

    @staticmethod
    def get_ram_usage() -> dict[str, Any]:
        """Return system RAM stats via psutil."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "used_gb": round(mem.used / 1e9, 1),
                "total_gb": round(mem.total / 1e9, 1),
                "percent": mem.percent,
            }
        except Exception:
            return {"used_gb": -1, "total_gb": -1, "percent": -1}

    @staticmethod
    def get_loaded_models() -> list[str]:
        """Return list of currently loaded Ollama models from `ollama ps`."""
        try:
            result = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=5)
            lines = [ln for ln in result.stdout.strip().split("\n")[1:] if ln.strip()]
            return [ln.split()[0] for ln in lines if ln.split()]
        except Exception:
            return []

    @staticmethod
    def unload_all_models() -> None:
        """Unload every known model from Ollama to free VRAM before inference."""
        for model in _KNOWN_MODELS:
            try:
                subprocess.run(["ollama", "stop", model], capture_output=True, timeout=10)
            except Exception:
                pass

    def full_health_check(self) -> dict[str, Any]:
        """Return a snapshot of all hardware metrics."""
        return {
            "gpu_temp": self.get_gpu_temp(),
            "gpu_memory": self.get_gpu_memory(),
            "ram": self.get_ram_usage(),
            "loaded_models": self.get_loaded_models(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def is_safe_to_run(self) -> tuple[bool, str]:
        """Return (safe, reason) for a go/no-go check before inference."""
        temp = self.get_gpu_temp()
        if temp != -1 and temp > THERMAL_CEILING:
            return False, f"GPU temp {temp}°C exceeds ceiling {THERMAL_CEILING}°C"
        ram = self.get_ram_usage()
        if ram["percent"] > 80:
            return False, f"RAM usage {ram['percent']}% exceeds 80% threshold"
        return True, "Hardware OK"

    def wait_for_cool(self) -> int:
        """Block until GPU drops below THERMAL_RESUME. Returns final temp."""
        temp = self.get_gpu_temp()
        if temp == -1 or temp <= THERMAL_RESUME:
            return temp
        logger.warning("GPU at %d°C — waiting to cool below %d°C...", temp, THERMAL_RESUME)
        while temp > THERMAL_RESUME:
            time.sleep(10)
            temp = self.get_gpu_temp()
            if temp == -1:
                logger.warning("Lost GPU temp sensor — proceeding cautiously")
                return temp
            logger.info("  Cooling... %d°C", temp)
        logger.info("  Resumed at %d°C", temp)
        return temp


# ---------------------------------------------------------------------------
# Adaptive runner
# ---------------------------------------------------------------------------


class AdaptiveRunner:
    """
    Hardware-adaptive LLM execution engine.

    Automatically selects an execution tier based on real-time GPU temperature
    and RAM usage, then runs the four-analyst War Room analysis pipeline with
    appropriate cooling pauses and context trimming.
    """

    def __init__(self) -> None:
        """Initialize the runner with a fresh hardware monitor and empty execution log."""
        self.monitor = HardwareMonitor()
        self.execution_log: list[dict[str, Any]] = []
        self.tier_used: Optional[int] = None

    def _select_tier(self) -> int:
        """Choose Tier 2 or Tier 3 based on current hardware state.

        Tier 2 (Sequential, qwen3:32b): GPU < 65°C and RAM < 60%
        Tier 3 (Micro, llama3.1:8b):    GPU >= 65°C or RAM >= 60% or unreadable
        """
        health = self.monitor.full_health_check()
        temp = health["gpu_temp"]
        ram_pct = health["ram"]["percent"]

        logger.info("Hardware pre-check: GPU %s°C | RAM %s%%", temp, ram_pct)

        if temp == -1:
            logger.info("Tier 3 selected — GPU temp unreadable (safest default)")
            return 3

        if temp < 65 and ram_pct < 60:
            logger.info("Tier 2 selected — Sequential, qwen3:32b, %ds cooling", COOLDOWN_SECONDS)
            return 2

        logger.info(
            "Tier 3 selected — GPU %d°C / RAM %d%% exceeds threshold; "
            "using llama3.1:8b with extended cooling",
            temp, ram_pct,
        )
        return 3

    def _trim_context(self, text: str, max_chars: int) -> str:
        """Truncate evidence block to prevent KV cache pressure."""
        if len(text) <= max_chars:
            return text
        logger.warning("Trimming context %d → %d chars for thermal safety", len(text), max_chars)
        return text[:max_chars] + "\n\n[Context trimmed for thermal safety]"

    async def _call_model(
        self,
        session: "aiohttp.ClientSession",
        endpoint: dict[str, str],
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a single chat completion to the configured endpoint and parse JSON.

        Works with both Ollama (DGX mode) and OpenAI (cloud mode).
        Returns a dict — either the parsed JSON or {"error": "..."} on failure.
        """
        import src.config as _cfg  # imported here so runtime mode changes are reflected

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if _cfg.EXECUTION_MODE == "cloud":
            api_key = os.environ.get("OPENAI_API_KEY", "")
            headers["Authorization"] = f"Bearer {api_key}"

        payload: dict[str, Any] = {
            "model": endpoint["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

        # OpenAI uses response_format; Ollama uses format
        if _cfg.EXECUTION_MODE == "cloud":
            payload["response_format"] = {"type": "json_object"}
        else:
            payload["format"] = "json"

        content: str = ""
        try:
            timeout = aiohttp.ClientTimeout(total=300)
            async with session.post(
                endpoint["url"], json=payload, headers=headers, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    source = "OpenAI" if _cfg.EXECUTION_MODE == "cloud" else "Ollama"
                    return {"error": f"{source} returned HTTP {resp.status}: {error_text[:200]}"}
                data = await resp.json()
                content = data["choices"][0]["message"]["content"]

            # Strip any markdown fences the model may wrap around the JSON
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return json.loads(content.strip())

        except json.JSONDecodeError as exc:
            return {
                "error": f"JSON parse failed: {exc}",
                "raw_preview": content[:500],
            }
        except asyncio.TimeoutError:
            return {"error": "Request timed out after 300s"}
        except Exception as exc:
            return {"error": f"Model call failed: {exc}"}

    async def run_analysis(
        self,
        session_id: str,
        product_name: str,
        product_description: str,
        target_user: str,
        differentiator: str,
        product_stage: str,
        competitors: str,
        comparison_cards_json: str,
        agent_brief: str,
        curated_evidence_json: str,
        frame_analyses_json: str,
        screenshot_matches_json: str,
        n_screenshots: int = 69,
        n_apps: int = 10,
        n_reviews: int = 60,
        log_fn: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ) -> dict[str, Any]:
        """Run the full four-analyst pipeline with hardware-adaptive execution.

        Analysts run sequentially (one model loaded at a time) with cooling pauses
        between each round. The partner review synthesizes all three analyses.

        Args:
            session_id: UUID for this analysis session; deliverable saved here.
            product_name: Short product name.
            product_description: Full product description.
            target_user: Who this product is for.
            differentiator: Key differentiating claim.
            product_stage: E.g. "MVP with 12 beta users".
            competitors: Comma-separated competitor names.
            comparison_cards_json: JSON string of side-by-side comparison cards.
            agent_brief: Synthesized intelligence brief from screenshot matching.
            curated_evidence_json: JSON string of curated user reviews.
            frame_analyses_json: JSON string of GPT-4o Vision frame analyses.
            screenshot_matches_json: JSON string of screenshot match results.
            n_screenshots: Total screenshots in competitor suite (for prompt context).
            n_apps: Number of competitor apps in suite.
            n_reviews: Number of curated reviews.

        Returns:
            Deliverable dict including verdicts from all four analysts plus metadata.
        """
        import src.config as _cfg

        from src.prompts.market_researcher import (
            MARKET_RESEARCHER_SYSTEM_PROMPT,
            build_market_researcher_prompt,
        )
        from src.prompts.partner_review import (
            PARTNER_REVIEW_SYSTEM_PROMPT,
            build_partner_review_prompt,
        )
        from src.prompts.strategist import STRATEGIST_SYSTEM_PROMPT, build_strategist_prompt
        from src.prompts.ux_analyst import UX_ANALYST_SYSTEM_PROMPT, build_ux_analyst_prompt

        execution_mode = _cfg.EXECUTION_MODE
        endpoints = _cfg.get_endpoints()

        async def _log(analyst: str, message: str) -> None:
            """Emit a log line to both the Python logger and the SSE callback (if wired)."""
            logger.info("[%s] %s", analyst.upper(), message)
            if log_fn is not None:
                await log_fn(analyst, message)

        # ── Mode-specific setup ───────────────────────────────────────────────
        if execution_mode == "cloud":
            model = endpoints["strategist"]["model"]
            tier: Optional[int] = None
            max_ctx = MAX_CONTEXT_CHARS
            cooldown = 1  # minimal pause only

            logger.info("=" * 60)
            logger.info("ADAPTIVE RUNNER — CLOUD MODE")
            logger.info("Model: %s | Parallel execution | No thermal constraints", model)
            logger.info("=" * 60)
            await _log("system", f"Cloud mode — {model} — running 3 analysts in parallel")
        else:
            tier = self._select_tier()
            self.tier_used = tier
            model = PREFERRED_MODEL if tier == 2 else FALLBACK_MODEL
            max_ctx = MAX_CONTEXT_CHARS if tier == 2 else MAX_CONTEXT_CHARS // 2
            cooldown = COOLDOWN_SECONDS if tier == 2 else COOLDOWN_SECONDS * 2

            logger.info("=" * 60)
            logger.info("ADAPTIVE RUNNER — DGX MODE — Tier %d", tier)
            logger.info("Model: %s | Max context: %d chars | Cooldown: %ds", model, max_ctx, cooldown)
            logger.info("=" * 60)
            await _log("system", f"DGX Spark mode — Tier {tier} — model: {model} — cooldown: {cooldown}s")

            # Unload everything before starting to reclaim VRAM
            self.monitor.unload_all_models()
            await asyncio.sleep(5)
            self.monitor.wait_for_cool()

        # Trim all evidence blocks to prevent KV cache pressure
        comparison_cards_json = self._trim_context(comparison_cards_json, max_ctx)
        curated_evidence_json = self._trim_context(curated_evidence_json, max_ctx)
        frame_analyses_json = self._trim_context(frame_analyses_json, max_ctx)
        screenshot_matches_json = self._trim_context(screenshot_matches_json, max_ctx)
        agent_brief = self._trim_context(agent_brief, max_ctx // 2)

        results: dict[str, Any] = {}

        # ── Build all prompts up front ────────────────────────────────────────
        strategist_prompt = build_strategist_prompt(
            product_name, product_description, target_user, differentiator,
            product_stage, competitors, comparison_cards_json, agent_brief,
            curated_evidence_json, n_screenshots, n_apps, n_reviews,
        )
        ux_prompt = build_ux_analyst_prompt(
            product_name, product_description, target_user, differentiator,
            product_stage, frame_analyses_json, screenshot_matches_json,
            comparison_cards_json,
        )
        market_prompt = build_market_researcher_prompt(
            product_name, product_description, target_user, differentiator,
            product_stage, competitors, curated_evidence_json,
            comparison_cards_json, agent_brief,
        )

        # ── Run first three analysts ──────────────────────────────────────────
        async with aiohttp.ClientSession() as http_session:

            if execution_mode == "cloud":
                # PARALLEL — no GPU constraints in cloud mode
                logger.info("\n[ROUNDS 1-3] Running analysts in parallel (cloud mode)")
                pipeline_start = time.time()

                await _log("strategist", f"Sending request to {model}...")
                await _log("ux_analyst", f"Sending request to {model}...")
                await _log("market_researcher", f"Sending request to {model}...")

                strategist_out, ux_out, market_out = await asyncio.gather(
                    self._call_model(
                        http_session, endpoints["strategist"],
                        STRATEGIST_SYSTEM_PROMPT, strategist_prompt,
                    ),
                    self._call_model(
                        http_session, endpoints["ux_analyst"],
                        UX_ANALYST_SYSTEM_PROMPT, ux_prompt,
                    ),
                    self._call_model(
                        http_session, endpoints["market_researcher"],
                        MARKET_RESEARCHER_SYSTEM_PROMPT, market_prompt,
                    ),
                )

                parallel_elapsed = round(time.time() - pipeline_start, 1)
                logger.info("  Parallel analysts complete in %.1fs", parallel_elapsed)

                for key, label, raw in [
                    ("strategist", "Strategist", strategist_out),
                    ("ux_analyst", "UX Analyst", ux_out),
                    ("market_researcher", "Market Researcher", market_out),
                ]:
                    if "error" not in raw:
                        if key == "strategist":
                            raw = normalize_strategist(raw)
                        elif key == "ux_analyst":
                            raw = normalize_ux_analyst(raw)
                        elif key == "market_researcher":
                            raw = normalize_market_researcher(raw)
                    status = "OK" if "error" not in raw else f"FAILED: {raw['error'][:80]}"
                    logger.info("  %s: %s", label, status)
                    analyst_key = key  # strategist | ux_analyst | market_researcher
                    await _log(analyst_key, f"Response received ({parallel_elapsed}s) — {status}")
                    results[key] = raw
                    self.execution_log.append({
                        "round": label,
                        "mode": "cloud",
                        "model": model,
                        "elapsed_seconds": parallel_elapsed,
                        "status": status,
                    })

                await asyncio.sleep(cooldown)

            else:
                # SEQUENTIAL with thermal management — DGX mode
                analyst_rounds = [
                    ("strategist", "Strategist", STRATEGIST_SYSTEM_PROMPT,
                     strategist_prompt, "strategist"),
                    ("ux_analyst", "UX Analyst", UX_ANALYST_SYSTEM_PROMPT,
                     ux_prompt, "ux_analyst"),
                    ("market_researcher", "Market Researcher", MARKET_RESEARCHER_SYSTEM_PROMPT,
                     market_prompt, "market_researcher"),
                ]

                for i, (key, label, sys_prompt, user_prompt_str, ep_key) in enumerate(analyst_rounds):
                    logger.info("\n[ROUND %d/4] %s", i + 1, label)
                    self.monitor.wait_for_cool()

                    health_before = self.monitor.full_health_check()
                    gpu_temp = health_before["gpu_temp"]
                    ram_pct = health_before["ram"]["percent"]
                    logger.info(
                        "  Pre-inference: GPU %s°C | RAM %s%%",
                        gpu_temp,
                        ram_pct,
                    )
                    await _log(key, f"Starting analysis (model: {model} | GPU: {gpu_temp}°C | RAM: {ram_pct}%)")

                    start = time.time()
                    result = await self._call_model(
                        http_session, endpoints[ep_key], sys_prompt, user_prompt_str,
                    )
                    elapsed = time.time() - start

                    if "error" not in result:
                        if key == "strategist":
                            result = normalize_strategist(result)
                        elif key == "ux_analyst":
                            result = normalize_ux_analyst(result)
                        elif key == "market_researcher":
                            result = normalize_market_researcher(result)

                    status = "OK" if "error" not in result else f"FAILED: {result['error'][:80]}"
                    logger.info("  %s: %s (%.1fs)", label, status, elapsed)
                    await _log(key, f"Complete ({elapsed:.1f}s) — {status}")

                    results[key] = result
                    self.execution_log.append({
                        "round": label,
                        "mode": "dgx",
                        "model": model,
                        "tier": tier,
                        "elapsed_seconds": round(elapsed, 1),
                        "status": status,
                        "gpu_temp_before": health_before["gpu_temp"],
                    })

                    if i < len(analyst_rounds) - 1:
                        logger.info("  Cooling pause: %ds", cooldown)
                        await asyncio.sleep(cooldown)

            # --- Round 4: Partner Review ---
            logger.info("\n[ROUND 4/4] Partner Review")
            await _log("partner", "Cross-validating all three analyses...")

            if execution_mode == "dgx":
                self.monitor.wait_for_cool()

            partner_prompt = build_partner_review_prompt(
                product_name,
                product_description,
                target_user,
                differentiator,
                product_stage,
                json.dumps(results.get("strategist", {}), indent=2),
                json.dumps(results.get("ux_analyst", {}), indent=2),
                json.dumps(results.get("market_researcher", {}), indent=2),
            )

            partner_endpoint = endpoints.get("strategist", endpoints[next(iter(endpoints))])
            challenge_out = await self._call_model(
                http_session, partner_endpoint,
                PARTNER_REVIEW_SYSTEM_PROMPT, partner_prompt, max_tokens=2048,
            )
            if "error" not in challenge_out:
                challenge_out = normalize_challenge(challenge_out)
            partner_status = "OK" if "error" not in challenge_out else "FAILED"
            logger.info("  Partner Review: %s", partner_status)
            await _log("partner", f"Partner review complete — {partner_status}")

        # --- Normalise schema before assembly ---
        # Clamp final_score to 0-10 range (prompt asks for 0-10, but guard against
        # models that return 0-100 despite instructions).
        raw_score = challenge_out.get("final_score", 0)
        try:
            score_float = float(raw_score)
        except (TypeError, ValueError):
            score_float = 0.0
        if score_float > 10:
            score_float = round(score_float / 10, 1)

        # Map market_readiness to the enum Report.tsx expects.
        _READINESS_MAP: dict[str, str] = {
            "READY_TO_SCALE": "STRONG",
            "NEEDS_PIVOT": "NOT_READY",
            "DO_NOT_INVEST": "NOT_READY",
            "NOT_READY": "NOT_READY",
            "NEEDS_WORK": "NEEDS_WORK",
            "COMPETITIVE": "COMPETITIVE",
            "STRONG": "STRONG",
            "EXCEPTIONAL": "EXCEPTIONAL",
        }
        raw_readiness = challenge_out.get("market_readiness", "NEEDS_WORK")
        market_readiness = _READINESS_MAP.get(str(raw_readiness).upper(), "NEEDS_WORK")

        # Inject video evidence comparison cards into ux_analyst_section.
        # The UX analyst LLM produces text-based cards; these are kept, but if
        # the video evidence synthesis generated richer cards we prepend them
        # (mapped from synthesis format to Report.tsx ComparisonCard format).
        ux_section: dict[str, Any] = dict(results.get("ux_analyst", {}))
        if comparison_cards_json and comparison_cards_json.strip() not in ("{}", "[]", ""):
            try:
                evidence_cards: list[dict[str, Any]] = json.loads(comparison_cards_json)
                mapped: list[dict[str, Any]] = []
                for i, card in enumerate(evidence_cards[:6]):
                    user_side = card.get("user_side", card.get("user_screen", {}))
                    comp_side = card.get("competitor_side", card.get("competitor_screen", {}))
                    if not user_side or not comp_side:
                        continue
                    mapped.append({
                        "card_id": card.get("card_id", f"card-{i}"),
                        "user_screen": {
                            "frame_number": user_side.get("frame_number"),
                            "image_path": user_side.get("image_path", ""),
                            "image_url": user_side.get("image_url", ""),
                            "screen_label": user_side.get("screen_label", f"Frame {i + 1}"),
                            "ux_score": float(user_side.get("ux_score", 5)),
                            "strengths": user_side.get("strengths", []),
                            "weaknesses": user_side.get("weaknesses", []),
                        },
                        "competitor_screen": {
                            "app": comp_side.get("app", "competitor"),
                            "filename": comp_side.get("filename", ""),
                            "image_path": comp_side.get("image_path", ""),
                            "image_url": comp_side.get("image_url", ""),
                            "screen_label": comp_side.get("screen_label", "Competitor screen"),
                            "ux_score": float(comp_side.get("ux_score", 5)),
                            "strengths": comp_side.get("strengths", []),
                            "weaknesses": comp_side.get("weaknesses", []),
                        },
                        "similarity_score": float(card.get("similarity_score", 0.5)),
                        "comparison_verdict": card.get("comparison_verdict", "COMPARABLE"),
                        "what_to_steal": card.get("what_to_steal", ""),
                        "what_to_avoid": card.get("what_to_avoid", ""),
                    })
                if mapped:
                    # Prefer evidence-backed cards over LLM-generated placeholders
                    ux_section["comparison_cards"] = mapped + ux_section.get("comparison_cards", [])[len(mapped):]
            except Exception as _inject_exc:
                logger.warning("Could not inject comparison cards: %s", _inject_exc)

        # --- Assemble deliverable ---
        exec_meta: dict[str, Any] = {
            "mode": execution_mode,
            "model": model,
            "max_context_chars": max_ctx,
            "execution_log": self.execution_log,
        }
        if execution_mode == "dgx":
            exec_meta.update({
                "tier": tier,
                "thermal_ceiling_c": THERMAL_CEILING,
                "thermal_resume_c": THERMAL_RESUME,
                "cooldown_seconds": cooldown,
            })

        deliverable: dict[str, Any] = {
            "product_name": product_name,
            "product_description": product_description,
            "target_user": target_user,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_metadata": exec_meta,
            "verdict": {
                "headline": challenge_out.get("headline", "Analysis complete"),
                "score": score_float,
                "recommendation": challenge_out.get(
                    "one_thing_to_do_monday",
                    challenge_out.get("recommendation", ""),
                ),
                "market_readiness": market_readiness,
                "one_thing_to_do_monday": challenge_out.get("one_thing_to_do_monday", ""),
            },
            "strategist_section": results.get("strategist", {}),
            "ux_analyst_section": ux_section,
            "market_researcher_section": results.get("market_researcher", {}),
            "challenge_layer": challenge_out,
        }

        # Preserve pipeline comparison_cards (with image_path fields) as a top-level key.
        # The models receive them as context text; the PIPELINE version is authoritative
        # for image_path fields used by frontend side-by-side rendering.
        # Note: comparison_cards_json may have been context-trimmed (invalid JSON); the
        # except branch produces an empty list rather than crashing the save.
        try:
            if comparison_cards_json and comparison_cards_json.strip() not in ("{}", "[]", ""):
                deliverable["comparison_cards"] = json.loads(comparison_cards_json)
            else:
                deliverable["comparison_cards"] = []
        except Exception:
            deliverable["comparison_cards"] = []

        # Persist to disk before returning so a crash mid-delivery doesn't lose the result
        session_dir = Path("sessions") / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        with open(session_dir / "deliverable.json", "w") as fh:
            json.dump(deliverable, fh, indent=2)

        logger.info("\nDeliverable saved: sessions/%s/deliverable.json", session_id)
        logger.info(
            "Final score: %s | Readiness: %s",
            challenge_out.get("final_score", "N/A"),
            challenge_out.get("market_readiness", "N/A"),
        )
        logger.info("Headline: %s", challenge_out.get("headline", "N/A"))

        return deliverable

    def run_sync(self, **kwargs: Any) -> dict[str, Any]:
        """Synchronous wrapper around run_analysis() for non-async callers."""
        return asyncio.run(self.run_analysis(**kwargs))
