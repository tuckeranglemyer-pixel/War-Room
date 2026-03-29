"""
Comparison builder — side-by-side card generator.

Takes curated theme evidence (from evidence_curator) and a pair of analyses
(user frame + matched competitor screenshot) and produces a structured
comparison card ready for frontend rendering and agent context injection.

Each card contains:
    - user_side: structured observations about the user's screen
    - competitor_side: structured observations about the competitor's screen
    - match_reasoning: why these screens are comparable (GPT-4o-mini)
    - actionable_insight: what to do based on market reception (GPT-4o-mini)
    - market_evidence: curated reviews per theme with sentiment verdicts
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_openai_client: OpenAI | None = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    return _openai_client


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

EXTRACT_PROMPT = """\
From this UX analysis, extract:
1. screen_label: A short label for this screen \
(e.g. "Dashboard — Main View", "Onboarding — Step 2", "Settings — Integrations")
2. key_observations: Exactly 3 bullet points — the most important UX observations. \
Each under 15 words.

UX ANALYSIS:
{analysis}

Output ONLY valid JSON, no markdown fences:
{{"screen_label": "...", "key_observations": ["...", "...", "..."]}}"""


CARD_SYNTHESIS_PROMPT = """\
You are writing a comparison card for a product founder.

USER'S PRODUCT: {product_description}
TARGET USER: {target_user}
DIFFERENTIATOR: {differentiator}

USER'S SCREEN ANALYSIS:
{user_frame_analysis}

MATCHED COMPETITOR SCREEN ({app}):
{competitor_analysis}

SHARED THEMES AND SUPPORTING REVIEWS:
{curated_evidence_json}

Write two things:
1. match_reasoning (2-3 sentences): WHY these screens are comparable, what specific UI \
patterns they share, and why this comparison matters for THIS founder's product and target user.
2. actionable_insight (2-3 sentences): Based on how real users responded to the competitor's \
version of this pattern (cite specific review sentiment from above), what should the founder DO? \
Be specific — reference the competitor's design choice and its market reception.

Output ONLY valid JSON, no markdown fences:
{{"match_reasoning": "...", "actionable_insight": "..."}}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> Any:
    """Extract a JSON object or array from potentially markdown-wrapped LLM output."""
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for start_ch, end_ch in [("{", "}"), ("[", "]")]:
        start = text.find(start_ch)
        end = text.rfind(end_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def _extract_structure(analysis: str) -> dict[str, Any]:
    """Extract screen_label and key_observations from a UX analysis string.

    Returns a dict with keys ``screen_label`` and ``key_observations``.
    Falls back to safe defaults on any failure.
    """
    prompt = EXTRACT_PROMPT.format(analysis=analysis[:2000])
    try:
        response = _get_openai().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.2,
        )
        raw = response.choices[0].message.content or ""
        parsed = _extract_json(raw)
        if isinstance(parsed, dict):
            obs = parsed.get("key_observations", [])
            return {
                "screen_label": str(parsed.get("screen_label", "Unknown Screen")),
                "key_observations": [str(o) for o in obs[:3]],
            }
    except Exception as exc:
        print(f"   WARNING: Structure extraction failed: {exc}")
    return {"screen_label": "Unknown Screen", "key_observations": []}


def _synthesize_narrative(
    user_context: dict[str, Any],
    user_frame_analysis: str,
    competitor_match: dict[str, Any],
    curated_themes: list[dict[str, Any]],
) -> dict[str, str]:
    """Generate match_reasoning and actionable_insight via GPT-4o-mini.

    Returns dict with keys ``match_reasoning`` and ``actionable_insight``.
    Falls back to empty strings on any failure.
    """
    # Condense curated themes to stay within token budget
    curated_summary = json.dumps(
        [
            {
                "theme": t["theme_name"],
                "user": t["user_observation"],
                "competitor": t["competitor_observation"],
                "top_reviews": [
                    {"text": r["text"][:200], "sentiment": r["sentiment"]}
                    for r in t.get("supporting_reviews", [])[:2]
                ],
            }
            for t in curated_themes[:3]
        ],
        indent=2,
    )
    prompt = CARD_SYNTHESIS_PROMPT.format(
        product_description=str(user_context.get("productDescription", ""))[:500],
        target_user=user_context.get("target_user", "not specified"),
        differentiator=user_context.get("differentiator", "not specified"),
        user_frame_analysis=user_frame_analysis[:1500],
        app=competitor_match.get("app", "unknown"),
        competitor_analysis=competitor_match.get("document", "")[:1500],
        curated_evidence_json=curated_summary,
    )
    try:
        response = _get_openai().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.4,
        )
        raw = response.choices[0].message.content or ""
        parsed = _extract_json(raw)
        if isinstance(parsed, dict):
            return {
                "match_reasoning": str(parsed.get("match_reasoning", "")),
                "actionable_insight": str(parsed.get("actionable_insight", "")),
            }
    except Exception as exc:
        print(f"   WARNING: Card narrative synthesis failed: {exc}")
    return {"match_reasoning": "", "actionable_insight": ""}


