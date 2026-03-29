"""Shared utility functions used across the War Room pipeline."""

from __future__ import annotations

from typing import Any


def strip_markdown_fences(content: str) -> str:
    """Remove markdown code fences that LLMs sometimes wrap around JSON output.

    Handles ```json, plain ```, and trailing ``` markers.
    """
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def clamp_score(raw_score: Any, max_val: float = 10.0) -> float:
    """Normalise an LLM-returned score to 0–max_val.

    Models sometimes return 0-100 despite being asked for 0-10.
    """
    try:
        value = float(raw_score)
    except (TypeError, ValueError):
        return 0.0
    if value > max_val:
        return round(value / 10, 1)
    return value
