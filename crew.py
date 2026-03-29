"""
Thin wrapper — canonical CrewAI orchestration lives in
``src/orchestration/adversarial_debate_engine.py``.
"""

from __future__ import annotations

from src.orchestration.adversarial_debate_engine import (
    build_crew,
    buyer_llm,
    daily_driver_buyer_llm,
    daily_driver_llm,
    first_timer_llm,
    local_llm,
)

__all__ = [
    "build_crew",
    "buyer_llm",
    "daily_driver_buyer_llm",
    "daily_driver_llm",
    "first_timer_llm",
    "local_llm",
]
