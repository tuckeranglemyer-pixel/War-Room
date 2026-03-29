"""
Model and runtime configuration for War Room.

Loads optional ``.env`` from the project root (``python-dotenv``), then applies
defaults. Override via environment variables for deployment without editing code.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover

    def load_dotenv(*_a: object, **_k: object) -> bool:
        return False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_env() -> None:
    load_dotenv(_repo_root() / ".env")


def _get_str(key: str, default: str) -> str:
    raw = os.environ.get(key)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


def _get_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


_load_env()

# ---------------------------------------------------------------------------
# Local dev defaults (small models, single Ollama instance)
# ---------------------------------------------------------------------------

LOCAL_MODEL = _get_str("LOCAL_MODEL", "ollama/llama3.1:8b")
LOCAL_BASE_URL = _get_str("LOCAL_BASE_URL", "http://localhost:11434")
# Daily Driver and Buyer share this model in dev; First-Timer uses LOCAL_MODEL.
DAILY_DRIVER_BUYER_MODEL = _get_str("DAILY_DRIVER_BUYER_MODEL", "ollama/llama3.3:60b")

# ---------------------------------------------------------------------------
# DGX Spark production model assignments
# ---------------------------------------------------------------------------
# FIRST_TIMER_MODEL  = "ollama/llama3.3:70b"   # port 8001
# DAILY_DRIVER_MODEL = "ollama/qwen3:32b"       # port 8002
# BUYER_MODEL        = "ollama/mistral-small:24b" # port 8003

# ---------------------------------------------------------------------------
# RAG / ChromaDB
# ---------------------------------------------------------------------------

CHROMA_DB_PATH = _get_str("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = _get_str("COLLECTION_NAME", "pm_tools")
RAG_RESULTS_PER_QUERY = _get_int("RAG_RESULTS_PER_QUERY", 5)

# ---------------------------------------------------------------------------
# Swarm reconnaissance
# ---------------------------------------------------------------------------

MAX_SCOUTS = _get_int("MAX_SCOUTS", 20)
MAX_WORKERS = _get_int("MAX_WORKERS", 10)

# ---------------------------------------------------------------------------
# API server
# ---------------------------------------------------------------------------

API_HOST = _get_str("API_HOST", "0.0.0.0")
API_PORT = _get_int("API_PORT", 8000)
