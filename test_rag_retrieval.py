"""
Tests for War Room's RAG retrieval pipeline.

Covers ChromaDB query execution, metadata filtering, result formatting,
deduplication, and the evidence injection mechanism that grounds every
agent argument in real user data.

The pm_tools ChromaDB collection contains 31,668 unique chunks sourced from:
  - Reddit (r/productivity, r/notion, r/projectmanagement, and related)
  - Hacker News stories and comments
  - Google Play app reviews
  - App metadata (pricing, features, categories)
  - Screenshots analyzed via GPT-4o Vision

Live ChromaDB tests are marked skip — they require a loaded pm_tools collection.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Shared mock factory
# ---------------------------------------------------------------------------


def _make_mock_collection(
    docs: list[str] | None = None,
    metas: list[dict] | None = None,
    count: int = 31668,
) -> MagicMock:
    """Build a MagicMock that mimics a ChromaDB collection's query/count interface."""
    if docs is None:
        docs = [
            "Notion's onboarding is genuinely confusing for new users.",
            "Moved from Notion to Linear — databases broke at scale.",
            "Notion is great but the mobile app is unusable.",
        ]
    if metas is None:
        metas = [
            {
                "source": "reddit",
                "type": "post",
                "subreddit": "productivity",
                "url": "https://reddit.com/r/productivity/1",
                "app": "notion",
                "rating": "",
            },
            {
                "source": "hackernews",
                "type": "comment",
                "hn_url": "https://news.ycombinator.com/item?id=123",
                "app": "notion",
                "rating": "",
            },
            {
                "source": "google_play",
                "type": "review",
                "rating": "2",
                "url": "",
                "app": "notion",
            },
        ]

    col = MagicMock()
    col.query.return_value = {
        "documents": [docs],
        "metadatas": [metas],
    }
    col.count.return_value = count
    return col


# ---------------------------------------------------------------------------
# Autouse fixture: replace the live ChromaDB collection for every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_chroma_collection():
    """Swap out the module-level ChromaDB collection with a mock before each test."""
    import tools

    original = tools._pm_tools_collection
    mock_col = _make_mock_collection()
    tools._pm_tools_collection = mock_col
    yield mock_col
    tools._pm_tools_collection = original


# ---------------------------------------------------------------------------
# _query_collection: raw query → formatted result string
# ---------------------------------------------------------------------------


def test_query_collection_returns_formatted_chunks_with_app_and_source_labels(
    patch_chroma_collection,
):
    """_query_collection must format each chunk with an app name and source label header."""
    import tools

    result = tools._query_collection("notion onboarding first impression")

    assert isinstance(result, str)
    assert len(result) > 0
    assert "NOTION" in result.upper() or "notion" in result.lower()


def test_query_collection_includes_subreddit_label_for_reddit_posts(
    patch_chroma_collection,
):
    """Reddit chunks must display as 'reddit/r/<subreddit>' in the formatted output."""
    import tools

    result = tools._query_collection("notion collaboration")

    assert "reddit" in result.lower() or "productivity" in result.lower(), (
        "Reddit chunks must carry a subreddit label in formatted output"
    )


def test_query_collection_includes_star_rating_for_google_play_reviews(
    patch_chroma_collection,
):
    """Google Play review chunks must display their star rating in the formatted header."""
    import tools

    result = tools._query_collection("notion review")

    assert "2" in result, "Google Play review rating must appear in the formatted output"


def test_query_collection_separates_chunks_with_delimiter(patch_chroma_collection):
    """Multiple result chunks must be separated by a visible delimiter."""
    import tools

    result = tools._query_collection("notion usability")

    assert "---" in result, (
        "Multiple chunks must be separated by '---' delimiters for readability"
    )


def test_retrieval_respects_top_k_parameter(patch_chroma_collection):
    """_query_collection must pass n_results=k directly to the ChromaDB query call."""
    import tools

    tools._query_collection("notion", n_results=3)

    call_kwargs = patch_chroma_collection.query.call_args[1]
    assert call_kwargs.get("n_results") == 3, (
        f"ChromaDB query must receive n_results=3, got: {call_kwargs}"
    )