def _build_market_evidence(
    curated_themes: list[dict[str, Any]],
    app: str,
) -> list[dict[str, Any]]:
    """Convert curated themes into the market_evidence list for a card."""
    evidence: list[dict[str, Any]] = []
    for theme in curated_themes[:3]:
        reviews = theme.get("supporting_reviews", [])
        pos = sum(1 for r in reviews if r.get("sentiment") == "positive")
        neg = sum(1 for r in reviews if r.get("sentiment") == "negative")
        total = len(reviews)
        if pos > neg:
            verdict = "positive"
        elif neg > pos:
            verdict = "negative"
        else:
            verdict = "mixed"
        pos_pct = round(100 * pos / total) if total else 0
        review_summary = (
            f"{app.capitalize()} users are {pos_pct}% positive on "
            f"'{theme['theme_name']}' based on {total} reviews."
        )
        evidence.append(
            {
                "theme": theme["theme_name"],
                "verdict": verdict,
                "review_summary": review_summary,
                "reviews": [
                    {
                        "text": r["text"][:300],
                        "source": r.get("source", "unknown"),
                        "sentiment": r.get("sentiment", "neutral"),
                    }
                    for r in reviews[:3]
                ],
            }
        )
    return evidence


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_comparison_card(
    frame_number: int,
    user_analysis: str,
    competitor_match: dict[str, Any],
    curated_themes: list[dict[str, Any]],
    user_context: dict[str, Any],
    card_index: int = 0,
    user_frame_image_path: str = "",
) -> dict[str, Any]:
    """Build a single side-by-side comparison card.

    Args:
        frame_number: Which video frame this card corresponds to.
        user_analysis: The ``ux_analysis`` string for the user's frame.
        competitor_match: A result from ``matcher.find_similar_screens``:
            {app, filename, similarity_score, document}.
        curated_themes: Output from ``evidence_curator.curate_evidence``.
        user_context: Onboarding answers (productDescription, target_user, …).
        card_index: Zero-based index used to generate the card_id.

    Returns:
        Fully structured comparison card dict suitable for JSON serialisation.
    """
    app = competitor_match.get("app", "unknown")
    competitor_doc = competitor_match.get("document", "")

    # Two GPT-4o-mini calls: structure extraction for both sides
    user_struct = _extract_structure(user_analysis)
    competitor_struct = _extract_structure(competitor_doc)

    # One GPT-4o-mini call: match_reasoning + actionable_insight
    narrative = _synthesize_narrative(user_context, user_analysis, competitor_match, curated_themes)

    market_evidence = _build_market_evidence(curated_themes, app)

    return {
        "card_id": f"comparison_{card_index:03d}",
        "user_side": {
            "frame_number": frame_number,
            "image_path": user_frame_image_path,
            "screen_label": user_struct["screen_label"],
            "key_observations": user_struct["key_observations"],
        },
        "competitor_side": {
            "app": app,
            "filename": competitor_match.get("filename", ""),
            # image_path constructed once in matcher.find_similar_screens and passed through.
            "image_path": competitor_match.get("image_path", ""),
            "screen_label": competitor_struct["screen_label"],
            "similarity_score": float(competitor_match.get("similarity_score", 0.0)),
            "key_observations": competitor_struct["key_observations"],
        },
        "match_reasoning": narrative["match_reasoning"],
        "actionable_insight": narrative["actionable_insight"],
        "market_evidence": market_evidence,
    }
