"""
ChromaDB-backed RAG tools for The War Room.

Provides CrewAI ``@tool`` search functions and ``fetch_context_for_product`` for
injecting retrieved evidence directly into task prompts when tool loops are weak.
"""

from __future__ import annotations

from typing import Optional

import chromadb
from crewai.tools import tool

from config import CHROMA_DB_PATH, COLLECTION_NAME, RAG_RESULTS_PER_QUERY

# Shared ChromaDB client — initialized once at module load to avoid re-opening on every tool call.
# Collection access is deferred to call time so a missing collection does not crash on import.
_chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
_pm_tools_collection = None
try:
    _pm_tools_collection = _chroma_client.get_collection(COLLECTION_NAME)
except Exception:
    pass  # Collection not yet loaded; search tools return a clear error message


def fetch_context_for_product(
    product_name: str,
    n_results: int = RAG_RESULTS_PER_QUERY,
) -> str:
    """Pre-fetch real user evidence from ChromaDB and format it for task injection.

    Guarantees real evidence is available even when the local LLM does not reliably
    execute the ReAct tool-calling loop.

    Args:
        product_name: Product name and description; first token seeds the ``app`` filter.
        n_results: Maximum chunks to retrieve per internal query.

    Returns:
        A formatted evidence block, or a short placeholder if ChromaDB is unavailable
        or no documents match.
    """
    if _pm_tools_collection is None:
        return "[ChromaDB not ready — no pre-seeded context available]"

    app_key = product_name.lower().split()[0]  # "notion" from "Notion — ..."
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
        where: Optional ChromaDB metadata filter.

    Returns:
        Joined formatted chunks, or a human-readable error string.
    """
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
    """Search G2-style business reviews (stub until wired to a G2 collection).

    Args:
        query: Search string.

    Returns:
        Placeholder message until the G2 pipeline is connected.
    """
    return f"[RAG not connected yet] No results for: {query}"


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
    """Search UI screenshot descriptions (stub until wired).

    Args:
        query: Search string.

    Returns:
        Placeholder message until screenshot embeddings are connected.
    """
    return f"[RAG not connected yet] No results for: {query}"


@tool("Search PM Knowledge Base")
def search_pm_knowledge(query: str) -> str:
    """Search the full pm_tools corpus without a source filter.

    Args:
        query: Natural-language query across all ingested sources.

    Returns:
        Formatted snippets or an error string.
    """
    return _query_collection(query)


@tool("Search User Uploads")
def search_user_uploads(query: str) -> str:
    """Search user-uploaded screenshots and video frames for this session.

    Args:
        query: Search string for user-provided visual evidence.

    Returns:
        Formatted snippets or an error string.
    """
    return _query_collection(
        query,
        n_results=RAG_RESULTS_PER_QUERY,
        where={"source": "user_upload"},
    )


def create_session_user_upload_tool(session_id: str):
    """Return a session-scoped variant of the user-uploads search tool.

    The returned tool filters ChromaDB results to documents that match BOTH
    ``source == "user_upload"`` AND ``session_id == <session_id>``, so agents
    only see evidence from the specific ingest run tied to this debate.

    Args:
        session_id: The upload session UUID returned by ``POST /api/ingest/video``.

    Returns:
        A ``@tool``-decorated function ready to pass to a CrewAI ``Agent``.
    """

    @tool("Search User Uploads")
    def search_user_uploads_session(query: str) -> str:
        """Search user-uploaded screenshots and video frames scoped to this session.

        Args:
            query: Search string for user-provided visual evidence.

        Returns:
            Formatted snippets or an error string.
        """
        return _query_collection(
            query,
            n_results=RAG_RESULTS_PER_QUERY,
            where={
                "$and": [
                    {"source": {"$eq": "user_upload"}},
                    {"session_id": {"$eq": session_id}},
                ]
            },
        )

    return search_user_uploads_session


@tool("Search User Context")
def search_user_context(query: str) -> str:
    """Search structured onboarding context supplied by the user.

    Args:
        query: Search string for user context chunks.

    Returns:
        Formatted snippets or an error string.
    """
    return _query_collection(
        query,
        n_results=3,
        where={"source": "user_context"},
    )
