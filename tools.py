from crewai.tools import tool
import chromadb
from typing import Optional

# Shared ChromaDB client — initialized once at module load to avoid re-opening on every tool call
_chroma_client = chromadb.PersistentClient(path="./chroma_db")
_pm_tools_collection = _chroma_client.get_collection("pm_tools")


def _query_collection(query: str, n_results: int = 5, where: Optional[dict] = None) -> str:
    """Run a ChromaDB query and return consistently formatted results.

    Each chunk is rendered as:
        [APP | source_label type] rating=N url
        chunk text
    Chunks are separated by '---'.
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
    """Search Google Play reviews for productivity apps. Returns real user reviews with star ratings (2,608 reviews)."""
    return _query_collection(query, where={"source": "google_play"})


@tool("Search Reddit")
def search_reddit(query: str) -> str:
    """Search Reddit posts and comments from r/productivity, r/notion, r/projectmanagement and related subreddits (22,692 posts/comments)."""
    return _query_collection(query, where={"source": "reddit"})


@tool("Search G2 Reviews")
def search_g2_reviews(query: str) -> str:
    """Search G2 verified business user reviews for productivity apps."""
    return f"[RAG not connected yet] No results for: {query}"


@tool("Search HN Comments")
def search_hn_comments(query: str) -> str:
    """Search Hacker News stories and comments about productivity tools (6,348 entries with source URLs)."""
    return _query_collection(query, where={"source": "hackernews"})


@tool("Search Competitor Data")
def search_competitor_data(query: str) -> str:
    """Search metadata, pricing, features, and competitive comparisons for productivity apps."""
    return f"[RAG not connected yet] No results for: {query}"


@tool("Search Screenshots")
def search_screenshots(query: str) -> str:
    """Search UI screenshot descriptions and visual comparisons of competitor productivity apps."""
    return f"[RAG not connected yet] No results for: {query}"


@tool("Search PM Knowledge Base")
def search_pm_knowledge(query: str) -> str:
    """Search 31,668 chunks of real user data across 20 project management tools.
    Sources include Reddit posts/comments, Hacker News threads, Google Play reviews,
    and app metadata. Use this to ground arguments in real user evidence."""
    try:
        results = _pm_tools_collection.query(query_texts=[query], n_results=5)
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

            source_label = source
            if subreddit:
                source_label = f"reddit/r/{subreddit}"
            elif source == "hackernews":
                source_label = "Hacker News"

            header = f"[{app.upper()} | {source_label} {source_type}]"
            if url:
                header += f" {url}"

            formatted_chunks.append(f"{header}\n{doc}")

        return "\n\n---\n\n".join(formatted_chunks)

    except Exception as exc:
        return f"[ChromaDB error] {exc}"
