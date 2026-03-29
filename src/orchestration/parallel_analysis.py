"""
Parallel Analysis Engine
========================
Runs 3 specialist models in parallel via vLLM, then one challenge pass.
Produces the final deliverable JSON for the one-pager.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

from src.config import CHALLENGE_ENDPOINT, VLLM_ENDPOINTS
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


async def call_vllm(
    session: aiohttp.ClientSession,
    endpoint: dict,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> dict:
    """Call a vLLM endpoint and return parsed JSON."""
    payload = {
        "model": endpoint["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    content = ""
    try:
        async with session.post(
            endpoint["url"],
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300),
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                return {"error": f"vLLM returned {resp.status}: {error_text}"}

            data = await resp.json()
            content = data["choices"][0]["message"]["content"]

            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            return json.loads(content)

    except json.JSONDecodeError as e:
        return {"error": f"JSON parse failed: {e}", "raw_content": content[:500]}
    except asyncio.TimeoutError:
        return {"error": "vLLM call timed out after 300s"}
    except Exception as e:
        return {"error": f"vLLM call failed: {e!s}"}


def _status_line(label: str, output: dict) -> str:
    if "error" in output:
        return f"  {label:<22s} FAILED — {output['error']}"
    return f"  {label:<22s} OK"


async def run_parallel_analysis(
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
) -> dict:
    """
    Run the full parallel analysis pipeline:
    1. Three specialist models run in parallel
    2. Partner review reads all three outputs
    3. Assemble final deliverable JSON
    """

    print(f"\n{'=' * 60}")
    print(f"  PARALLEL ANALYSIS — Session {session_id}")
    print(f"{'=' * 60}")

    # ------------------------------------------------------------------
    # ROUND 1: Three specialists in parallel
    # ------------------------------------------------------------------
    print("\n[ROUND 1] Running 3 specialists in parallel...")
    start = time.time()

    strategist_prompt = build_strategist_prompt(
        product_name,
        product_description,
        target_user,
        differentiator,
        product_stage,
        competitors,
        comparison_cards_json,
        agent_brief,
        curated_evidence_json,
        n_screenshots,
        n_apps,
        n_reviews,
    )

    ux_analyst_prompt = build_ux_analyst_prompt(
        product_name,
        product_description,
        target_user,
        differentiator,
        product_stage,
        frame_analyses_json,
        screenshot_matches_json,
        comparison_cards_json,
    )

    market_researcher_prompt = build_market_researcher_prompt(
        product_name,
        product_description,
        target_user,
        differentiator,
        product_stage,
        competitors,
        curated_evidence_json,
        comparison_cards_json,
        agent_brief,
    )

    async with aiohttp.ClientSession() as http:
        strategist_output, ux_analyst_output, market_researcher_output = (
            await asyncio.gather(
                call_vllm(
                    http,
                    VLLM_ENDPOINTS["strategist"],
                    STRATEGIST_SYSTEM_PROMPT,
                    strategist_prompt,
                ),
                call_vllm(
                    http,
                    VLLM_ENDPOINTS["ux_analyst"],
                    UX_ANALYST_SYSTEM_PROMPT,
                    ux_analyst_prompt,
                ),
                call_vllm(
                    http,
                    VLLM_ENDPOINTS["market_researcher"],
                    MARKET_RESEARCHER_SYSTEM_PROMPT,
                    market_researcher_prompt,
                ),
            )
        )

        round1_time = time.time() - start
        print(_status_line("Strategist:", strategist_output))
        print(_status_line("UX Analyst:", ux_analyst_output))
        print(_status_line("Market Researcher:", market_researcher_output))
        print(f"  Round 1 time: {round1_time:.1f}s")

        # ------------------------------------------------------------------
        # ROUND 2: Partner Review (sequential — needs all three outputs)
        # ------------------------------------------------------------------
        print("\n[ROUND 2] Running Partner Review (Llama 70B)...")
        start2 = time.time()

        partner_prompt = build_partner_review_prompt(
            product_name,
            product_description,
            target_user,
            differentiator,
            product_stage,
            json.dumps(strategist_output, indent=2),
            json.dumps(ux_analyst_output, indent=2),
            json.dumps(market_researcher_output, indent=2),
        )

        challenge_output = await call_vllm(
            http,
            CHALLENGE_ENDPOINT,
            PARTNER_REVIEW_SYSTEM_PROMPT,
            partner_prompt,
            max_tokens=2048,
            temperature=0.2,
        )

        round2_time = time.time() - start2
        print(_status_line("Partner Review:", challenge_output))
        print(f"  Round 2 time: {round2_time:.1f}s")

    # ------------------------------------------------------------------
    # ASSEMBLY: Combine into final deliverable
    # ------------------------------------------------------------------
    print("\n[ASSEMBLY] Building final deliverable...")

    deliverable = {
        "product_name": product_name,
        "product_description": product_description,
        "target_user": target_user,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "verdict": {
            "headline": challenge_output.get("headline", "Analysis complete"),
            "score": challenge_output.get("final_score", 0),
            "recommendation": challenge_output.get("one_thing_to_do_monday", ""),
            "market_readiness": challenge_output.get("market_readiness", "NEEDS_WORK"),
        },
        "strategist_section": strategist_output,
        "ux_analyst_section": ux_analyst_output,
        "market_researcher_section": market_researcher_output,
        "challenge_layer": challenge_output,
    }

    session_dir = Path(f"sessions/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)
    deliverable_path = session_dir / "deliverable.json"
    with open(deliverable_path, "w") as f:
        json.dump(deliverable, f, indent=2)

    total_time = round1_time + round2_time
    print(f"\n  Total analysis time: {total_time:.1f}s")
    print(f"  Deliverable saved:  {deliverable_path}")
    print(f"  Final score:        {challenge_output.get('final_score', 'N/A')}")
    print(f"  Headline:           {challenge_output.get('headline', 'N/A')}")

    return deliverable


def run_parallel_analysis_sync(**kwargs: object) -> dict:
    """Synchronous wrapper for the async parallel analysis."""
    return asyncio.run(run_parallel_analysis(**kwargs))
