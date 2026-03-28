"""
CrewAI orchestration for The War Room: dynamic personas, reconnaissance swarm,
and a sequential four-round debate with context chaining across three agents.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from crewai import Agent, Crew, LLM, Process, Task

from config import LOCAL_BASE_URL, LOCAL_MODEL, MAX_SCOUTS, MAX_WORKERS
from meta_prompt import generate_personas
from swarm import deploy_swarm
from tools import (
    fetch_context_for_product,
    search_pm_knowledge,
)

# --- LLM configuration (see config.py; swap models on DGX via env or config) ---
# DGX production example (commented in config.py):
#   first_timer_llm = LLM(model=FIRST_TIMER_MODEL, base_url=LOCAL_BASE_URL)
local_llm = LLM(model=LOCAL_MODEL, base_url=LOCAL_BASE_URL)
first_timer_llm = local_llm
daily_driver_llm = local_llm
buyer_llm = local_llm


def build_crew(
    product_description: str,
    task_callback: Optional[Callable[..., None]] = None,
    session_context: Optional[dict[str, Any]] = None,
) -> Crew:
    """Assemble the War Room crew with generated personas, swarm briefing, and four tasks.

    Args:
        product_description: Product name and description to evaluate.
        task_callback: Optional CrewAI callback invoked after each task completes.
        session_context: Optional user evaluation context (team size, tools, budget,
            main problem, use case, upload count). When set, agents prioritize
            user-uploaded evidence.

    Returns:
        A configured sequential ``Crew`` ready to ``kickoff()``.
    """

    # --- Step 0: Build session context block (injected into every task) ---
    context_block = ""
    if session_context:
        product_name = session_context.get("product_name", product_description)
        target_user = session_context.get("target_user") or "Not specified"
        competitors = session_context.get("competitors") or "Not specified"
        differentiator = session_context.get("differentiator") or "Not specified"
        product_stage = session_context.get("product_stage") or "Not specified"

        product_section = f"""PRODUCT BEING EVALUATED:
- Product: {product_name}
- What it does: {product_description}
- Target user: {target_user}
- Competes with: {competitors}
- Key differentiator: {differentiator}
- Stage: {product_stage}

"""
        video_evidence = session_context.get("video_evidence")
        if video_evidence:
            journey_summary = video_evidence.get("journey_summary", "")
            frame_analyses = video_evidence.get("frame_analyses", [])
            frame_snippets = "\n\n".join(
                f"[Frame {i + 1}]\n{text[:600]}"
                for i, text in enumerate(frame_analyses[:10])
            )
            video_section = f"""VIDEO EVIDENCE FROM FOUNDER'S PRODUCT WALKTHROUGH:

JOURNEY SUMMARY:
{journey_summary[:3000]}

KEY FRAME ANALYSES (up to 10 frames):
{frame_snippets}

CRITICAL: The above is PRIMARY evidence from the founder's live walkthrough. Reference specific frames and the journey summary in your analysis. This evidence takes priority over general reviews when they conflict.

"""
            context_block = product_section + video_section
        else:
            context_block = product_section

    agent_tools = [search_pm_knowledge]

    # --- Step 1: Generate personas via meta-prompt ---
    personas = generate_personas(product_description, local_llm)

    # --- Step 1.5: Deploy reconnaissance swarm ---
    swarm_result = deploy_swarm(
        product_description,
        max_scouts=MAX_SCOUTS,
        max_workers=MAX_WORKERS,
    )
    swarm_briefing = swarm_result["briefing"]
    swarm_stats = swarm_result["stats"]

    # --- Step 1b: Pre-fetch real evidence from ChromaDB ---
    # Small local models (7B/8B) don't reliably execute the ReAct tool-calling loop,
    # so we inject real evidence directly into each task description as a guaranteed
    # knowledge base. Agents cite from this evidence rather than hallucinating.
    print("\n📚 Fetching real user evidence from knowledge base...")
    real_evidence = fetch_context_for_product(product_description)
    evidence_count = real_evidence.count("[") - real_evidence.count("[Query error")
    print(f"   → Loaded {evidence_count} real evidence chunks for debate context\n")

    # --- Step 2: Create Agents ---
    first_timer = Agent(
        role=personas[0]["role"],
        goal=personas[0]["goal"],
        backstory=personas[0]["backstory"]
        + "\n\nEVIDENCE PREFERENCE: You trust App Store reviews and Reddit first impressions — the voice of normal users. When searching the knowledge base, prioritize these sources."
        + "\n\nCRITICAL TOOL RULE: You MUST use the search_pm_knowledge tool to gather real user evidence BEFORE making any argument. Never argue from general knowledge alone — always search first. Every claim you make must be backed by evidence from the knowledge base. If you cannot find evidence for a claim, say so explicitly.",
        llm=first_timer_llm,
        tools=agent_tools,
        max_iter=10,
        verbose=True,
    )

    daily_driver = Agent(
        role=personas[1]["role"],
        goal=personas[1]["goal"],
        backstory=personas[1]["backstory"]
        + "\n\nEVIDENCE PREFERENCE: You trust long-form G2 reviews and Hacker News technical discussions — the voice of power users. When searching the knowledge base, prioritize these sources."
        + "\n\nCRITICAL TOOL RULE: You MUST use the search_pm_knowledge tool to gather real user evidence BEFORE making any argument. Never argue from general knowledge alone — always search first. Every claim you make must be backed by evidence from the knowledge base. If you cannot find evidence for a claim, say so explicitly.",
        llm=daily_driver_llm,
        tools=agent_tools,
        max_iter=10,
        verbose=True,
    )

    buyer = Agent(
        role=personas[2]["role"],
        goal=personas[2]["goal"],
        backstory=personas[2]["backstory"]
        + "\n\nEVIDENCE PREFERENCE: You trust pricing comparisons, feature matrices, and business user reviews — the voice of decision-makers. When searching the knowledge base, prioritize these sources."
        + "\n\nCRITICAL TOOL RULE: You MUST use the search_pm_knowledge tool to gather real user evidence BEFORE making any argument. Never argue from general knowledge alone — always search first. Every claim you make must be backed by evidence from the knowledge base. If you cannot find evidence for a claim, say so explicitly.",
        llm=buyer_llm,
        tools=agent_tools,
        max_iter=10,
        verbose=True,
    )

    # --- Step 3: Create Tasks (4 rounds, sequential with context chaining) ---

    # ROUND 1 — First-Timer analyzes
    round1 = Task(
        description=f"""{context_block}IMPORTANT: Use the search_pm_knowledge tool for EVERY point you make. Search before you argue. Cite real user reviews, not general knowledge.

