# ChromaDB RAG retrieval tools — 31,668 chunks across 20 PM tools
"""
ChromaDB RAG retrieval for War Room.

Provides:
  - fetch_context_for_product(): bulk evidence pre-fetch injected directly into
    task prompts — used because small local LLMs don't reliably execute the
    ReAct tool-calling loop on their own
  - _query_collection(): raw query with optional metadata filter
  - CrewAI @tool wrappers for per-source retrieval (reddit, HN, app reviews, etc.)
  - search_pm_knowledge: unrestricted full-corpus search used in agent tool loops

The ChromaDB client and collection are initialized once at module load.
A missing collection does not crash on import — search tools return a clear
error string instead.
"""

from __future__ import annotations

from typing import Optional

import chromadb
from crewai.tools import tool

from src.inference.model_config import CHROMA_DB_PATH, COLLECTION_NAME, RAG_RESULTS_PER_QUERY

_chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
_pm_tools_collection = None
try:
    _pm_tools_collection = _chroma_client.get_collection(COLLECTION_NAME)
except Exception:
    pass


def fetch_context_for_product(
    product_name: str,
    n_results: int = RAG_RESULTS_PER_QUERY,
) -> str:
    """Pre-fetch real user evidence from ChromaDB and format it for task injection.

    Issues four targeted queries covering onboarding, bugs, strengths, and
    enterprise concerns. Deduplicates by URL. Returns a formatted block ready
    to embed verbatim in a CrewAI task description.

    Args:
        product_name: Product name and description; first token seeds the app filter.
        n_results: Maximum chunks to retrieve per internal query.

    Returns:
        Formatted evidence block, or a short placeholder if ChromaDB is unavailable.
    """
    if _pm_tools_collection is None:
        return "[ChromaDB not ready — no pre-seeded context available]"

    app_key = product_name.lower().split()[0]
    queries = [
        f"{product_name} onboarding confusing difficult first time user",
        f"{product_name} problems bugs performance slow",
        f"{product_name} love best feature positive review",
        f"{product_name} team collaboration enterprise pricing",
    ]

    seen_ids: set[str] = set()
    chunks: list[str] = []

    for query in queries:
        try:
            results = _pm_tools_collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"app": app_key},
            )
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                doc_id = meta.get("url", doc[:40])
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)

                source = meta.get("source", "unknown")
                source_type = meta.get("type", "")
                subreddit = meta.get("subreddit", "")
                url = meta.get("url") or meta.get("hn_url", "")
                rating = meta.get("rating", "")

                label = source
                if subreddit:
                    label = f"r/{subreddit}"
                elif source == "hackernews":
                    label = "Hacker News"
                elif source == "google_play":
                    label = "Google Play"

                header = f"[{label} {source_type}]"
                if rating:
                    header += f" ★{rating}"
                if url:
                    header += f" {url}"

                chunks.append(f"{header}\n{doc[:400]}")
        except Exception as exc:
            chunks.append(f"[Query error: {exc}]")

    if not chunks:
        return f"[No evidence found for '{product_name}' in knowledge base]"

    return (
        f"\n\n--- REAL USER EVIDENCE FROM KNOWLEDGE BASE ({len(chunks)} sources) ---\n\n"
        + "\n\n".join(chunks)
        + "\n\n--- END OF KNOWLEDGE BASE EVIDENCE ---\n"
    )


