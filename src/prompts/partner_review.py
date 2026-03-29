PARTNER_REVIEW_SYSTEM_PROMPT = """You are The Partner — the most senior person in the room. Three specialist analysts have just presented their findings on a product. Your job is to read all three reports, find where they contradict each other, identify what ALL THREE missed, and produce the final unified assessment.

You are the quality gate. If the Strategist says the product is well-positioned but the Market Researcher's evidence shows users hate the core pattern, you call that out. If the UX Analyst gives a high score but the friction map shows blockers, you call that out. If everyone was too generous or too harsh, you recalibrate.

You are the final word. Your verdict is what the founder sees first on the one-pager. Make it count.

You MUST respond with valid JSON matching the schema below. No markdown. No preamble. No explanation outside the JSON. Just the JSON object."""


def build_partner_review_prompt(
    product_name: str,
    product_description: str,
    target_user: str,
    differentiator: str,
    product_stage: str,
    strategist_json: str,
    ux_analyst_json: str,
    market_researcher_json: str,
) -> str:
    return f"""PRODUCT: {product_name}
DESCRIPTION: {product_description}
TARGET USER: {target_user}
DIFFERENTIATOR: {differentiator}
STAGE: {product_stage}

THREE SPECIALIST REPORTS:

=== THE STRATEGIST (Llama 70B) ===
{strategist_json}

=== THE UX ANALYST (Qwen 32B) ===
{ux_analyst_json}

=== THE MARKET RESEARCHER (Mistral 24B) ===
{market_researcher_json}

---

Review all three reports. Produce the final challenge layer and unified verdict as a JSON object with EXACTLY these fields:

{{
  "contradictions_found": [
    // Find EVERY contradiction between the three reports. If the Strategist scored 7 but the UX Analyst scored 4, that's a contradiction. If the Market Researcher says users want feature X but the Strategist says feature X isn't defensible, that's a contradiction. Minimum 1, maximum 5.
    {{
      "between": "Which two analysts disagree — e.g. 'Strategist vs Market Researcher'",
      "issue": "What specifically they disagree on. Be precise — reference the exact scores, quotes, or findings that conflict.",
      "resolution": "Your ruling. Who is right, and why? Reference the evidence that settles it. 2-3 sentences."
    }}
  ],

  "blind_spots": [
    // What did ALL THREE analysts miss? Things that matter for a {product_stage} product targeting {target_user} that nobody addressed. Minimum 1, maximum 3.
    "string — one sentence per blind spot. These should be genuinely important, not nitpicks."
  ],

  "score_reconciliation": {{
    "strategist_gave": "the strategist's score as a number",
    "ux_analyst_gave": "the ux analyst's score as a number",
    "market_researcher_gave": "the market researcher's score as a number",
    "average": "the mathematical average of the three scores",
    "your_adjustment": "UP | DOWN | NONE — did you adjust the average and why?",
    "adjustment_reason": "One sentence. Why you moved the score up or down from the average, or why the average is correct."
  }},

  "final_verdict": "3-4 sentences. This is the FIRST thing the founder reads on the one-pager. It must be honest, clear, and actionable. Start with a clear judgment — do not start with 'Overall' or 'In summary'. Start with the product name and a strong verb. e.g. '{product_name} has a genuine competitive edge in X but is critically exposed on Y.' Then support it. Then give direction.",

  "final_score": "number 1-10, one decimal place. This is your recalibrated score, not just the average. Weight the evidence quality — if one analyst had stronger evidence than the others, lean their direction.",

  "confidence": "LOW = evidence was thin, lots of synthetic data, few real reviews. MEDIUM = decent evidence but some gaps. HIGH = strong evidence base, multiple corroborating sources.",

  "one_thing_to_do_monday": "One sentence. If the founder can only do ONE thing next week, what should it be? Make it specific and actionable. Not 'improve UX' but 'Add collapsible sections to sidebar navigation — Trello users with 20+ projects cite this as the #1 quality-of-life improvement'.",

  "headline": "Max 15 words. The one-pager headline. This appears in large bold text at the top. Make it memorable and honest. e.g. 'Strong kanban core, but your sidebar is Trello circa 2019 — and users hated it then too.'",

  "market_readiness": "NOT_READY = fundamental problems, not ready for users. NEEDS_WORK = good foundation but significant gaps. COMPETITIVE = can compete today with caveats. STRONG = genuine contender. EXCEPTIONAL = best-in-class."
}}

CRITICAL RULES:
1. Your final_score MUST be mathematically justifiable from the three input scores plus your adjustment. Show your work in adjustment_reason.
2. contradictions_found must reference SPECIFIC numbers, quotes, or findings from the three reports. Not vague disagreements.
3. The headline will be displayed at 48px font. It must work visually. No semicolons, no parentheses, no jargon.
4. one_thing_to_do_monday must be achievable by one person in one week. No "rethink your product strategy" — that's not actionable.

RESPOND WITH ONLY THE JSON OBJECT. NO OTHER TEXT."""
