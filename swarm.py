"""
Swarm Reconnaissance — Parallel evidence gathering before the 3-agent debate.
Spawns multiple 'scout' queries across the RAG knowledge base, each targeting
a different product facet. Compiles results into a structured evidence briefing
that feeds into Round 1 context.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tools import search_pm_knowledge

# Each scout targets a different product dimension
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


def run_scout(query: str) -> dict:
    """Single scout agent — searches the knowledge base for one facet."""
    start = time.time()
    try:
        result = search_pm_knowledge(query)
        return {
            "query": query,
            "evidence": result,
            "elapsed": round(time.time() - start, 2),
            "status": "success"
        }
    except Exception as e:
        return {
            "query": query,
            "evidence": f"[Scout failed: {e}]",
            "elapsed": round(time.time() - start, 2),
            "status": "error"
        }


def deploy_swarm(product_name: str, max_scouts: int = 20, max_workers: int = 10) -> dict:
    """
    Deploy a reconnaissance swarm of parallel search agents.

    Args:
        product_name: The product being analyzed
        max_scouts: Number of scout queries to run (default 20)
        max_workers: Parallel thread count (default 10)

    Returns:
        Structured evidence briefing with all scout results compiled
    """
    print(f"\n🐝 DEPLOYING SWARM — {max_scouts} scouts searching 31,668 chunks...")
    print(f"   Target: {product_name}")
    print(f"   Parallel workers: {max_workers}\n")

    # Generate product-specific queries
    queries = [q.format(product=product_name) for q in SCOUT_QUERIES[:max_scouts]]

    results = []
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

    # Compile evidence briefing — skip stub/placeholder responses
    evidence_sections = []
    for r in results:
        if r["status"] == "success" and "[RAG not connected" not in r["evidence"] and "[ChromaDB]" not in r["evidence"]:
            evidence_sections.append(f"### {r['query']}\n{r['evidence']}")

    briefing = f"""# SWARM RECONNAISSANCE BRIEFING
## Product: {product_name}
## Scouts Deployed: {max_scouts} | Successful: {successful} | Time: {total_time}s

The following evidence was gathered by {max_scouts} parallel research agents \
scanning 31,668 real user reviews from Reddit, Hacker News, Google Play, and \
app metadata databases. This briefing feeds into the adversarial debate.

---

""" + "\n\n---\n\n".join(evidence_sections)

    print(f"\n🐝 SWARM COMPLETE — {successful}/{max_scouts} scouts returned evidence in {total_time}s")
    print(f"   Briefing: {len(briefing)} characters of compiled evidence\n")

    return {
        "briefing": briefing,
        "stats": {
            "scouts_deployed": max_scouts,
            "scouts_successful": successful,
            "total_time": total_time,
            "product": product_name
        }
    }


if __name__ == "__main__":
    product = input("Enter product to scout: ")
    result = deploy_swarm(product)
    print("\n" + "=" * 60)
    print(result["briefing"][:2000] + "\n...")
