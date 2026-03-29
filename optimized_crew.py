"""
DGX-optimized War Room CLI: smart evidence curation via llama3:8b query generation,
then thermal-safe debate (see ``thermal_safe_debate_runner.build_and_run_safe``).
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from typing import Callable

import requests

from src.inference.model_config import LOCAL_BASE_URL
from src.orchestration import thermal_safe_debate_runner as ts
from src.rag import chroma_retrieval as _chroma

logger = logging.getLogger(__name__)

BASE_URL = LOCAL_BASE_URL

_original_fetch_context: Callable[..., str] = ts.fetch_context_for_product


def smart_evidence_fetch(product: str, llm_base_url: str = "http://localhost:11434") -> str:
    """
    Stage 0: Lightweight model generates product-specific RAG queries,
    then we execute them all against ChromaDB and compile a curated briefing.
    This replaces dumb hardcoded queries with intelligent, targeted retrieval.
    """
    from src.rag.chroma_retrieval import _query_collection

    logger.info("Stage 0: Smart evidence curation (llama3:8b)")

    if _chroma._pm_tools_collection is None:
        logger.warning("ChromaDB collection unavailable — skipping smart retrieval")
        return (
            f"EVIDENCE BRIEFING FOR: {product}\n"
            "[ChromaDB not ready — no pre-seeded context available]\n"
        )

    app_key = product.lower().split()[0]

    # Step 1: Ask small model to generate targeted queries
    prompt = f"""You are a research assistant preparing evidence for a product debate about: {product}

Generate exactly 10 search queries that would find the most critical user feedback about this product. Focus on:
- Onboarding problems and first-time user confusion
- Performance issues (speed, crashes, mobile stability)
- Pricing complaints and free-tier limitations
- Missing features users are angry about
- Competitor comparisons (what users switched to and why)
- Long-term reliability issues (data loss, sync problems)
- Integration and API complaints
- Search/findability problems within the product

Return ONLY a JSON array of 10 query strings. No explanation. Example:
["notion search broken slow", "notion mobile app crashes", ...]"""

    try:
        resp = requests.post(
            f"{llm_base_url}/v1/chat/completions",
            json={
                "model": "llama3:8b",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]

        # Parse JSON array from response
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            queries = [q for q in parsed if isinstance(q, str)]
        else:
            raise ValueError("No JSON array found")

        logger.info("Generated %d smart queries", len(queries))
    except Exception as e:
        logger.warning("Smart query generation failed (%s), using fallback queries", e)
        product_name = product.split("-")[0].strip().split()[0]
        queries = [
            f"{product_name} onboarding confusing new user",
            f"{product_name} slow performance complaints",
            f"{product_name} mobile app crashes bugs",
            f"{product_name} pricing expensive complaints",
            f"{product_name} missing features users want",
            f"{product_name} vs competitor switched from",
            f"{product_name} search broken findability",
            f"{product_name} data loss sync problems",
            f"{product_name} integration API issues",
            f"{product_name} long term reliability problems",
        ]

    # Step 2: Run all queries against ChromaDB and deduplicate
    all_results: list[str] = []
    seen_ids: set[str] = set()

    for q in queries[:10]:
        try:
            raw_block = _query_collection(
                q, n_results=5, where={"app": app_key}
            )
            if raw_block.startswith("[ChromaDB error]") or raw_block.startswith(
                "No results found"
            ):
                continue
            for doc in raw_block.split("\n\n---\n\n"):
                doc = doc.strip()
                if not doc:
                    continue
                doc_id = doc[:100]
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_results.append(doc)
        except Exception as e:
            logger.warning("Query failed: %s — %s", q, e)

    logger.info(
        "Retrieved %d unique evidence chunks from %d queries",
        len(all_results),
        len(queries[:10]),
    )

    # Step 3: Compile into structured briefing (cap at 15000 chars)
    briefing = f"EVIDENCE BRIEFING FOR: {product}\n"
    briefing += "Sources: %d unique chunks from Reddit, HN, Google Play\n" % len(
        all_results
    )
    briefing += "=" * 60 + "\n\n"

    char_count = len(briefing)
    for i, doc in enumerate(all_results):
        entry = f"[Evidence #{i + 1}]\n{doc}\n\n---\n\n"
        if char_count + len(entry) > 15000:
            break
        briefing += entry
        char_count += len(entry)

    return briefing


def _smart_fetch_then_unload_small_model(product_name: str, n_results: int = 5) -> str:
    """Adapter: same contract as ``fetch_context_for_product`` for thermal-safe runner."""
    _ = n_results
    logger.info("Running smart evidence curation...")
    evidence = smart_evidence_fetch(product_name, BASE_URL)
    logger.info("Evidence briefing: %d chars, ready for injection", len(evidence))
    subprocess.run(
        ["ollama", "stop", "llama3:8b"], capture_output=True, timeout=10
    )
    time.sleep(5)
    return evidence


def run_war_room(product: str) -> str:
    """Run the full thermal-safe debate with smart RAG curation instead of template queries."""
    ts.fetch_context_for_product = _smart_fetch_then_unload_small_model
    try:
        return ts.build_and_run_safe(product)
    finally:
        ts.fetch_context_for_product = _original_fetch_context


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    product_input = input("Enter product to analyze (name + description): ")
    print("\nTHE WAR ROOM — Optimized (smart evidence + thermal-safe)\n")
    report = run_war_room(product_input)
    print(report)
