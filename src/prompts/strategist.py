"""
Strategist prompt — market positioning and product-market fit analysis.

The strategist synthesizes competitive intelligence, curated user evidence, and
the agent brief into a structured assessment of whether the product has a
defensible position and what the top-line risks are to adoption.

Output: JSON with market_position, key_risks, key_strengths, competitive_gaps,
market_readiness_score (0-100), top_3_priorities, and pmf_verdict.
"""

from __future__ import annotations

STRATEGIST_SYSTEM_PROMPT = """You are a senior product strategist at a top-tier VC firm.
You have reviewed hundreds of early-stage B2B SaaS products and have a near-perfect track record
of identifying which ones will reach product-market fit within 18 months.

Your job is to assess market positioning and competitive defensibility.
You are HARSH on undifferentiated products and GENEROUS toward products with genuine insight.
You do not sugarcoat. If the product is a vitamin masquerading as a painkiller, you say so.

Respond with a single valid JSON object. No markdown, no prose, no code fences.
Required fields — follow the schema EXACTLY, including enum values:
{
  "competitive_positioning": "string — 2-3 sentences on where this product sits vs competitors and why",
  "top_risks": [
    {
      "risk": "string — specific risk statement",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "evidence": "string — cite specific evidence from the data",
      "competitor_learned_from": "string — which competitor already solved or suffered from this"
    }
  ],
  "top_opportunities": [
    {
      "opportunity": "string — specific opportunity statement",
      "impact": "TRANSFORMATIVE | HIGH | MEDIUM | LOW",
      "evidence": "string — cite specific evidence from the data",
      "competitor_failed_at": "string — which competitor failed to capture this opportunity"
    }
  ],
  "moat_assessment": "string — 2-3 sentences on the defensibility of the position",
  "strategist_score": float 0.0-10.0 (e.g. 7.5),
  "strategist_summary": "string — 3-4 sentences, the strategic take, direct and non-hedged"
}"""


def build_strategist_prompt(
    product_name: str,
    product_description: str,
    target_user: str,
    differentiator: str,
    product_stage: str,
    competitors: str,
    comparison_cards_json: str,
    agent_brief: str,
    curated_evidence_json: str,
    n_screenshots: int = 69,
    n_apps: int = 10,
    n_reviews: int = 60,
) -> str:
    """Build the user-turn prompt for the strategist analysis."""
    return f"""PRODUCT UNDER EVALUATION
========================
Name: {product_name}
Description: {product_description}
Target user: {target_user}
Key differentiator: {differentiator}
Stage: {product_stage}
Competing against: {competitors}

COMPETITIVE INTELLIGENCE
========================
Evidence corpus: {n_screenshots} competitor screenshots across {n_apps} apps, {n_reviews} curated user reviews.

AGENT BRIEF (synthesized from video walkthrough and competitor matching):
{agent_brief[:3000] if agent_brief else "No agent brief available."}

CURATED USER EVIDENCE (reviews and sentiment from real users of competing products):
{curated_evidence_json[:4000] if curated_evidence_json else "No curated evidence available."}

COMPARISON CARDS (side-by-side UX comparisons vs top competitor screens):
{comparison_cards_json[:2000] if comparison_cards_json else "No comparison cards available."}

ASSIGNMENT
==========
Assess this product's market positioning and competitive defensibility.
- Does the differentiator hold up against the competitive evidence?
- What does the curated user evidence reveal about unmet needs this product could own?
- Where are the competitive gaps this product could exploit vs. where it is already late?
- Give a market_readiness_score: 0=completely unready, 100=ready to scale.

Respond with a single valid JSON object matching the schema in your system prompt."""
