"""
Configuration for the War Room parallel analysis pipeline.

Update VLLM_ENDPOINTS if model ports change on the DGX Spark.
These are separate from the Ollama-based dev settings in
``src/inference/model_config.py``; both configs coexist so the legacy
debate engine and the new parallel pipeline can run side by side.
"""

from __future__ import annotations

import os

from src.inference.model_config import _get_str, _get_int  # noqa: PLC2701


# ---------------------------------------------------------------------------
# vLLM endpoints — three specialist roles mapped to distinct model defaults
# Adaptive fallback routes all through FALLBACK_MODEL when DGX thermal constraints require it
# ---------------------------------------------------------------------------

VLLM_ENDPOINTS = {
    "strategist": {
        "url": "http://localhost:11434/v1/chat/completions",
        "model": _get_str("FIRST_TIMER_MODEL", "ollama/llama3.3:70b"),
    },
    "ux_analyst": {
        "url": "http://localhost:11434/v1/chat/completions",
        "model": _get_str("DAILY_DRIVER_MODEL", "ollama/qwen3:32b"),
    },
    "market_researcher": {
        "url": "http://localhost:11434/v1/chat/completions",
        "model": _get_str("BUYER_MODEL", "ollama/mistral-small:24b"),
    },
}

# Challenge pass reuses the Strategist endpoint
CHALLENGE_ENDPOINT = VLLM_ENDPOINTS["strategist"]

# Frame extraction settings
MAX_FRAMES = _get_int("MAX_FRAMES", 10)

# Similarity threshold — don't include matches below this
MIN_SIMILARITY_THRESHOLD = float(_get_str("MIN_SIMILARITY_THRESHOLD", "0.50"))