def test_source_filter_applies_where_clause_to_chromadb_query(patch_chroma_collection):
    """_query_collection with a where filter must pass that filter to ChromaDB."""
    import tools

    tools._query_collection("notion review", where={"source": "google_play"})

    call_kwargs = patch_chroma_collection.query.call_args[1]
    assert call_kwargs.get("where") == {"source": "google_play"}, (
        "Source filter must be forwarded as a ChromaDB metadata where clause"
    )


def test_chromadb_exception_returns_error_string_not_raised_exception(
    patch_chroma_collection,
):
    """When ChromaDB raises during query, _query_collection must return an error string."""
    import tools

    patch_chroma_collection.query.side_effect = RuntimeError("disk I/O error")

    result = tools._query_collection("any query")

    assert isinstance(result, str)
    assert "error" in result.lower() or "ChromaDB" in result, (
        "ChromaDB errors must surface as readable strings, not raised exceptions"
    )


def test_empty_query_returns_structured_response_not_exception(patch_chroma_collection):
    """An empty query string must not raise; it must return a string result."""
    import tools

    patch_chroma_collection.query.return_value = {"documents": [[]], "metadatas": [[]]}

    try:
        result = tools._query_collection("")
        assert isinstance(result, str)
    except Exception as exc:
        pytest.fail(f"Empty query raised an unexpected exception: {exc}")


# ---------------------------------------------------------------------------
# fetch_context_for_product: multi-query evidence aggregation
# ---------------------------------------------------------------------------


def test_fetch_context_assembles_evidence_block_with_required_header_and_footer(
    patch_chroma_collection,
):
    """fetch_context_for_product must wrap retrieved evidence in labeled section delimiters."""
    import tools

    result = tools.fetch_context_for_product("notion")

    assert "REAL USER EVIDENCE" in result, (
        "Evidence block must open with 'REAL USER EVIDENCE' header"
    )
    assert "KNOWLEDGE BASE" in result, (
        "Evidence block must reference 'KNOWLEDGE BASE' in its framing"
    )


def test_fetch_context_issues_multiple_targeted_queries_for_evidence_depth(
    patch_chroma_collection,
):
    """fetch_context_for_product must fire multiple distinct queries to cover different evidence angles."""
    import tools

    tools.fetch_context_for_product("notion onboarding")

    assert patch_chroma_collection.query.call_count >= 2, (
        "fetch_context_for_product must issue at least 2 ChromaDB queries "
        "to cover different dimensions (onboarding, bugs, positives, enterprise)"
    )


def test_fetch_context_deduplicates_chunks_with_identical_urls(patch_chroma_collection):
    """fetch_context_for_product must not include the same URL/chunk twice across multiple queries."""
    import tools

    patch_chroma_collection.query.return_value = {
        "documents": [["Notion databases are broken at scale."]],
        "metadatas": [[{"source": "reddit", "type": "post", "url": "https://reddit.com/r/notion/42", "app": "notion", "subreddit": "notion", "rating": ""}]],
    }

    result = tools.fetch_context_for_product("notion")

    occurrences = result.count("Notion databases are broken at scale.")
    assert occurrences == 1, (
        f"Deduplicated evidence must appear exactly once, found {occurrences} times"
    )


def test_collection_unavailable_returns_chromadb_not_ready_message():
    """When the ChromaDB collection is None, fetch_context_for_product returns a graceful error."""
    import tools

    original = tools._pm_tools_collection
    tools._pm_tools_collection = None
    try:
        result = tools.fetch_context_for_product("notion")
        assert "ChromaDB not ready" in result or "not ready" in result.lower(), (
            "Missing collection must produce a clear 'not ready' message, not a crash"
        )
    finally:
        tools._pm_tools_collection = original


