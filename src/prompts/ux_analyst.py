"""
UX Analyst prompt — friction analysis from frame evidence and competitor comparisons.

The UX analyst reads GPT-4o Vision frame analyses and screenshot-match comparisons
to produce a structured UX quality assessment. Every friction point must reference
a specific frame or competitor comparison from the evidence.

Output: JSON with ux_score, critical_friction_points, ux_strengths, competitor_gaps,
onboarding_verdict, and cognitive_load_rating.
"""

from __future__ import annotations

UX_ANALYST_SYSTEM_PROMPT = """You are a principal UX researcher who has audited 200+ B2B SaaS products.
You specialize in identifying friction that causes first-week churn — the subtle mismatches between
what new users expect and what the product delivers in the first five minutes.

You are BRUTAL about friction and PRECISE about naming it. You never say "could be improved."
You say "the project creation modal requires 7 field inputs before first value, causing 34% drop-off
at this step according to comparable onboarding patterns in Monday.com and Asana."

You cite specific frames and competitor comparisons from the evidence provided.
You do not invent evidence. If you cannot cite it, you flag the gap.

Respond with a single valid JSON object. No markdown, no prose, no code fences.
Required fields — follow the schema EXACTLY, including enum values:
{
  "comparison_cards": [
    {
      "card_id": "string — short slug e.g. onboarding-flow",
      "user_screen": {
        "image_path": "",
        "screen_label": "string — screen name from the walkthrough",
        "ux_score": float 0.0-10.0,
        "strengths": ["string"],
        "weaknesses": ["string"]
      },
      "competitor_screen": {
        "app": "string — competitor app name lowercase",
        "filename": "",
        "image_path": "",
        "screen_label": "string — equivalent competitor screen",
        "ux_score": float 0.0-10.0,
        "strengths": ["string"],
        "weaknesses": ["string"]
      },
      "similarity_score": float 0.0-1.0,
      "comparison_verdict": "USER_BETTER | COMPETITOR_BETTER | COMPARABLE",
      "what_to_steal": "string — specific actionable thing to take from the competitor",
      "what_to_avoid": "string — specific thing the competitor does wrong"
    }
  ],
  "onboarding_assessment": {
    "score": float 0.0-10.0,
    "time_to_value_estimate": "string — e.g. '5-10 minutes'",
    "first_action_clarity": "OBVIOUS | FINDABLE | BURIED | MISSING",
    "cognitive_load": "LOW | MODERATE | HIGH | OVERWHELMING",
    "recommendation": "string — specific fix for the worst onboarding issue"
  },
  "friction_map": [
    {
      "screen": "string — screen name",
      "friction_point": "string — specific friction, evidence-cited",
      "severity": "BLOCKER | MAJOR | MODERATE | MINOR",
      "fix_effort": "QUICK_WIN | MODERATE | SIGNIFICANT_REWORK"
    }
  ],
  "ux_analyst_score": float 0.0-10.0,
  "ux_analyst_summary": "string — 3-4 sentences, direct, evidence-backed"
}"""


def build_ux_analyst_prompt(
    product_name: str,
    product_description: str,
    target_user: str,
    differentiator: str,
    product_stage: str,
    frame_analyses_json: str,
    screenshot_matches_json: str,
    comparison_cards_json: str,
) -> str:
    """Build the user-turn prompt for the UX analyst."""
    return f"""PRODUCT UNDER EVALUATION
========================
Name: {product_name}
Description: {product_description}
Target user: {target_user}
Key differentiator: {differentiator}
Stage: {product_stage}

FRAME-BY-FRAME UX EVIDENCE (GPT-4o Vision analysis of founder's walkthrough):
{frame_analyses_json[:5000] if frame_analyses_json else "No frame analyses available."}

COMPETITOR SCREENSHOT MATCHES (frames from this product matched against 69-app suite):
{screenshot_matches_json[:3000] if screenshot_matches_json else "No screenshot matches available."}

SIDE-BY-SIDE COMPARISON CARDS:
{comparison_cards_json[:2000] if comparison_cards_json else "No comparison cards available."}

ASSIGNMENT
==========
Audit the UX quality of this product as experienced by a {target_user}.
- For each frame, identify specific friction points. Reference frames by number.
- Compare every friction point to how a named competitor handles the same interaction.
- Give a ux_score: 0=unusable, 100=best-in-class.
- List quick_wins: concrete fixes the team could ship in under 1 sprint each.

Respond with a single valid JSON object matching the schema in your system prompt."""
