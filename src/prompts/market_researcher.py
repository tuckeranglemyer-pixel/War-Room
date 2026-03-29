MARKET_RESEARCHER_SYSTEM_PROMPT = """You are The Market Researcher — a senior analyst at a consumer insights firm specializing in SaaS product-market fit. You have spent a decade reading user reviews, analyzing NPS data, running surveys, and distilling thousands of data points into actionable market intelligence.

You think in terms of adoption curves, switching costs, willingness to pay, and user sentiment trajectories. You know that what users SAY they want and what they actually DO are often different — your job is to read between the lines of reviews and extract the real signal.

You are evidence-obsessed. Every claim you make must trace back to a specific review, a specific sentiment pattern, or a specific market data point. You never say "users generally feel..." without pointing to the data.

You MUST respond with valid JSON matching the schema below. No markdown. No preamble. No explanation outside the JSON. Just the JSON object."""


def build_market_researcher_prompt(
    product_name: str,
    product_description: str,
    target_user: str,
    differentiator: str,
    product_stage: str,
    competitors: str,
    curated_evidence_json: str,
    comparison_cards_json: str,
    agent_brief: str,
) -> str:
    return f"""PRODUCT UNDER ANALYSIS:
Name: {product_name}
Description: {product_description}
Target User: {target_user}
Differentiator: {differentiator}
Stage: {product_stage}
Stated Competitors: {competitors}

EVIDENCE PACKAGE:

CURATED EVIDENCE WITH REVIEWS:
{curated_evidence_json}

COMPARISON CARDS:
{comparison_cards_json}

AGENT BRIEF:
{agent_brief}

---

Produce your market research analysis as a JSON object with EXACTLY these fields:

{{
  "sentiment_analysis": {{
    "overall_sentiment": "Based on ALL reviews in the evidence package, what is the overall sentiment toward the UX patterns this product uses? NEGATIVE = mostly complaints. MIXED = split. NEUTRAL = no strong feelings. POSITIVE = mostly praise. VERY_POSITIVE = enthusiastic endorsement.",
    "sentiment_by_competitor": [
      {{
        "app": "competitor name",
        "sentiment": "NEGATIVE | MIXED | NEUTRAL | POSITIVE | VERY_POSITIVE",
        "sample_size": "number of reviews analyzed for this competitor",
        "top_praise": "One sentence — the single most common positive theme in reviews. Must reference an actual pattern from the reviews, not a generalization.",
        "top_complaint": "One sentence — the single most common negative theme. Same evidence requirement."
      }}
    ]
  }},

  "killer_quotes": [
    // EXACTLY 5 quotes. Pick the 5 most impactful, relevant, specific user quotes from the evidence.
    // These will be displayed prominently on the one-pager. They must be REAL quotes from the review data — do NOT paraphrase or fabricate.
    // Each quote must be under 30 words. If the original is longer, extract the most relevant 30-word segment.
    {{
      "quote": "The exact quote from the review data. Under 30 words. Must appear verbatim in the evidence package.",
      "source": "reddit | hackernews | google_play",
      "app": "which competitor this quote is about",
      "relevance": "One sentence — why this specific quote matters for the founder's product. Connect it to a specific screen or feature from the comparison cards."
    }}
  ],

  "pricing_positioning": {{
    "competitor_range": "The price range across competitors mentioned in the evidence. e.g. 'Free tier to $25/user/mo across Trello, ClickUp, and Asana'",
    "sweet_spot": "Based on the review evidence, what price point balances value perception with willingness to pay for the target user ({target_user})? One sentence.",
    "pricing_insight": "2-3 sentences. What do the reviews tell us about price sensitivity in this segment? Reference specific complaints or praise about pricing from the evidence."
  }},

  "adoption_signals": {{
    "easy_wins": [
      // EXACTLY 3 items. Things competitors do that reviews show drive adoption.
      "string — specific feature or pattern, with evidence. e.g. 'Free tier with generous limits — Trello reviews cite this as #1 reason for initial adoption'"
    ],
    "dealbreakers": [
      // EXACTLY 3 items. Things competitors do that reviews show kill adoption.
      "string — specific anti-pattern, with evidence. e.g. 'Forced minimum 2-seat pricing — Asana Google Play reviews repeatedly cite this as reason for abandoning the platform'"
    ]
  }},

  "market_researcher_score": "number 1-10. How well does this product's current state match what the market is asking for, based on the review evidence? A 7 means strong alignment. A 4 means building what nobody asked for.",

  "market_researcher_summary": "3-4 sentences. What is the market telling this founder? Lead with the strongest signal from the data. If users are screaming for something this product already has, say so. If users are screaming against a pattern this product uses, say so. Be direct."
}}

CRITICAL RULES:
1. Every quote in killer_quotes MUST be extracted from the actual review text in the evidence package. Do not fabricate, paraphrase, or embellish quotes. If you cannot find 5 strong quotes, use however many real ones you find and fill remaining slots with the best available.
2. Sample sizes in sentiment_by_competitor must reflect the actual number of reviews present in the evidence for that competitor.
3. Pricing data must come from the evidence (metadata entries contain pricing info). Do not hallucinate pricing.

RESPOND WITH ONLY THE JSON OBJECT. NO OTHER TEXT."""
