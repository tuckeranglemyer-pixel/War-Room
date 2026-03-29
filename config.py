"""
Thin wrapper — canonical configuration lives in ``src/inference/model_config.py``.

Multi-model defaults (DGX Spark target):
  FIRST_TIMER_MODEL  = ollama/llama3.3:70b      — broad, impressionistic (Llama)
  DAILY_DRIVER_MODEL = ollama/qwen3:32b         — precise, technical (Qwen)
  BUYER_MODEL        = ollama/mistral-small:24b — concise, business (Mistral)

Adaptive fallback (thermal constraints):
  FALLBACK_MODEL     = ollama/qwen3:32b         — all personas on one model when DGX
                                                  thermal limits prevent concurrent serving
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
    FALLBACK_MODEL,
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
    "FALLBACK_MODEL",
    "FIRST_TIMER_MODEL",
    "LOCAL_BASE_URL",
    "LOCAL_MODEL",
    "MAX_SCOUTS",
    "MAX_WORKERS",
    "RAG_RESULTS_PER_QUERY",
]
