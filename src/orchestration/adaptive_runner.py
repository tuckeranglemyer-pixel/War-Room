"""
Adaptive Runner — Hardware-aware execution engine for the War Room analysis pipeline.

Implements three execution tiers that automatically select based on real-time GPU telemetry:

  Tier 2 (Sequential): 1 model at a time via Ollama with cooling pauses.
                        Uses qwen3:32b. Default for healthy DGX Spark.
  Tier 3 (Micro):       Ultra-conservative — halved context, llama3.1:8b, 60s cooling.
                        Used when GPU temp >= 65°C or RAM >= 60%.

Tier 1 (Full parallel vLLM) is architecturally documented in ARCHITECTURE.md but
is not implemented here because simultaneous 3-model loading is the root cause of
the DGX Spark power-loss crashes. Sequential execution prevents cumulative VRAM
pressure from triggering the thermal shutdown circuit.

Key safety properties:
  - All models are unloaded before starting (ollama_stop_all)
  - GPU temp is checked before every round; execution blocks until THERMAL_RESUME_C
  - Context is trimmed to MAX_CONTEXT_CHARS before any inference call
  - Deliverable is persisted to disk before returning so a crash mid-delivery
    does not lose the result
  - Execution metadata (tier, model, timing, GPU temps) is embedded in every
    deliverable.json for post-mortem analysis

Env vars:
  OLLAMA_URL               — Ollama completions endpoint (default: localhost:11434/v1/...)
  WAR_ROOM_MODEL           — Tier 2 model tag (default: qwen3:32b)
  WAR_ROOM_FALLBACK_MODEL  — Tier 3 model tag (default: llama3.1:8b)
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
from typing import Any, Optional

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

    async def _call_ollama(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a single chat completion to Ollama and parse the JSON response.

        Returns a dict — either the parsed JSON or {"error": "..."} on failure.
        """
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

        content: str = ""
        try:
            timeout = aiohttp.ClientTimeout(total=300)
            async with aiohttp.ClientSession() as session:
                async with session.post(OLLAMA_URL, json=payload, timeout=timeout) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return {"error": f"Ollama returned HTTP {resp.status}: {error_text[:200]}"}
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
            return {"error": "Ollama timed out after 300s"}
        except Exception as exc:
            return {"error": f"Ollama call failed: {exc}"}

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

        tier = self._select_tier()
        self.tier_used = tier
        model = PREFERRED_MODEL if tier == 2 else FALLBACK_MODEL
        max_ctx = MAX_CONTEXT_CHARS if tier == 2 else MAX_CONTEXT_CHARS // 2
        cooldown = COOLDOWN_SECONDS if tier == 2 else COOLDOWN_SECONDS * 2

        logger.info("=" * 60)
        logger.info("ADAPTIVE RUNNER — Tier %d", tier)
        logger.info("Model: %s | Max context: %d chars | Cooldown: %ds", model, max_ctx, cooldown)
        logger.info("=" * 60)

        # Unload everything before starting to reclaim VRAM
        self.monitor.unload_all_models()
        time.sleep(5)
        self.monitor.wait_for_cool()

        # Trim all evidence blocks to prevent KV cache pressure
        comparison_cards_json = self._trim_context(comparison_cards_json, max_ctx)
        curated_evidence_json = self._trim_context(curated_evidence_json, max_ctx)
        frame_analyses_json = self._trim_context(frame_analyses_json, max_ctx)
        screenshot_matches_json = self._trim_context(screenshot_matches_json, max_ctx)
        agent_brief = self._trim_context(agent_brief, max_ctx // 2)

        results: dict[str, Any] = {}

        # --- Round definitions ---
        rounds = [
            (
                "strategist",
                "Strategist",
                STRATEGIST_SYSTEM_PROMPT,
                lambda: build_strategist_prompt(
                    product_name, product_description, target_user, differentiator,
                    product_stage, competitors, comparison_cards_json, agent_brief,
                    curated_evidence_json, n_screenshots, n_apps, n_reviews,
                ),
            ),
            (
                "ux_analyst",
                "UX Analyst",
                UX_ANALYST_SYSTEM_PROMPT,
                lambda: build_ux_analyst_prompt(
                    product_name, product_description, target_user, differentiator,
                    product_stage, frame_analyses_json, screenshot_matches_json,
                    comparison_cards_json,
                ),
            ),
            (
                "market_researcher",
                "Market Researcher",
                MARKET_RESEARCHER_SYSTEM_PROMPT,
                lambda: build_market_researcher_prompt(
                    product_name, product_description, target_user, differentiator,
                    product_stage, competitors, curated_evidence_json,
                    comparison_cards_json, agent_brief,
                ),
            ),
        ]

        # --- Run first three analysts sequentially ---
        for i, (key, label, sys_prompt, build_prompt) in enumerate(rounds):
            logger.info("\n[ROUND %d/4] %s", i + 1, label)
            self.monitor.wait_for_cool()

            health_before = self.monitor.full_health_check()
            logger.info(
                "  Pre-inference: GPU %s°C | RAM %s%%",
                health_before["gpu_temp"],
                health_before["ram"]["percent"],
            )

            start = time.time()
            result = await self._call_ollama(model, sys_prompt, build_prompt())
            elapsed = time.time() - start

            status = "OK" if "error" not in result else f"FAILED: {result['error'][:80]}"
            logger.info("  %s: %s (%.1fs)", label, status, elapsed)

            results[key] = result
            self.execution_log.append({
                "round": label,
                "model": model,
                "tier": tier,
                "elapsed_seconds": round(elapsed, 1),
                "status": status,
                "gpu_temp_before": health_before["gpu_temp"],
            })

            if i < len(rounds) - 1:
                logger.info("  Cooling pause: %ds", cooldown)
                time.sleep(cooldown)

        # --- Round 4: Partner Review ---
        logger.info("\n[ROUND 4/4] Partner Review")
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
        challenge_out = await self._call_ollama(
            model, PARTNER_REVIEW_SYSTEM_PROMPT, partner_prompt, max_tokens=2048
        )
        partner_status = "OK" if "error" not in challenge_out else "FAILED"
        logger.info("  Partner Review: %s", partner_status)

        # --- Assemble deliverable ---
        deliverable: dict[str, Any] = {
            "product_name": product_name,
            "product_description": product_description,
            "target_user": target_user,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_metadata": {
                "tier": tier,
                "model": model,
                "thermal_ceiling_c": THERMAL_CEILING,
                "thermal_resume_c": THERMAL_RESUME,
                "cooldown_seconds": cooldown,
                "max_context_chars": max_ctx,
                "execution_log": self.execution_log,
            },
            "verdict": {
                "headline": challenge_out.get("headline", "Analysis complete"),
                "score": challenge_out.get("final_score", 0),
                "recommendation": challenge_out.get("recommendation", ""),
                "market_readiness": challenge_out.get("market_readiness", "NEEDS_WORK"),
                "one_thing_to_do_monday": challenge_out.get("one_thing_to_do_monday", ""),
            },
            "strategist_section": results.get("strategist", {}),
            "ux_analyst_section": results.get("ux_analyst", {}),
            "market_researcher_section": results.get("market_researcher", {}),
            "challenge_layer": challenge_out,
        }

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
