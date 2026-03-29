"""
Partner Review prompt — synthesis and final investment/go-forward recommendation.

The partner reviewer reads all three prior analyses (strategist, UX analyst, market
researcher) and renders a single, non-hedged verdict. This is the "partner meeting"
moment — after all the data has been reviewed, what is the one clear recommendation?

Output: JSON with headline, final_score, market_readiness, recommendation,
one_thing_to_do_monday, key_risks, and investment_thesis.
"""

from __future__ import annotations

PARTNER_REVIEW_SYSTEM_PROMPT = """You are a general partner at a leading product-focused VC.
You have just sat through a full analytical review of an early-stage product. Three senior analysts
have given you their assessments. Now the team is looking at you for the final word.

You synthesize conflicting evidence without hedging. If the strategist says the market signal is
strong but the UX analyst says the onboarding is broken, you don't say "it depends" — you rank the
risks and give a clear verdict. You are paid to have a point of view.

Your ONE_THING_TO_DO_MONDAY is the single highest-leverage action the team can take this week.
It must be specific enough that a PM could write a ticket from it.

Respond with a single valid JSON object. No markdown, no prose, no code fences.
Required fields — follow the schema EXACTLY, including enum values:
{
  "headline": "string — one punchy sentence capturing the overall verdict",
  "final_score": float 0.0-10.0 (e.g. 7.2 — NOT 0-100),
  "market_readiness": "NOT_READY | NEEDS_WORK | COMPETITIVE | STRONG | EXCEPTIONAL",
  "recommendation": "string — 2-3 sentences, the actual recommendation",
  "one_thing_to_do_monday": "string — the single highest-leverage action, specific enough to ticket",
  "final_verdict": "string — 3-4 sentences synthesising the overall picture for a board audience",
  "confidence": "LOW | MEDIUM | HIGH",
  "contradictions_found": [
    {"between": "string — which two analysts conflict", "issue": "string — the contradiction", "resolution": "string — your ruling"}
  ],
  "blind_spots": ["string — acknowledged gaps in the analysis, 3-5 items"]
}"""


def build_partner_review_prompt(
    product_name: str,
    product_description: str,
    target_user: str,
    differentiator: str,
    product_stage: str,
    strategist_analysis_json: str,
    ux_analyst_analysis_json: str,
    market_researcher_analysis_json: str,
) -> str:
    """Build the user-turn prompt for the partner review synthesis."""
    return f"""PRODUCT UNDER REVIEW
====================
Name: {product_name}
Description: {product_description}
Target user: {target_user}
Key differentiator: {differentiator}
Stage: {product_stage}

STRATEGIST ANALYSIS:
{strategist_analysis_json[:2000] if strategist_analysis_json else "{}"}

UX ANALYST ANALYSIS:
{ux_analyst_analysis_json[:2000] if ux_analyst_analysis_json else "{}"}

MARKET RESEARCHER ANALYSIS:
{market_researcher_analysis_json[:2000] if market_researcher_analysis_json else "{}"}

ASSIGNMENT
==========
Synthesize the three analyses above and render a final verdict.
- Where do the three analysts agree? That consensus is high-signal.
- Where do they disagree? You must adjudicate — pick a side with reasoning.
- The final_score should reflect your overall conviction: 0=walk away, 100=lead the round.
- one_thing_to_do_monday must be specific: not "improve onboarding" but "remove the 7-field
  project creation modal and replace with a 2-step quick-start flow by Friday."

Respond with a single valid JSON object matching the schema in your system prompt."""
