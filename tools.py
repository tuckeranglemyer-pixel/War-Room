"""
Thin wrapper — canonical RAG and CrewAI tools live in ``src/rag/chroma_retrieval.py``.
"""

from __future__ import annotations

from src.rag.chroma_retrieval import (
    _query_collection,
    fetch_context_for_product,
    search_app_reviews,
    search_competitor_data,
    search_g2_reviews,
    search_hn_comments,
    search_pm_knowledge,
    search_reddit,
    search_screenshots,
)

__all__ = [
    "_query_collection",
    "fetch_context_for_product",
    "search_app_reviews",
    "search_competitor_data",
    "search_g2_reviews",
    "search_hn_comments",
    "search_pm_knowledge",
    "search_reddit",
    "search_screenshots",
]
