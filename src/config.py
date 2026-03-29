"""
Configuration for the War Room parallel analysis pipeline.

Supports two execution modes:
  dgx   — Local Ollama on DGX Spark (default: qwen3:32b). Sequential with thermal management.
  cloud — OpenAI API (gpt-4o). Parallel execution, no thermal constraints.

Toggle via WAR_ROOM_MODE env var, or at runtime via POST /api/config/mode/{mode}.
"""

from __future__ import annotations

import os

from src.inference.model_config import _get_str, _get_int  # noqa: PLC2701


# ---------------------------------------------------------------------------
# Execution mode
# ---------------------------------------------------------------------------

# "dgx" for local Ollama on DGX Spark, "cloud" for OpenAI API
EXECUTION_MODE: str = os.environ.get("WAR_ROOM_MODE", "cloud")

# ---------------------------------------------------------------------------
# Per-mode endpoint configs
# ---------------------------------------------------------------------------

DGX_CONFIG: dict[str, dict[str, str]] = {
    "strategist": {
        "url": "http://localhost:11434/v1/chat/completions",
        "model": os.environ.get("WAR_ROOM_MODEL", "qwen3:32b"),
    },
    "ux_analyst": {
        "url": "http://localhost:11434/v1/chat/completions",
        "model": os.environ.get("WAR_ROOM_MODEL", "qwen3:32b"),
    },
    "market_researcher": {
        "url": "http://localhost:11434/v1/chat/completions",
        "model": os.environ.get("WAR_ROOM_MODEL", "qwen3:32b"),
    },
}

CLOUD_CONFIG: dict[str, dict[str, str]] = {
    "strategist": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o",
    },
    "ux_analyst": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o",
    },
    "market_researcher": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o",
    },
}


def get_endpoints() -> dict[str, dict[str, str]]:
    """Return the active endpoint config for the current execution mode."""
    if EXECUTION_MODE == "dgx":
        return DGX_CONFIG
    return CLOUD_CONFIG


# ---------------------------------------------------------------------------
# Hardware governor flags — only meaningful in DGX mode
# ---------------------------------------------------------------------------

# Thermal governor and cooling pauses are only active in DGX mode.
# These are updated together with EXECUTION_MODE by the /api/config/mode endpoint.
THERMAL_GOVERNOR_ENABLED: bool = EXECUTION_MODE == "dgx"
COOLING_ENABLED: bool = EXECUTION_MODE == "dgx"

# ---------------------------------------------------------------------------
# Legacy vLLM endpoints — kept for backward compatibility with other modules
# that import VLLM_ENDPOINTS directly.
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

CHALLENGE_ENDPOINT = VLLM_ENDPOINTS["strategist"]

# Frame extraction settings
MAX_FRAMES = _get_int("MAX_FRAMES", 10)

# Similarity threshold — don't include matches below this
MIN_SIMILARITY_THRESHOLD = float(_get_str("MIN_SIMILARITY_THRESHOLD", "0.50"))
