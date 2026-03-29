"""
Thin wrapper — canonical configuration lives in ``src/inference/model_config.py``.
"""

from __future__ import annotations

from src.inference.model_config import (
    API_HOST,
    API_PORT,
    BUYER_MODEL,
    CHROMA_DB_PATH,
    COLLECTION_NAME,
    DAILY_DRIVER_BUYER_MODEL,
    DAILY_DRIVER_MODEL,
    FIRST_TIMER_MODEL,
    LOCAL_BASE_URL,
    LOCAL_MODEL,
    MAX_SCOUTS,
    MAX_WORKERS,
    RAG_RESULTS_PER_QUERY,
)

__all__ = [
    "API_HOST",
    "API_PORT",
    "BUYER_MODEL",
    "CHROMA_DB_PATH",
    "COLLECTION_NAME",
    "DAILY_DRIVER_BUYER_MODEL",
    "DAILY_DRIVER_MODEL",
    "FIRST_TIMER_MODEL",
    "LOCAL_BASE_URL",
    "LOCAL_MODEL",
    "MAX_SCOUTS",
    "MAX_WORKERS",
    "RAG_RESULTS_PER_QUERY",
]
