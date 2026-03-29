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
# vLLM endpoints — one per specialist model on the DGX Spark
# ---------------------------------------------------------------------------

VLLM_ENDPOINTS = {
    "strategist": {
        "url": _get_str("VLLM_STRATEGIST_URL", "http://localhost:8001/v1/chat/completions"),
        "model": _get_str("VLLM_STRATEGIST_MODEL", "meta-llama/Llama-3.1-70B-Instruct"),
    },
    "ux_analyst": {
        "url": _get_str("VLLM_UX_ANALYST_URL", "http://localhost:8002/v1/chat/completions"),
        "model": _get_str("VLLM_UX_ANALYST_MODEL", "Qwen/Qwen2.5-32B-Instruct"),
    },
    "market_researcher": {
        "url": _get_str("VLLM_MARKET_RESEARCHER_URL", "http://localhost:8003/v1/chat/completions"),
        "model": _get_str("VLLM_MARKET_RESEARCHER_MODEL", "mistralai/Mistral-Small-24B-Instruct-2501"),
    },
}

# Challenge pass reuses the Strategist endpoint (Llama 70B)
CHALLENGE_ENDPOINT = VLLM_ENDPOINTS["strategist"]

# Frame extraction settings
MAX_FRAMES = _get_int("MAX_FRAMES", 10)

# Similarity threshold — don't include matches below this
MIN_SIMILARITY_THRESHOLD = float(_get_str("MIN_SIMILARITY_THRESHOLD", "0.50"))