You are testing this productivity app: {product_description}

INTELLIGENCE BRIEFING: Before this debate began, {swarm_stats['scouts_deployed']} reconnaissance agents swept the knowledge base in {swarm_stats['total_time']} seconds and gathered evidence across 20 product dimensions. Here is the compiled intelligence:

{swarm_briefing[:3000]}

Use this briefing as your starting evidence, then search for additional details with the search_pm_knowledge tool to deepen your analysis.

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
        description=f"""{context_block}You are a daily power user of this productivity app: {product_description}

You have used this product for months. You know its shortcuts, hidden features, and breaking points. You have just read an analysis from a first-time user.

YOUR ASSIGNMENT:

1. CHALLENGE EACH FINDING: For each of the first-timer's 3 problems, take a clear position:
   - AGREE and explain why this problem is actually WORSE than they described, OR
   - DISAGREE and explain why this problem goes away after the first week, citing evidence from below
   You MUST disagree with at least ONE finding. You MUST agree and escalate at least ONE finding. No fence-sitting.

2. EXPOSE 2 HIDDEN PROBLEMS: Issues a first-time user would NEVER discover but that make daily users miserable. Cite evidence from the knowledge base below.

3. CHALLENGE THEIR COMPETITOR PICK: Are they right or naive? Cite evidence from below.

4. RATE THEIR ANALYSIS: 1-10, how thorough was the first-timer's review? What did they miss?

ONLY cite evidence from the knowledge base provided below — do not invent usernames or URLs.
{real_evidence}""",
        expected_output="Point-by-point response to Round 1. For each of their 3 problems: clearly labeled AGREE or DISAGREE with cited evidence from G2 or HN. Then 2 hidden long-term problems with evidence. Then a challenge to their competitor recommendation with evidence. Then a 1-10 rating of their analysis quality. Format with clear AGREE/DISAGREE labels.",
        agent=daily_driver,
        context=[round1],
    )

    # ROUND 3 — First-Timer fires back
    round3 = Task(
        description=f"""{context_block}You are the same first-time user from Round 1. You have just read a challenge from a power user who disagrees with parts of your analysis.

YOUR ASSIGNMENT:

1. DEFEND OR CONCEDE: For each point where the Daily Driver disagreed:
   - If you still believe you are right: explain why the power user's perspective is biased by familiarity. Cite evidence from the knowledge base below.
   - If the Daily Driver convinced you: concede clearly. Explain why the product team should STILL fix this — first-timer experience drives growth.

2. RESPOND TO THEIR HIDDEN PROBLEMS: The Daily Driver found 2 problems you missed. Do these change your overall assessment?

3. UPDATED VERDICT: Update your severity ratings. What changed? Revised stay-or-leave recommendation.

STUBBORNNESS RULE: Do not concede a point unless the Daily Driver provided specific cited evidence. "You get used to it" is an admission of failure, not a defense.

ONLY cite evidence from the knowledge base provided below — do not invent usernames or URLs.
{real_evidence}""",
        expected_output="Point-by-point defense or concession for each disagreement, with a confidence score 1-10 for each position. Response to the 2 hidden problems. Updated severity ratings with explanation. Revised stay-or-leave recommendation. Format as direct responses to each challenge.",
        agent=first_timer,
        context=[round1, round2],
    )

    # ROUND 4 — Buyer delivers final verdict
    round4 = Task(
        description=f"""{context_block}You are evaluating this productivity app for team-wide adoption: {product_description}

You have read the FULL debate. Now make the business decision.

YOUR ASSIGNMENT:

1. SETTLE EACH DISAGREEMENT: For every point where they disagreed — state who is right based on evidence from below. What does each disagreement reveal about the product's maturity?

2. BUSINESS-CRITICAL ASSESSMENT using evidence from the knowledge base:
   - PRICING: Fair at team scale? Features locked behind enterprise tiers?
   - INTEGRATIONS: Actually works with tools teams use?
   - DATA: Can you export if you leave? Vendor lock-in risk?
   - ADMIN: Team management, permissions, audit trails?

3. THE BLIND SPOT: ONE strategic problem both analysts missed — about the MARKET, not the product.

4. FINAL VERDICT:
   A. BUY DECISION: YES, NO, or YES WITH CONDITIONS. Not "it depends."
   B. OVERALL SCORE: 1-100, defensible with evidence from below.
   C. TOP 3 FIXES: Priority-ranked. For each: PM sprint description, cited evidence, estimated retention impact.
   D. COMPETITIVE POSITIONING: Where this sits vs top 3 competitors, defensible advantage, fatal gap.

You are spending real budget. Make the decision. Own it.

ONLY cite evidence from the knowledge base provided below — do not invent usernames or URLs.
{real_evidence}""",
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
        task_callback=task_callback,
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
