"""
Response synthesis and verdict extraction for War Room debate output.

Parses the free-text Round 4 (Buyer) output into machine-readable fields
so the WebSocket layer can deliver structured JSON to the frontend without
any additional LLM inference calls.

Extracted fields:
  - score: integer 1-100
  - decision: YES | NO | YES WITH CONDITIONS | UNKNOWN
  - top_3_fixes: list of up to 3 prioritized fix strings
  - full_report: the complete raw Round 4 text, unmodified
"""

from __future__ import annotations

import re
from typing import Any


def parse_verdict(raw: str) -> dict[str, Any]:
    """Best-effort extraction of score, decision, and fixes from Round 4 text.

    Args:
        raw: Final crew output as a string (the Buyer agent's complete response).

    Returns:
        Dict with ``score``, ``decision``, ``top_3_fixes``, and ``full_report`` keys.
        ``score`` defaults to 0 if no parseable number is found.
        ``decision`` defaults to ``"UNKNOWN"`` if no keyword matches.
        ``top_3_fixes`` contains at least one fallback string.
    """
    score_match = re.search(
        r"\b([1-9][0-9]?|100)\b(?=\s*(?:/100|out of 100|score))",
        raw,
        re.IGNORECASE,
    )
    score = int(score_match.group(1)) if score_match else 0

    decision = "UNKNOWN"
    for candidate in ("YES WITH CONDITIONS", "YES", "NO"):
        if candidate in raw.upper():
            decision = candidate
            break

    fixes: list[str] = []
    fixes_section = re.search(
        r"TOP 3 FIXES[:\s]*(.*?)(?:\n\n|\Z)",
        raw,
        re.IGNORECASE | re.DOTALL,
    )
    if fixes_section:
        items = re.findall(
            r"(?:^|\n)\s*\d+[.)]\s+(.+?)(?=\n\s*\d+[.)]|\Z)",
            fixes_section.group(1),
            re.DOTALL,
        )
        fixes = [item.strip() for item in items[:3]]
    if not fixes:
        fixes = ["See full report for recommended fixes."]

    return {
        "score": score,
        "decision": decision,
        "top_3_fixes": fixes,
        "full_report": raw,
    }


# Alias for backward compatibility and test import paths
_parse_verdict = parse_verdict
