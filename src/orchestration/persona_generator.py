"""
Meta-prompting for adversarial persona generation.

Produces three JSON personas (first-timer, daily driver, buyer) with
intentionally incompatible priorities. Different training-distribution
priors across three personas are what make the debate produce genuine
disagreement rather than correlated consensus.

Static fallback personas are returned when LLM JSON parsing fails.
"""

from __future__ import annotations

import json
from typing import Any

from crewai import LLM

META_PROMPT = """You are an expert product researcher who has spent 15 years studying how people adopt, use, and abandon productivity software. You have analyzed user behavior across every major tool in the space — Notion, Asana, Monday.com, Linear, Todoist, ClickUp, Trello, Slack, Coda, Airtable, and dozens of others. You know exactly why people switch between these tools and what breaks their trust.

A product team wants to run adversarial QA testing on this productivity app:

PRODUCT: {product_description}

You have access to a knowledge base containing:
- 4,000+ real App Store and Play Store reviews for the top 20 productivity apps
- 1,600+ Reddit posts with comments from r/productivity, r/notion, r/projectmanagement and related subreddits
- 1,000+ Hacker News comments discussing productivity tools
- 200-400 G2 reviews from verified business users
- Metadata files with pricing, category, features, and use cases for each competitor
- Pre-processed feature-level sentiment scores for every review
- Screenshots and visual descriptions of competitor UIs and key user flows

Generate exactly 3 consumer personas that will test this product adversarially. These personas must satisfy ALL of the following:

CONFLICT REQUIREMENT: Each persona must have fundamentally incompatible priorities. What persona 1 considers essential, persona 2 must consider bloat. What persona 2 values most, persona 3 must see as a red flag. Their ideal version of this product would be three completely different products.

SPECIFICITY REQUIREMENT: Each persona must include:
- Their exact job, team size, and what they use productivity tools FOR
- The specific competing tools they currently use or have churned from in the last 12 months, and the EXACT reason they left each one
- How long they give a new productivity tool before deciding to stay or leave
- The specific workflow they will try to accomplish during this test
- What competing product they will switch to if this product fails them

ARCHETYPE REQUIREMENT:
- Persona 1: THE FIRST-TIMER — evaluating for the first time, comparing against what they already use
- Persona 2: THE DAILY DRIVER — used it heavily for months, knows where the bodies are buried
- Persona 3: THE BUYER — evaluating for team adoption with budget authority

EVIDENCE PREFERENCE:
- Persona 1 trusts App Store reviews and Reddit first impressions
- Persona 2 trusts long-form G2 reviews and Hacker News technical discussions
- Persona 3 trusts pricing comparisons, feature matrices, and business user reviews

TONE: These personas are not polite. They have been burned by productivity tools before. They are skeptical, specific, and do not give products the benefit of the doubt.

Return ONLY a valid JSON array with exactly 3 objects. No markdown, no explanation, no preamble, no code fences.
Each object must have exactly these keys:
- "role": a descriptive title (example: "Sprint-Obsessed PM Who Churned From Notion")
- "goal": one sentence describing what they are trying to accomplish AND what would make them abandon this product
- "backstory": at least 5 sentences with specific tool names, specific workflows, specific past frustrations, specific comparison points, and what they need to see in the first session to keep going"""


def generate_personas(product_description: str, llm: LLM) -> list[dict[str, Any]]:
    """Generate three adversarial debate personas via the meta-prompt.

    Args:
        product_description: Free-text product name and context for the run.
        llm: CrewAI LLM instance used to sample persona JSON.

    Returns:
        A list of three persona dicts with ``role``, ``goal``, and ``backstory``
        keys, or static fallbacks if JSON parsing fails.
    """
    prompt = META_PROMPT.format(product_description=product_description)
    response = llm.call(messages=[{"role": "user", "content": prompt}])

    try:
        text = (
            response if isinstance(response, str)
            else response.content if hasattr(response, "content")
            else str(response)
        )
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        personas = json.loads(text)
        if isinstance(personas, list) and len(personas) == 3:
            return personas
    except (json.JSONDecodeError, Exception) as exc:
        print(f"Warning: Failed to parse personas JSON: {exc}")

    return [
        {
            "role": "First-Time User Comparing Against Current Tools",
            "goal": "Find the 3 biggest problems a new user hits in their first session, backed by real user evidence",
            "backstory": (
                "You evaluate new productivity tools with extreme skepticism. "
                "You have churned from Notion after database views broke at scale, "
                "left Asana because the mobile app was unusable, and abandoned "
                "Monday.com because the pricing tripled when you added your team. "
                "You give any new tool exactly one focused session before deciding. "
                "You trust App Store reviews and Reddit first impressions over marketing pages."
            ),
        },
        {
            "role": "Daily Power User Who Knows Every Breaking Point",
            "goal": "Challenge surface-level analysis and expose the deep problems that only emerge after months of real usage",
            "backstory": (
                "You have used this product daily for over a year. You know every "
                "keyboard shortcut, every workaround, and every bug that the dev team "
                "pretends doesn't exist. You have seen features launch broken and stay "
                "broken for months. You trust G2 verified reviews and Hacker News "
                "technical discussions because they come from people who actually push "
                "tools to their limits. You are tired of first-time reviewers who test "
                "a product for 10 minutes and think they understand it."
            ),
        },
        {
            "role": "The CTO Who Has Bought and Killed 4 Project Management Tools",
            "goal": "Make a final buy/no-buy decision for team-wide adoption based on pricing, integrations, data portability, and admin controls",
            "backstory": (
                "You have budget authority for a 30-person engineering org. You have "
                "adopted and abandoned Jira, Basecamp, ClickUp, and Linear in the last "
                "3 years. Each migration cost your team 2 weeks of lost productivity. "
                "You care about pricing at scale, SSO, audit trails, API access, and "
                "data export. You trust pricing comparisons, feature matrices, and "
                "business user reviews. If a tool doesn't have real admin controls, "
                "it's a toy, not a business tool."
            ),
        },
    ]
