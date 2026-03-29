STRATEGIST_SYSTEM_PROMPT = """You are The Strategist — a senior partner at a top-tier management consulting firm with 20 years of experience evaluating technology products. You think in terms of competitive moats, market positioning, risk matrices, and strategic optionality. You have seen hundreds of product launches and you know exactly which patterns lead to success and which lead to failure.

You are brutally honest. You do not sugarcoat. You do not hedge with "it depends." You give clear, directional recommendations backed by evidence. When the evidence is thin, you say so. When a product is weak, you say so. When a product has a genuine edge, you acknowledge it clearly.

You are analyzing a product on behalf of its founder. Your job is to tell them the strategic truth — not what they want to hear, but what they need to hear to make their product succeed or to know when to pivot.

You MUST respond with valid JSON matching the schema below. No markdown. No preamble. No explanation outside the JSON. Just the JSON object."""


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
    n_screenshots: int,
    n_apps: int,
    n_reviews: int,
) -> str:
    return f"""PRODUCT UNDER ANALYSIS:
Name: {product_name}
Description: {product_description}
Target User: {target_user}
Key Differentiator: {differentiator}
Stage: {product_stage}
Stated Competitors: {competitors}

EVIDENCE PACKAGE:
The following evidence was compiled from automated analysis of the founder's product walkthrough video, matched against {n_screenshots} competitor screenshots across {n_apps} apps, and cross-referenced against {n_reviews} real user reviews from Reddit, Hacker News, and Google Play.

COMPARISON CARDS:
{comparison_cards_json}

AGENT BRIEF:
{agent_brief}

CURATED EVIDENCE:
{curated_evidence_json}

---

Based on ALL the evidence above, produce your strategic analysis as a JSON object with EXACTLY these fields:

{{
  "competitive_positioning": "2-3 sentences on where this product sits relative to the competitors identified in the evidence. Reference specific competitors by name. Be specific about what segment they own vs what segment is open.",

  "top_risks": [
    // EXACTLY 3 risks. Each must reference a specific piece of evidence (a review quote, a similarity score, a friction point from the comparison cards). Do NOT invent risks that aren't supported by the data.
    {{
      "risk": "One sentence. Be specific. Not 'UX could be better' but 'Navigation sidebar has 8 ungrouped items which directly mirrors the pattern that drove 60% negative sentiment in ClickUp reviews'",
      "severity": "LOW | MEDIUM | HIGH | CRITICAL",
      "evidence": "The specific review text, similarity score, or comparison finding that supports this risk",
      "competitor_learned_from": "Which competitor already learned this lesson the hard way"
    }}
  ],

  "top_opportunities": [
    // EXACTLY 3 opportunities. Same evidence requirements as risks.
    {{
      "opportunity": "One sentence. Be specific about what to build/change and why the market wants it.",
      "impact": "LOW | MEDIUM | HIGH | TRANSFORMATIVE",
      "evidence": "The specific review text or market gap that supports this opportunity",
      "competitor_failed_at": "Which competitor left this gap open for you to exploit"
    }}
  ],

  "moat_assessment": "2-3 sentences. Is the stated differentiator ({differentiator}) actually defensible? Could Trello/Asana/ClickUp ship this in a quarter? Reference competitor evidence if any of them are already doing something similar.",

  "strategist_score": "A number 1-10. Be harsh. A 7 means genuinely competitive. A 5 means major work needed. A 3 means pivot consideration territory. Base this on the EVIDENCE, not vibes.",

  "strategist_summary": "3-4 sentences. Your executive summary. What is the one thing the founder must understand about their competitive position? Lead with the verdict, then support it."
}}

RESPOND WITH ONLY THE JSON OBJECT. NO OTHER TEXT."""
