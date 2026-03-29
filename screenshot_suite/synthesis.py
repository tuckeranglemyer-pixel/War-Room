"""
Evidence synthesis pipeline orchestrator.

Ties evidence_curator and comparison_builder together to produce:
    - Structured comparison cards (for frontend rendering via GET /api/comparisons/{id})
    - A condensed agent brief (for injection into debate task descriptions)

Called from server.py after video frame analysis and screenshot matching complete,
before the debate crew starts. Runs synchronously (blocking) since server.py's
ingest_video endpoint is already blocking-style.
"""

from __future__ import annotations

from typing import Any

from screenshot_suite.comparison_builder import build_comparison_card
from screenshot_suite.evidence_curator import curate_evidence


# ---------------------------------------------------------------------------
# Agent brief generator (programmatic — no extra LLM call)
# ---------------------------------------------------------------------------


def _generate_agent_brief(
    cards: list[dict[str, Any]],
    user_context: dict[str, Any],
) -> str:
    """Produce a text brief from comparison cards for injection into agent prompts.

    Programmatically formatted — no LLM call needed since the cards already
    contain all the synthesised insights. Kept under ~4 000 tokens.
    """
    if not cards:
        return ""

    apps = sorted({c["competitor_side"]["app"] for c in cards})

    # Collect risk and opportunity signals across all cards
    risks: list[str] = []
    opportunities: list[str] = []
    for card in cards:
        frame_n = card["user_side"]["frame_number"]
        comp_app = card["competitor_side"]["app"]
        for ev in card.get("market_evidence", []):
            summary = ev.get("review_summary", "")
            if ev.get("verdict") == "negative":
                risks.append(f"Frame {frame_n} vs {comp_app}: {summary}")
            elif ev.get("verdict") == "positive":
                opportunities.append(f"Frame {frame_n} vs {comp_app}: {summary}")

    lines: list[str] = [
        "COMPETITIVE SCREENSHOT ANALYSIS BRIEF",
        "=" * 45,
        (
            f"Your product was compared against {len(cards)} screens from: "
            f"{', '.join(a.capitalize() for a in apps)}.\n"
        ),
    ]

    for i, card in enumerate(cards[:6], 1):
        user_label = card["user_side"]["screen_label"]
        comp_app = card["competitor_side"]["app"].capitalize()
        comp_label = card["competitor_side"]["screen_label"]
        sim = card["competitor_side"]["similarity_score"]
        evidence = card.get("market_evidence", [])
        top_theme = evidence[0]["theme"] if evidence else "UI patterns"

        # First observation for each side (guard against empty lists)
        user_obs_list = card["user_side"].get("key_observations", [])
        comp_obs_list = card["competitor_side"].get("key_observations", [])
        user_obs = user_obs_list[0] if user_obs_list else "See analysis"
        comp_obs = comp_obs_list[0] if comp_obs_list else "See analysis"

        lines.append(f"KEY FINDING {i}: {top_theme.upper()}")
        lines.append(f"- Your screen ({user_label}): {user_obs}")
        lines.append(
            f"- Closest match: {comp_app} ({comp_label}, similarity {sim:.2f}) — {comp_obs}"
        )
        if evidence:
            lines.append(f"- Market says: {evidence[0]['review_summary']}")
        insight = card.get("actionable_insight", "")
        if insight:
            lines.append(f"- Action: {insight}")
        lines.append("")

    if risks:
        lines.append("TOP RISKS (negative competitor reviews matching your patterns):")
        for idx, r in enumerate(risks[:3], 1):
            lines.append(f"{idx}. {r}")
        lines.append("")

    if opportunities:
        lines.append("TOP OPPORTUNITIES (competitor weaknesses you could exploit):")
        for idx, o in enumerate(opportunities[:3], 1):
            lines.append(f"{idx}. {o}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def synthesize_evidence(
    session_id: str,
    video_evidence: dict[str, Any],
    user_context: dict[str, Any],
) -> dict[str, Any]:
    """Run the full curation + card-building pipeline for a completed video ingest.

    Args:
        session_id: Debate session identifier (used only for log messages).
        video_evidence: The ``VIDEO_EVIDENCE[session_id]`` dict.  Must contain
            ``screenshot_matches`` as populated by server.py's ingest_video.
        user_context: Onboarding answers.  Expected keys: ``productDescription``,
            ``target_user``, ``competitors``, ``differentiator``, ``product_stage``.

    Returns:
        Dict with keys:
            ``comparison_cards``  — list of card dicts for frontend rendering
            ``agent_brief``       — text block for debate context injection
            ``total_comparisons`` — int
            ``apps_compared``     — sorted list of app names
            ``dominant_themes``   — top 5 theme names by frequency
    """
    screenshot_matches: list[dict[str, Any]] = video_evidence.get("screenshot_matches", [])
    if not screenshot_matches:
        return {
            "comparison_cards": [],
            "agent_brief": "",
            "total_comparisons": 0,
            "apps_compared": [],
            "dominant_themes": [],
        }

    print(f"\n🔍 Synthesising evidence for {len(screenshot_matches)} frame matches...")

    cards: list[dict[str, Any]] = []
    card_index = 0

    for match in screenshot_matches:
        frame_number: int = match["frame_number"]
        user_analysis: str = match.get("user_analysis", "")
        competitors_list: list[dict[str, Any]] = match.get("matched_competitors", [])

        if not user_analysis or not competitors_list:
            continue

        # Build one card per frame using only the top (most similar) competitor match
        top_match = competitors_list[0]
        print(
            f"   Frame {frame_number}: curating against "
            f"{top_match['app']}/{top_match['filename']} "
            f"(sim={top_match['similarity_score']:.2f})"
        )

        try:
            curated_themes = curate_evidence(user_context, user_analysis, top_match)
        except Exception as exc:
            print(f"   WARNING: Evidence curation failed for frame {frame_number}: {exc}")
            curated_themes = []

        try:
            card = build_comparison_card(
                frame_number=frame_number,
                user_analysis=user_analysis,
                competitor_match=top_match,
                curated_themes=curated_themes,
                user_context=user_context,
                card_index=card_index,
            )
            cards.append(card)
            card_index += 1
        except Exception as exc:
            print(f"   WARNING: Card build failed for frame {frame_number}: {exc}")

    agent_brief = _generate_agent_brief(cards, user_context)
    apps_compared = sorted({c["competitor_side"]["app"] for c in cards})

    # Dominant themes — most frequently occurring theme_name across all market_evidence
    theme_counts: dict[str, int] = {}
    for card in cards:
        for ev in card.get("market_evidence", []):
            t = ev.get("theme", "")
            if t:
                theme_counts[t] = theme_counts.get(t, 0) + 1
    dominant_themes = sorted(theme_counts, key=lambda t: theme_counts[t], reverse=True)[:5]

    print(
        f"   ✓ Built {len(cards)} comparison cards across "
        f"{len(apps_compared)} competitor apps\n"
    )

    return {
        "comparison_cards": cards,
        "agent_brief": agent_brief,
        "total_comparisons": len(cards),
        "apps_compared": apps_compared,
        "dominant_themes": dominant_themes,
    }
