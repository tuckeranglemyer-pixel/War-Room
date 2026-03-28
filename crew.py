from crewai import Agent, Task, Crew, Process, LLM
from tools import (
    search_app_reviews,
    search_reddit,
    search_g2_reviews,
    search_hn_comments,
    search_competitor_data,
    search_screenshots,
    search_pm_knowledge,
)
from meta_prompt import generate_personas

# --- LLM Configuration ---
# Local development: all agents use mistral:7b via Ollama
# DGX production: swap these to different models on different ports
#   first_timer_llm = LLM(model="ollama/llama3.3:70b", base_url="http://localhost:11434")
#   daily_driver_llm = LLM(model="ollama/qwen3:32b", base_url="http://localhost:11434")
#   buyer_llm = LLM(model="ollama/mistral-small:24b", base_url="http://localhost:11434")

local_llm = LLM(model="ollama/mistral:7b", base_url="http://localhost:11434")
first_timer_llm = local_llm
daily_driver_llm = local_llm
buyer_llm = local_llm

ALL_TOOLS = [
    search_pm_knowledge,
    search_app_reviews,
    search_reddit,
    search_g2_reviews,
    search_hn_comments,
    search_competitor_data,
    search_screenshots,
]


def build_crew(product_description: str) -> Crew:
    """Build the War Room crew with dynamically generated personas."""

    # --- Step 1: Generate personas via meta-prompt ---
    personas = generate_personas(product_description, local_llm)

    # --- Step 2: Create Agents ---
    first_timer = Agent(
        role=personas[0]["role"],
        goal=personas[0]["goal"],
        backstory=personas[0]["backstory"]
        + "\n\nEVIDENCE PREFERENCE: You trust App Store reviews and Reddit first impressions — the voice of normal users. When searching the knowledge base, prioritize these sources.",
        llm=first_timer_llm,
        tools=ALL_TOOLS,
        max_iter=10,
        verbose=True,
    )

    daily_driver = Agent(
        role=personas[1]["role"],
        goal=personas[1]["goal"],
        backstory=personas[1]["backstory"]
        + "\n\nEVIDENCE PREFERENCE: You trust long-form G2 reviews and Hacker News technical discussions — the voice of power users. When searching the knowledge base, prioritize these sources.",
        llm=daily_driver_llm,
        tools=ALL_TOOLS,
        max_iter=10,
        verbose=True,
    )

    buyer = Agent(
        role=personas[2]["role"],
        goal=personas[2]["goal"],
        backstory=personas[2]["backstory"]
        + "\n\nEVIDENCE PREFERENCE: You trust pricing comparisons, feature matrices, and business user reviews — the voice of decision-makers. When searching the knowledge base, prioritize these sources.",
        llm=buyer_llm,
        tools=ALL_TOOLS,
        max_iter=10,
        verbose=True,
    )

    # --- Step 3: Create Tasks (4 rounds, sequential with context chaining) ---

    # ROUND 1 — First-Timer analyzes
    round1 = Task(
        description=f"""You are testing this productivity app: {product_description}

You are a first-time user. You have never opened this product before. You will give this product exactly one honest session before deciding whether to continue or go back to what you know.

YOUR KNOWLEDGE BASE: You have access to real user data including App Store reviews, Play Store reviews, Reddit discussions, and first-impression reports. Each review has pre-processed feature-level sentiment scores. When searching reviews, pay attention to sentiment patterns — a feature with 200 reviews but 85% negative sentiment is a bigger problem than a feature with 20 reviews and 50% negative sentiment. Search this data. Do not speculate when real evidence exists.

YOUR ASSIGNMENT:

1. ONBOARDING AUDIT: Describe your first 2 minutes with this product step by step. Where did you get confused? Where did the product fail to explain itself? Search the knowledge base for App Store and Reddit reviews that describe the same onboarding friction.

2. FIND 3 CRITICAL PROBLEMS: For EACH problem provide:
   - THE MOMENT: The exact interaction where this fails
   - THE EVIDENCE: Quote or cite at least one real user review or Reddit post from the knowledge base
   - SEVERITY: Rate 1-10 where 10 means "I am closing this tab and never coming back"
   - THE ALTERNATIVE: Name the specific competitor that handles this better and how

3. ONE GENUINE STRENGTH: What does this product do better than the competition? Cite evidence. Then explain whether this strength is enough to overcome the problems.

Do not write a balanced review. You are a real user with limited patience.""",
        expected_output="Onboarding audit describing first 2 minutes step by step. Then 3 critical problems, each with: the exact failing interaction, a cited real user review or Reddit post, a severity rating 1-10, and a named competitor that handles it better. Then 1 acknowledged strength with evidence. Format as clearly labeled numbered sections.",
        agent=first_timer,
    )

    # ROUND 2 — Daily Driver challenges
    round2 = Task(
        description=f"""You are a daily power user of this productivity app: {product_description}

You have used this product for months. You know its shortcuts, hidden features, and breaking points. You have just read an analysis from a first-time user.

YOUR KNOWLEDGE BASE: You have access to long-form G2 reviews from verified business users, Hacker News technical discussions, and deep-dive Reddit threads. Each review has pre-processed feature-level sentiment scores — use these to distinguish widespread problems (high volume, high negativity) from edge cases (low volume, mixed sentiment). Search this data for evidence that supports or contradicts the first-timer's claims.

YOUR ASSIGNMENT:

1. CHALLENGE EACH FINDING: For each of the first-timer's 3 problems, take a clear position:
   - AGREE and explain why this problem is actually WORSE than they described, OR
   - DISAGREE and explain why this problem goes away after the first week, citing long-term user reviews
   You MUST disagree with at least ONE finding. You MUST agree and escalate at least ONE finding. No fence-sitting.

2. EXPOSE 2 HIDDEN PROBLEMS: Issues a first-time user would NEVER discover but that make daily users miserable — data corruption at scale, features that break in production, performance degradation, missing features competitors added, half-broken integrations. Search the knowledge base for G2 and HN evidence.

3. CHALLENGE THEIR COMPETITOR PICK: The first-timer recommended a competitor. You have used that competitor too. Are they right or naive? Cite evidence.

4. RATE THEIR ANALYSIS: 1-10, how thorough was the first-timer's review? What did they miss?""",
        expected_output="Point-by-point response to Round 1. For each of their 3 problems: clearly labeled AGREE or DISAGREE with cited evidence from G2 or HN. Then 2 hidden long-term problems with evidence. Then a challenge to their competitor recommendation with evidence. Then a 1-10 rating of their analysis quality. Format with clear AGREE/DISAGREE labels.",
        agent=daily_driver,
        context=[round1],
    )

    # ROUND 3 — First-Timer fires back
    round3 = Task(
        description=f"""You are the same first-time user from Round 1. You have just read a challenge from a power user who disagrees with parts of your analysis.

YOUR ASSIGNMENT:

1. DEFEND OR CONCEDE: For each point where the Daily Driver disagreed:
   - If you still believe you are right: explain why the power user's perspective is biased by familiarity. Just because THEY learned to work around a problem does not mean new users should have to. Cite App Store reviews showing normal users consistently hit this issue.
   - If the Daily Driver convinced you: concede clearly and explain what you missed. Then explain why the product team should STILL fix this even if power users have adapted — the first-timer experience drives growth.

2. RESPOND TO THEIR HIDDEN PROBLEMS: The Daily Driver found 2 problems you missed. Do these change your overall assessment?

3. UPDATED VERDICT: Update your severity ratings. What changed? Revised stay-or-leave recommendation.

STUBBORNNESS RULE: Do not concede a point unless the Daily Driver provided specific, cited evidence that directly contradicts your finding. The fact that a power user learned to work around a problem is NOT a valid rebuttal — products should not require users to suffer through bad design before it gets good. "You get used to it" is an admission of failure, not a defense. If they dismissed your concern without counter-evidence, say so directly.""",
        expected_output="Point-by-point defense or concession for each disagreement, with a confidence score 1-10 for each position. Response to the 2 hidden problems. Updated severity ratings with explanation. Revised stay-or-leave recommendation. Format as direct responses to each challenge.",
        agent=first_timer,
        context=[round1, round2],
    )

    # ROUND 4 — Buyer delivers final verdict
    round4 = Task(
        description=f"""You are evaluating this productivity app for team-wide adoption: {product_description}

You have read the FULL debate. Now make the business decision.

YOUR KNOWLEDGE BASE: You have access to pricing data, feature comparison matrices, business user reviews from G2, integration documentation, and team-focused reviews. You care about TEAM scale, not individual scale.

YOUR ASSIGNMENT:

1. SETTLE EACH DISAGREEMENT: For every point where they disagreed:
   - State who is right based on evidence
   - What this disagreement reveals about the product's maturity
   - Whether it causes problems at team scale (10+ users with different experience levels)

2. BUSINESS-CRITICAL ASSESSMENT:
   - PRICING: Fair at team scale? Cost as you add users? Critical features locked behind enterprise tiers?
   - INTEGRATIONS: Actually works with tools teams use? Search for integration complaints.
   - DATA: Can you export if you leave? Vendor lock-in?
   - ADMIN: Team management, permissions, audit trails? Or individual tool pretending to be a team tool?

3. THE BLIND SPOT: ONE strategic problem both analysts missed — about the MARKET, not the product. A competitor about to make this irrelevant, or a trend making this category obsolete.

4. FINAL VERDICT:
   A. BUY DECISION: YES, NO, or YES WITH CONDITIONS. Not "it depends."
   B. OVERALL SCORE: 1-100, defensible with evidence.
   C. TOP 3 FIXES: Ranked by priority. For each: describe in PM sprint language, cite evidence, estimate retention impact (5%? 20%? 50%?).
   D. COMPETITIVE POSITIONING: One paragraph — where this sits vs top 3 competitors, defensible advantage, fatal gap.

You are spending real budget. Make the decision. Own it.""",
        expected_output="Resolution of each disagreement with evidence. Business-critical assessment of pricing, integrations, data portability, admin. One strategic blind spot. Final verdict: YES/NO/YES WITH CONDITIONS, 1-100 score, top 3 prioritized fixes as actionable tickets with evidence and retention impact, competitive positioning summary. No hedging.",
        agent=buyer,
        context=[round1, round2, round3],
    )

    # --- Step 4: Assemble Crew ---
    crew = Crew(
        agents=[first_timer, daily_driver, buyer],
        tasks=[round1, round2, round3, round4],
        process=Process.sequential,
        verbose=True,
    )

    return crew


if __name__ == "__main__":
    product = input("Enter product to analyze (name + description): ")
    print("\n🔥 THE WAR ROOM — Generating adversarial personas...\n")
    crew = build_crew(product)
    print("\n⚔️ Starting 4-round adversarial debate...\n")
    result = crew.kickoff()
    print("\n" + "=" * 60)
    print("📋 FINAL WAR ROOM REPORT")
    print("=" * 60)
    print(result)
