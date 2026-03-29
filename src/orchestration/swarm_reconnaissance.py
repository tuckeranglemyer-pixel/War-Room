"""
Swarm reconnaissance — parallel evidence gathering before the adversarial debate.

Spawns multiple scout threads, each targeting a different product facet, and
compiles results into a structured briefing that seeds Round 1. Running 20
scouts in parallel against 31K ChromaDB chunks takes ~1-2 seconds on the DGX
versus ~40 seconds serially.

The briefing is injected verbatim into the Round 1 task description so the
First-Timer agent begins with a pre-loaded intelligence dossier rather than
starting the debate from zero.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.inference.model_config import MAX_SCOUTS, MAX_WORKERS
from src.rag.chroma_retrieval import search_pm_knowledge

SCOUT_QUERIES = [
    "{product} onboarding first impression new user experience",
    "{product} pricing cost team enterprise plan",
    "{product} mobile app performance speed",
    "{product} integrations API third party apps",
    "{product} bugs crashes data loss reliability",
    "{product} customer support response help",
    "{product} compared to competitors alternative switch",
    "{product} missing features feature request wishlist",
    "{product} UI design interface confusing navigation",
    "{product} collaboration team sharing permissions",
    "{product} data export import migration lock-in",
    "{product} notifications alerts overwhelming noise",
    "{product} search functionality find content",
    "{product} offline access sync issues",
    "{product} learning curve documentation tutorial",
    "{product} updates changes breaking workflow",
    "{product} security privacy concerns",
    "{product} customization templates flexibility",
    "{product} automation workflow integration",
    "{product} free vs paid limitations paywall",
]


def run_scout(query: str) -> dict[str, Any]:
    """Execute a single scout query against the PM knowledge base.

    Args:
        query: Pre-formatted search string for one product facet.

    Returns:
        Dict with ``query``, ``evidence``, ``elapsed`` seconds, and ``status``.
    """
    start = time.time()
    try:
        result = search_pm_knowledge(query)
        return {
            "query": query,
            "evidence": result,
            "elapsed": round(time.time() - start, 2),
            "status": "success",
        }
    except Exception as exc:
        return {
            "query": query,
            "evidence": f"[Scout failed: {exc}]",
            "elapsed": round(time.time() - start, 2),
            "status": "error",
        }


def deploy_swarm(
    product_name: str,
    max_scouts: int = MAX_SCOUTS,
    max_workers: int = MAX_WORKERS,
) -> dict[str, Any]:
    """Deploy parallel scout agents to gather evidence before the debate begins.

    Args:
        product_name: Product label inserted into each scout query template.
        max_scouts: Number of scout queries to run (capped by SCOUT_QUERIES length).
        max_workers: Thread pool size for concurrent scouts.

    Returns:
        Dict with ``briefing`` (compiled markdown) and ``stats`` (timing and counts).
    """
    print(f"\n🐝 DEPLOYING SWARM — {max_scouts} scouts searching 31,668 chunks...")
    print(f"   Target: {product_name}")
    print(f"   Parallel workers: {max_workers}\n")

    queries = [q.format(product=product_name) for q in SCOUT_QUERIES[:max_scouts]]
    results: list[dict[str, Any]] = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_scout, q): q for q in queries}
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            status = "✓" if result["status"] == "success" else "✗"
            print(f"   [{i:>2}/{max_scouts}] {status} {result['query'][:60]}... ({result['elapsed']}s)")

    total_time = round(time.time() - start, 2)
    successful = sum(1 for r in results if r["status"] == "success")

    evidence_sections = []
    for r in results:
        if (
            r["status"] == "success"
            and "[RAG not connected" not in r["evidence"]
            and "[ChromaDB]" not in r["evidence"]
        ):
            evidence_sections.append(f"### {r['query']}\n{r['evidence']}")

    briefing = (
        f"# SWARM RECONNAISSANCE BRIEFING\n"
        f"## Product: {product_name}\n"
        f"## Scouts Deployed: {max_scouts} | Successful: {successful} | Time: {total_time}s\n\n"
        f"The following evidence was gathered by {max_scouts} parallel research agents "
        f"scanning 31,668 real user reviews from Reddit, Hacker News, Google Play, and "
        f"app metadata databases. This briefing feeds into the adversarial debate.\n\n"
        f"---\n\n"
        + "\n\n---\n\n".join(evidence_sections)
    )

    print(f"\n🐝 SWARM COMPLETE — {successful}/{max_scouts} scouts returned evidence in {total_time}s")
    print(f"   Briefing: {len(briefing)} characters of compiled evidence\n")

    return {
        "briefing": briefing,
        "stats": {
            "scouts_deployed": max_scouts,
            "scouts_successful": successful,
            "total_time": total_time,
            "product": product_name,
        },
    }


if __name__ == "__main__":
    product = input("Enter product to scout: ")
    result = deploy_swarm(product)
    print("\n" + "=" * 60)
    print(result["briefing"][:2000] + "\n...")
