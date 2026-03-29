# Multi-model inference configuration — three distinct LLM families
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
    """Return the repository root (two levels above this file)."""
    return Path(__file__).resolve().parents[2]


def _load_env() -> None:
    """Load .env from the repository root if present."""
    load_dotenv(_repo_root() / ".env")


def _get_str(key: str, default: str) -> str:
    """Return a non-empty env var string, or default if unset or blank."""
    raw = os.environ.get(key)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


def _get_int(key: str, default: int) -> int:
    """Return an env var parsed as int, or default if unset, blank, or non-numeric."""
    raw = os.environ.get(key)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


_load_env()

# ---------------------------------------------------------------------------
# Local dev defaults (small utility model for persona generation + swarm)
# ---------------------------------------------------------------------------

LOCAL_MODEL = _get_str("LOCAL_MODEL", "ollama/llama3.1:8b")
LOCAL_BASE_URL = _get_str("LOCAL_BASE_URL", "http://localhost:11434")

# ---------------------------------------------------------------------------
# Per-agent model assignments — three distinct architectures for adversarial debate
#
# DGX Spark defaults (full three-model config):
#   First-Timer  → Llama 3.3 70B  (~38 GB INT4)  — broad, impressionistic
#   Daily Driver → Qwen3 32B      (~18 GB INT4)  — precise, technical
#   Buyer        → Mistral 24B    (~14 GB INT4)  — concise, business-focused
#
# Local dev override: set all three to a smaller model via env vars, e.g.
#   FIRST_TIMER_MODEL=ollama/llama3.1:8b DAILY_DRIVER_MODEL=ollama/llama3.1:8b ...
# ---------------------------------------------------------------------------

FIRST_TIMER_MODEL = _get_str("FIRST_TIMER_MODEL", "ollama/llama3.3:70b")
DAILY_DRIVER_MODEL = _get_str("DAILY_DRIVER_MODEL", "ollama/qwen3:32b")
BUYER_MODEL = _get_str("BUYER_MODEL", "ollama/mistral-small:24b")

# Adaptive fallback — all personas route through one model when DGX thermal
# constraints prevent concurrent multi-model serving. Multi-model is the design
# intent; single-model rotation is the engineering response to hardware limits.
FALLBACK_MODEL = _get_str("FALLBACK_MODEL", "ollama/qwen3:32b")

# Legacy alias kept for backward compatibility with any scripts that reference it.
DAILY_DRIVER_BUYER_MODEL = DAILY_DRIVER_MODEL

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
