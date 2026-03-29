"""
Adversarial debate engine — core four-round CrewAI orchestration.

Assembles three agents (First-Timer / Daily Driver / Buyer) backed by three
distinct model families (Llama 70B / Qwen 32B / Mistral 24B on DGX Spark),
generates adversarial personas via meta-prompting, runs swarm reconnaissance
across 31K RAG chunks, and wires four sequential critique rounds with explicit
context chaining:

  Round 1: First-Timer opens with onboarding audit + 3 problems
  Round 2: Daily Driver challenges Round 1 (AGREE/DISAGREE with evidence)
  Round 3: First-Timer rebuts Round 2 (defend or concede with cited evidence)
  Round 4: Buyer synthesizes full debate → YES/NO/CONDITIONS + 1-100 score

Context chaining makes this adversarial: each agent reads what prior agents
wrote before taking a position. Models cannot converge to vague consensus
because they're forced to take explicit positions on prior claims.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from crewai import Agent, Crew, LLM, Process, Task

from src.inference.model_config import (
    BUYER_MODEL,
    DAILY_DRIVER_MODEL,
    FIRST_TIMER_MODEL,
    LOCAL_BASE_URL,
    LOCAL_MODEL,
    MAX_SCOUTS,
    MAX_WORKERS,
)
from src.orchestration.persona_generator import generate_personas
from src.orchestration.swarm_reconnaissance import deploy_swarm
from src.rag.chroma_retrieval import (
    fetch_context_for_product,
    search_app_reviews,
    search_competitor_data,
    search_hn_comments,
    search_pm_knowledge,
    search_reddit,
    search_screenshots,
)

# ---------------------------------------------------------------------------
# LLM instances — three distinct model architectures for adversarial debate
#
# Each agent runs a different model family to guarantee independent analytical
# perspectives. On DGX Spark these load concurrently into 128 GB unified memory;
# on local hardware use thermal_safe_debate_runner for sequential model swaps.
# ---------------------------------------------------------------------------

local_llm = LLM(model=LOCAL_MODEL, base_url=LOCAL_BASE_URL)       # persona gen + swarm
first_timer_llm = LLM(model=FIRST_TIMER_MODEL, base_url=LOCAL_BASE_URL)    # Llama 3.3 70B
daily_driver_llm = LLM(model=DAILY_DRIVER_MODEL, base_url=LOCAL_BASE_URL)  # Qwen3 32B
buyer_llm = LLM(model=BUYER_MODEL, base_url=LOCAL_BASE_URL)                # Mistral 24B

# Kept for backward compatibility with any callers that imported this name.
daily_driver_buyer_llm = daily_driver_llm


def build_crew(
    product_description: str,
    task_callback: Optional[Callable[..., None]] = None,
    session_context: Optional[dict[str, Any]] = None,
    evidence_tier: str = "full",
) -> Crew:
    """Assemble the War Room crew with generated personas, swarm briefing, and four tasks.

    Args:
        product_description: Product name and description to evaluate.
        task_callback: Optional CrewAI callback invoked after each task completes.
        session_context: Optional user evaluation context (target_user, competitors,
            differentiator, product_stage, video_evidence). When set, agents
            prioritize user-supplied evidence over general reviews.
        evidence_tier: "full" pre-fetches ChromaDB evidence and injects it into task
            prompts (default for the 20 curated products). "general" skips ChromaDB
            pre-fetch — agents rely on model knowledge and live search_pm_knowledge
            tool calls instead.

    Returns:
        A configured sequential Crew ready to kickoff().
    """

    # --- Step 0: Build session context block injected into every task ---
    context_block = ""
    if session_context:
        product_name = session_context.get("product_name", product_description)
        # Use the full description from context if available (set when product_name is sent separately)
        product_full_desc = session_context.get("product_description", product_description)
        target_user = session_context.get("target_user") or "Not specified"
        competitors = session_context.get("competitors") or "Not specified"
        differentiator = session_context.get("differentiator") or "Not specified"
        product_stage = session_context.get("product_stage") or "Not specified"

        product_section = f"""PRODUCT BEING EVALUATED:
- Product: {product_name}
- What it does: {product_full_desc}
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

            # Prefer the synthesised agent brief (curated themes + reviews + insights).
            # Fall back to raw similarity matches when synthesis is not available.
            synthesis = video_evidence.get("synthesis")
            if synthesis and synthesis.get("agent_brief"):
                context_block += "\n\n" + synthesis["agent_brief"]
            else:
                screenshot_matches = video_evidence.get("screenshot_matches", [])
                if screenshot_matches:
                    match_lines = [
                        "\n\nSCREENSHOT COMPARISON EVIDENCE "
                        "(user frames vs competitor UI patterns):\n"
                    ]
                    for m in screenshot_matches[:10]:
                        for comp in m.get("matched_competitors", [])[:2]:
                            match_lines.append(
                                f"\nUser Frame {m['frame_number']} matches "
                                f"{comp['app']}/{comp['filename']} "
                                f"(similarity: {comp['similarity_score']:.2f}):\n"
                                f"Competitor analysis: {comp['document'][:500]}...\n"
                            )
                    context_block += "".join(match_lines)
        else:
            context_block = product_section

    agent_tools = [
        search_pm_knowledge,
        search_app_reviews,
        search_reddit,
        search_hn_comments,
        search_competitor_data,
        search_screenshots,
    ]

    # --- Step 1: Generate personas via meta-prompt ---
    personas = generate_personas(product_description, local_llm)

    # --- Step 1.5: Deploy reconnaissance swarm ---
    # ChromaDB is local-only; on Railway/cloud the swarm gracefully returns an
    # empty briefing (scouts detect the missing collection and are filtered out).
    # The outer try/except is a safety net in case deploy_swarm itself throws.
    try:
        swarm_result = deploy_swarm(
            product_description,
            max_scouts=MAX_SCOUTS,
            max_workers=MAX_WORKERS,
        )
        swarm_briefing = swarm_result["briefing"]
        swarm_stats = swarm_result["stats"]
    except Exception as swarm_exc:
        print(f"⚠️  Swarm reconnaissance unavailable (non-fatal): {swarm_exc}")
        swarm_briefing = "[Swarm reconnaissance unavailable — proceeding without pre-fetched evidence]"
        swarm_stats = {
            "scouts_deployed": 0,
            "scouts_successful": 0,
            "total_time": 0,
            "product": product_description,
        }

    # --- Step 1b: Pre-fetch real evidence from ChromaDB ---
    # "full" tier: inject pre-fetched evidence directly into task descriptions so
    # small local models have a guaranteed knowledge base to cite from.
    # "general" tier: skip pre-fetch — agents rely on model knowledge and live
    # search_pm_knowledge tool calls (no cached RAG citations in prompts).
    if evidence_tier == "full":
        print("\n📚 Fetching real user evidence from knowledge base...")
        real_evidence = fetch_context_for_product(product_description)
        evidence_count = real_evidence.count("[") - real_evidence.count("[Query error")
        print(f"   → Loaded {evidence_count} real evidence chunks for debate context\n")
    else:
        real_evidence = (
            "[General analysis mode — no pre-seeded ChromaDB evidence. "
            "Use search_pm_knowledge tool calls to gather evidence during debate.]"
        )
        print("\n📚 General analysis mode — skipping ChromaDB pre-fetch\n")

    # --- Step 2: Create Agents ---
    first_timer = Agent(
        role=personas[0]["role"],
        goal=personas[0]["goal"],
        backstory=(
            personas[0]["backstory"]
            + "\n\nEVIDENCE PREFERENCE: You trust App Store reviews and Reddit first impressions — the voice of normal users. When searching the knowledge base, prioritize these sources."
            + "\n\nCRITICAL TOOL RULE: You MUST use the search_pm_knowledge tool to gather real user evidence BEFORE making any argument. Never argue from general knowledge alone — always search first. Every claim you make must be backed by evidence from the knowledge base. If you cannot find evidence for a claim, say so explicitly."
        ),
        llm=first_timer_llm,
        tools=agent_tools,
        max_iter=10,
        verbose=True,
    )

    daily_driver = Agent(
        role=personas[1]["role"],
        goal=personas[1]["goal"],
        backstory=(
            personas[1]["backstory"]
            + "\n\nEVIDENCE PREFERENCE: You trust long-form G2 reviews and Hacker News technical discussions — the voice of power users. When searching the knowledge base, prioritize these sources."
            + "\n\nCRITICAL TOOL RULE: You MUST use the search_pm_knowledge tool to gather real user evidence BEFORE making any argument. Never argue from general knowledge alone — always search first. Every claim you make must be backed by evidence from the knowledge base. If you cannot find evidence for a claim, say so explicitly."
        ),
        llm=daily_driver_llm,
        tools=agent_tools,
        max_iter=10,
        verbose=True,
    )

    buyer = Agent(
        role=personas[2]["role"],
        goal=personas[2]["goal"],
        backstory=(
            personas[2]["backstory"]
            + "\n\nEVIDENCE PREFERENCE: You trust pricing comparisons, feature matrices, and business user reviews — the voice of decision-makers. When searching the knowledge base, prioritize these sources."
            + "\n\nCRITICAL TOOL RULE: You MUST use the search_pm_knowledge tool to gather real user evidence BEFORE making any argument. Never argue from general knowledge alone — always search first. Every claim you make must be backed by evidence from the knowledge base. If you cannot find evidence for a claim, say so explicitly."
        ),
        llm=buyer_llm,
        tools=agent_tools,
        max_iter=10,
        verbose=True,
    )

    # --- Step 3: Create Tasks (4 rounds, sequential with context chaining) ---

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