def _query_collection(
    query: str,
    n_results: int = RAG_RESULTS_PER_QUERY,
    where: Optional[dict] = None,
) -> str:
    """Run a ChromaDB query and return consistently formatted results.

    Args:
        query: Natural-language query text.
        n_results: Maximum documents to return.
        where: Optional ChromaDB metadata filter (e.g. ``{"source": "reddit"}``).

    Returns:
        Joined formatted chunks, or a human-readable error string.
    """
    if _pm_tools_collection is None:
        return "[ChromaDB] collection unavailable — no local database found on this host"
    try:
        kwargs: dict = {"query_texts": [query], "n_results": n_results}
        if where:
            kwargs["where"] = where

        results = _pm_tools_collection.query(**kwargs)
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]

        if not documents:
            return f"No results found for: {query}"

        formatted_chunks = []
        for doc, meta in zip(documents, metadatas):
            app = meta.get("app", "unknown")
            source = meta.get("source", "unknown")
            source_type = meta.get("type", "")
            subreddit = meta.get("subreddit", "")
            url = meta.get("url") or meta.get("hn_url", "")
            rating = meta.get("rating", "")

            source_label = source
            if subreddit:
                source_label = f"reddit/r/{subreddit}"
            elif source == "hackernews":
                source_label = "Hacker News"
            elif source == "google_play":
                source_label = "Google Play"
            elif source == "metadata":
                source_label = "App Metadata"

            header = f"[{app.upper()} | {source_label} {source_type}]"
            if rating:
                header += f" rating={rating}"
            if url:
                header += f" {url}"

            formatted_chunks.append(f"{header}\n{doc}")

        return "\n\n---\n\n".join(formatted_chunks)

    except Exception as exc:
        return f"[ChromaDB error] {exc}"


# ---------------------------------------------------------------------------
# CrewAI tool wrappers
# ---------------------------------------------------------------------------


@tool("Search App Reviews")
def search_app_reviews(query: str) -> str:
    """Search Google Play reviews (subset of the corpus).

    Args:
        query: Search string for reviews.

    Returns:
        Formatted snippets or an error string.
    """
    return _query_collection(query, where={"source": "google_play"})


@tool("Search Reddit")
def search_reddit(query: str) -> str:
    """Search Reddit posts and comments (productivity-related subreddits).

    Args:
        query: Search string for Reddit content.

    Returns:
        Formatted snippets or an error string.
    """
    return _query_collection(query, where={"source": "reddit"})


@tool("Search G2 Reviews")
def search_g2_reviews(query: str) -> str:
    """Search G2-style business reviews.

    G2 review data is not available in this dataset.
    Use search_app_reviews for mobile app reviews or search_reddit for
    community feedback instead.

    Args:
        query: Search string.

    Returns:
        Redirect message pointing to available alternatives.
    """
    return (
        "G2 reviews are not available in this dataset. "
        "Use search_app_reviews for Google Play/App Store reviews, "
        "or search_reddit for community user feedback."
    )


@tool("Search HN Comments")
def search_hn_comments(query: str) -> str:
    """Search Hacker News stories and comments.

    Args:
        query: Search string for HN content.

    Returns:
        Formatted snippets or an error string.
    """
    return _query_collection(query, where={"source": "hackernews"})


@tool("Search Competitor Data")
def search_competitor_data(query: str) -> str:
    """Search app metadata (pricing, features, categories).

    Args:
        query: Search string for metadata chunks.

    Returns:
        Formatted snippets or an error string.
    """
    return _query_collection(query, where={"source": "metadata"})


@tool("Search Screenshots")
def search_screenshots(query: str) -> str:
    """Search the 69-app UI screenshot analysis suite for competitor UI patterns.

    Uses sentence-transformer embeddings (all-MiniLM-L6-v2) over pre-analyzed
    screenshots from Airtable, Asana, Basecamp, ClickUp, Jira, Linear, Monday,
    Notion, Todoist, and Trello. Returns the 5 most similar competitor screens.

    Args:
        query: Natural-language description of the UI pattern or screen to find.

    Returns:
        Formatted competitor screenshot analyses ordered by similarity score.
    """
    try:
        from screenshot_suite.matcher import find_similar_screens  # noqa: PLC0415
    except ImportError:
        return "Screenshot suite unavailable (sentence-transformers not installed)."

    matches = find_similar_screens(query, top_k=5)
    if not matches:
        return "Screenshot suite not available or no matching screens found."

    parts = []
    for m in matches:
        parts.append(
            f"[{m['app'].upper()} | {m['filename']} | similarity: {m['similarity_score']:.3f}]\n"
            f"{m['document'][:800]}"
        )
    return "\n\n---\n\n".join(parts)


@tool("Search PM Knowledge Base")
def search_pm_knowledge(query: str) -> str:
    """Search the full pm_tools corpus without a source filter.

    Args:
        query: Natural-language query across all ingested sources.

    Returns:
        Formatted snippets or an error string.
    """
    return _query_collection(query)