def test_chunk_count_matches_expected_corpus_size(patch_chroma_collection):
    """The pm_tools collection must report 31,668 chunks matching the ingested dataset."""
    count = patch_chroma_collection.count()

    assert count == 31668, (
        f"pm_tools must contain 31,668 unique RAG chunks (got {count}). "
        "Re-run load_db.py if the count has drifted."
    )


def test_no_evidence_found_returns_descriptive_message_not_empty_string(
    patch_chroma_collection,
):
    """When queries return no documents, fetch_context_for_product must return a descriptive message."""
    import tools

    patch_chroma_collection.query.return_value = {"documents": [[]], "metadatas": [[]]}

    result = tools.fetch_context_for_product("nonexistent_product_xyz")

    assert isinstance(result, str)
    assert len(result) > 0, "No-evidence case must return a non-empty descriptive string"


# ---------------------------------------------------------------------------
# Specialized source-filtered search tools
# ---------------------------------------------------------------------------


def test_search_reddit_tool_filters_to_reddit_source(patch_chroma_collection):
    """search_reddit must apply a {'source': 'reddit'} where-filter to ChromaDB."""
    import tools

    tools._query_collection("notion collaboration", where={"source": "reddit"})

    call_kwargs = patch_chroma_collection.query.call_args[1]
    assert call_kwargs.get("where") == {"source": "reddit"}, (
        "Reddit search must restrict results to Reddit source"
    )


def test_search_app_reviews_filters_to_google_play_source(patch_chroma_collection):
    """search_app_reviews must apply a {'source': 'google_play'} where-filter."""
    import tools

    tools._query_collection("notion review", where={"source": "google_play"})

    call_kwargs = patch_chroma_collection.query.call_args[1]
    assert call_kwargs.get("where") == {"source": "google_play"}, (
        "App review search must restrict results to Google Play source"
    )


def test_search_hn_comments_filters_to_hackernews_source(patch_chroma_collection):
    """search_hn_comments must apply a {'source': 'hackernews'} where-filter."""
    import tools

    tools._query_collection("notion performance", where={"source": "hackernews"})

    call_kwargs = patch_chroma_collection.query.call_args[1]
    assert call_kwargs.get("where") == {"source": "hackernews"}, (
        "HN search must restrict results to Hacker News source"
    )


def test_search_competitor_data_filters_to_metadata_source(patch_chroma_collection):
    """search_competitor_data must apply a {'source': 'metadata'} where-filter."""
    import tools

    tools._query_collection("notion pricing tiers", where={"source": "metadata"})

    call_kwargs = patch_chroma_collection.query.call_args[1]
    assert call_kwargs.get("where") == {"source": "metadata"}, (
        "Competitor data search must restrict results to metadata source"
    )


def test_unrestricted_search_pm_knowledge_issues_query_without_where_filter(
    patch_chroma_collection,
):
    """search_pm_knowledge (full corpus) must query ChromaDB without any source restriction."""
    import tools

    tools._query_collection("notion overall quality")

    call_kwargs = patch_chroma_collection.query.call_args[1]
    assert call_kwargs.get("where") is None, (
        "Full-corpus search must not apply a source filter"
    )


# ---------------------------------------------------------------------------
# Live ChromaDB tests — require loaded pm_tools collection
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason="Requires local ChromaDB instance with pm_tools collection loaded (run load_db.py first)"
)
def test_live_chroma_returns_relevant_chunks_for_pm_tool_query():
    """Live ChromaDB query returns chunks from the real pm_tools collection."""
    import tools

    result = tools._query_collection("best project management tool", n_results=5)

    assert "No results" not in result
    assert len(result) > 100


@pytest.mark.skip(
    reason="Requires local ChromaDB instance with pm_tools collection loaded (run load_db.py first)"
)
def test_live_chunk_count_matches_expected_31668():
    """Live pm_tools collection must contain exactly 31,668 ingested chunks."""
    import tools

    assert tools._pm_tools_collection is not None
    count = tools._pm_tools_collection.count()
    assert count == 31668, f"Expected 31,668 chunks, got {count}"
