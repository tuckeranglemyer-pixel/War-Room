"""
Thermal-safe adversarial debate runner for DGX Spark.

Runs the full four-round debate with single-model-at-a-time loading:
  1. Unload all models before starting
  2. Load only the round's model into VRAM
  3. Run the round
  4. Unload the model
  5. Cooldown pause
  6. Thermal gate — block if GPU exceeds THERMAL_CEILING_C

This prevents cumulative VRAM pressure from crashing the DGX Spark
mid-debate. The tradeoff is ~30-second pauses between rounds vs the
faster but riskier concurrent-model approach in adversarial_debate_engine.py.

Env vars (all optional):
  SAFE_THERMAL_CEILING / SAFE_THERMAL_RESUME — pause/resume temps (default 75/65°C)
  SAFE_COOLDOWN_S — seconds between rounds (default 30)
  SAFE_PRE_ROUND_PAUSE_S — idle before loading model (default 15)
  SAFE_MAX_ITER — agent tool loop cap (default 4)
  SAFE_EVIDENCE_MAX_CHARS — truncate injected RAG block (default 12000)
  SAFE_SKIP_SWARM=1 — skip parallel Chroma scout queries entirely
  SAFE_SWARM_SCOUTS / SAFE_SWARM_WORKERS — default 10 scouts, 3 workers
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from crewai import Agent, Crew, LLM, Process, Task

from src.inference.model_config import LOCAL_BASE_URL
from src.inference.vllm_multi_model_dispatch import (
    COOLDOWN_BETWEEN_ROUNDS_S,
    PRE_ROUND_PAUSE_S,
    ROUND_MODELS,
    SAFE_EVIDENCE_MAX_CHARS,
    SAFE_MAX_ITER,
    SAFE_SWARM_SCOUTS,
    SAFE_SWARM_WORKERS,
    SKIP_SWARM,
    log_system_state,
    ollama_load_model,
    ollama_stop_all,
    ollama_stop_model,
    wait_for_thermal_safe,
)
from src.orchestration.persona_generator import generate_personas
from src.orchestration.swarm_reconnaissance import deploy_swarm
from src.rag.chroma_retrieval import fetch_context_for_product, search_pm_knowledge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("thermal_safe_debate_runner.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("thermal_safe_debate_runner")


# ---------------------------------------------------------------------------
# Safe swarm (reduced parallelism to limit concurrent GPU load)
# ---------------------------------------------------------------------------


def safe_deploy_swarm(product_name: str) -> dict[str, Any]:
    """Deploy swarm with reduced worker count to limit concurrent GPU load."""
    log.info("Deploying safe swarm (%d scouts, %d workers)", SAFE_SWARM_SCOUTS, SAFE_SWARM_WORKERS)
    return deploy_swarm(
        product_name,
        max_scouts=SAFE_SWARM_SCOUTS,
        max_workers=SAFE_SWARM_WORKERS,
    )


def maybe_truncate_evidence(text: str) -> str:
    """Limit injected evidence size to reduce KV cache and sustained GPU load."""
    if len(text) <= SAFE_EVIDENCE_MAX_CHARS:
        return text
    log.warning(
        "Truncating real_evidence from %d to %d chars (SAFE_EVIDENCE_MAX_CHARS)",
        len(text),
        SAFE_EVIDENCE_MAX_CHARS,
    )
    return text[:SAFE_EVIDENCE_MAX_CHARS] + "\n\n[… evidence truncated for SAFE mode …]\n"


# ---------------------------------------------------------------------------
# Single-round runner — one model loaded per round
# ---------------------------------------------------------------------------


def run_round(
    task: Task,
    crew_agents: list[Agent],
    round_label: str,
    model_tag: str,
    task_callback: Optional[Callable[..., None]] = None,
) -> str:
    """Execute a single debate round with isolated model loading.

    Unloads all models, waits for thermal safety, loads only the round's
    model, runs the crew, then unloads and cools before returning.

    Args:
        task: CrewAI Task for this round.
        crew_agents: List containing the single agent for this round.
        round_label: Human-readable label (e.g. "R1") for log messages.
        model_tag: Ollama model tag to load (e.g. "llama3.3:70b").
        task_callback: Optional CrewAI task callback.

    Returns:
        Task output as a string.
    """
    log_system_state(f"PRE-{round_label}")
    wait_for_thermal_safe()

    ollama_stop_all()
    time.sleep(3)
    if PRE_ROUND_PAUSE_S > 0:
        log.info("Pre-round pause: %ds (SAFE_PRE_ROUND_PAUSE_S)", PRE_ROUND_PAUSE_S)
        time.sleep(PRE_ROUND_PAUSE_S)
    ollama_load_model(model_tag)
    log_system_state(f"MODEL-LOADED-{round_label}")

    try:
        mini_crew = Crew(
            agents=crew_agents,
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            task_callback=task_callback,
        )
        result = mini_crew.kickoff()
        output = str(result)
    except Exception as exc:
        log.error("Round %s FAILED: %s", round_label, exc, exc_info=True)
        output = f"[Round {round_label} failed: {exc}]"

    log_system_state(f"POST-{round_label}")
    ollama_stop_model(model_tag)
    log.info("Cooling pause: %ds between rounds (SAFE_COOLDOWN_S)", COOLDOWN_BETWEEN_ROUNDS_S)
    time.sleep(COOLDOWN_BETWEEN_ROUNDS_S)
    log_system_state(f"COOLED-{round_label}")

    return output


# ---------------------------------------------------------------------------
# Full debate run — thermal-safe sequential execution
# ---------------------------------------------------------------------------


def build_and_run_safe(
    product_description: str,
    task_callback: Optional[Callable[..., None]] = None,
    session_context: Optional[dict[str, Any]] = None,
) -> str:
    """Run a full 4-round War Room debate with single-model-at-a-time thermal safety.

    Args:
        product_description: Product name and description to evaluate.
        task_callback: Optional CrewAI callback invoked after each task completes.
        session_context: Optional user evaluation context dict.

    Returns:
        Formatted final report string containing all four round outputs.
    """
    log.info("=" * 60)
    log.info("THERMAL-SAFE WAR ROOM — Starting debate")
    log.info("Product: %s", product_description)
    log_system_state("STARTUP")

    ollama_stop_all()
    time.sleep(3)

    # --- Build session context block ---
    context_block = ""
    if session_context:
        product_name = session_context.get("product_name", product_description)
        target_user = session_context.get("target_user") or "Not specified"
        competitors = session_context.get("competitors") or "Not specified"
        differentiator = session_context.get("differentiator") or "Not specified"
        product_stage = session_context.get("product_stage") or "Not specified"
        context_block = f"""PRODUCT BEING EVALUATED:
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
            context_block += f"""VIDEO EVIDENCE FROM FOUNDER'S PRODUCT WALKTHROUGH:

JOURNEY SUMMARY:
{journey_summary[:3000]}

KEY FRAME ANALYSES (up to 10 frames):
{frame_snippets}

CRITICAL: The above is PRIMARY evidence from the founder's live walkthrough.

"""

    # --- Step 1: Generate personas (uses small model) ---
    log.info("Step 1: Generating personas with small model")
    ft_model = ROUND_MODELS["first_timer"]
    ollama_load_model(ft_model)
    persona_llm = LLM(model=f"ollama/{ft_model}", base_url=LOCAL_BASE_URL)
    try:
        personas = generate_personas(product_description, persona_llm)
        log.info("Personas generated successfully")
    except Exception as exc:
        log.error("Persona generation failed: %s — retrying", exc)
        personas = generate_personas(product_description, persona_llm)
    ollama_stop_model(ft_model)
    time.sleep(5)

    # --- Step 2: Deploy safe swarm ---
    if SKIP_SWARM:
        log.info("Step 2: SAFE_SKIP_SWARM=1 — skipping reconnaissance swarm")
        swarm_briefing = "[Swarm skipped — SAFE_SKIP_SWARM]"
        swarm_stats: dict[str, Any] = {"scouts_deployed": 0, "total_time": 0}
    else:
        log.info("Step 2: Deploying safe reconnaissance swarm")
        log_system_state("PRE-SWARM")
        try:
            swarm_result = safe_deploy_swarm(product_description)
            swarm_briefing = swarm_result["briefing"]
            swarm_stats = swarm_result["stats"]
        except Exception as exc:
            log.error("Swarm failed: %s — continuing without briefing", exc)
            swarm_briefing = "[Swarm reconnaissance unavailable]"
            swarm_stats = {"scouts_deployed": 0, "total_time": 0}
        log_system_state("POST-SWARM")
        time.sleep(5)

    # --- Step 3: Pre-fetch evidence ---
    log.info("Step 3: Fetching evidence from ChromaDB")
    try:
        real_evidence = fetch_context_for_product(product_description)
        evidence_count = real_evidence.count("[") - real_evidence.count("[Query error")
        log.info("Loaded %d evidence chunks", evidence_count)
        real_evidence = maybe_truncate_evidence(real_evidence)
    except Exception as exc:
        log.error("Evidence fetch failed: %s", exc)
        real_evidence = "[Evidence unavailable]"
    log_system_state("POST-EVIDENCE")

    # --- Step 4: Run each round with isolated model loading ---
    agent_tools = [search_pm_knowledge]
    round_outputs: list[str] = []

    # Round 1 — First-Timer
    log.info("=" * 40)
    log.info("ROUND 1 — First-Timer Analysis")
    r1_model = ROUND_MODELS["first_timer"]
    r1_llm = LLM(model=f"ollama/{r1_model}", base_url=LOCAL_BASE_URL)
    first_timer = Agent(
        role=personas[0]["role"],
        goal=personas[0]["goal"],
        backstory=(
            personas[0]["backstory"]
            + "\n\nEVIDENCE PREFERENCE: You trust App Store reviews and Reddit first impressions."
            + "\n\nCRITICAL TOOL RULE: You MUST use the search_pm_knowledge tool to gather real user evidence BEFORE making any argument."
        ),
        llm=r1_llm,
        tools=agent_tools,
        max_iter=SAFE_MAX_ITER,
        verbose=True,
    )
    round1_task = Task(
        description=f"""{context_block}IMPORTANT: Use the search_pm_knowledge tool for EVERY point you make.

You are testing this productivity app: {product_description}

INTELLIGENCE BRIEFING: {swarm_stats.get('scouts_deployed', 0)} scouts gathered evidence.

{swarm_briefing[:3000]}

You are a first-time user. Give this product exactly one honest session.

YOUR ASSIGNMENT:
1. ONBOARDING AUDIT: First 2 minutes step by step. Where did you get confused?
2. FIND 3 CRITICAL PROBLEMS with severity ratings, cited evidence, competitor comparisons
3. ONE GENUINE STRENGTH with evidence

Do not write a balanced review. You are a real user with limited patience.""",
        expected_output="Onboarding audit, 3 critical problems with evidence and severity 1-10, 1 strength.",
        agent=first_timer,
    )
    r1_output = run_round(round1_task, [first_timer], "R1", r1_model, task_callback)
    round_outputs.append(r1_output)

    # Round 2 — Daily Driver
    log.info("=" * 40)
    log.info("ROUND 2 — Daily Driver Challenge")
    r2_model = ROUND_MODELS["daily_driver"]
    r2_llm = LLM(model=f"ollama/{r2_model}", base_url=LOCAL_BASE_URL)
    daily_driver = Agent(
        role=personas[1]["role"],
        goal=personas[1]["goal"],
        backstory=(
            personas[1]["backstory"]
            + "\n\nEVIDENCE PREFERENCE: You trust G2 reviews and Hacker News discussions."
            + "\n\nCRITICAL TOOL RULE: You MUST use the search_pm_knowledge tool."
        ),
        llm=r2_llm,
        tools=agent_tools,
        max_iter=SAFE_MAX_ITER,
        verbose=True,
    )
    round2_task = Task(
        description=f"""{context_block}You are a daily power user of: {product_description}

ROUND 1 OUTPUT (from the First-Timer):
{r1_output[:4000]}

YOUR ASSIGNMENT:
1. CHALLENGE EACH FINDING: AGREE (escalate) or DISAGREE (with evidence). Must disagree with at least one.
2. EXPOSE 2 HIDDEN PROBLEMS only long-term users would know.
3. CHALLENGE THEIR COMPETITOR PICK.
4. RATE THEIR ANALYSIS 1-10.

{real_evidence}""",
        expected_output="Point-by-point AGREE/DISAGREE with evidence, 2 hidden problems, competitor challenge, rating.",
        agent=daily_driver,
    )
    r2_output = run_round(round2_task, [daily_driver], "R2", r2_model, task_callback)
    round_outputs.append(r2_output)

    # Round 3 — First-Timer rebuttal
    log.info("=" * 40)
    log.info("ROUND 3 — First-Timer Rebuttal")
    r3_model = ROUND_MODELS["first_timer"]
    r3_llm = LLM(model=f"ollama/{r3_model}", base_url=LOCAL_BASE_URL)
    first_timer_r3 = Agent(
        role=personas[0]["role"],
        goal=personas[0]["goal"],
        backstory=(
            personas[0]["backstory"]
            + "\n\nSTUBBORNNESS RULE: Do not concede without specific cited evidence."
        ),
        llm=r3_llm,
        tools=agent_tools,
        max_iter=SAFE_MAX_ITER,
        verbose=True,
    )
    round3_task = Task(
        description=f"""{context_block}You are the same first-time user from Round 1. A power user challenged your findings.

YOUR ROUND 1 ANALYSIS:
{r1_output[:3000]}

DAILY DRIVER'S CHALLENGE (Round 2):
{r2_output[:4000]}

YOUR ASSIGNMENT:
1. DEFEND OR CONCEDE each disagreement with evidence.
2. RESPOND to their hidden problems.
3. UPDATED VERDICT with revised severity ratings.

{real_evidence}""",
        expected_output="Defense/concession for each point, response to hidden problems, updated ratings.",
        agent=first_timer_r3,
    )
    r3_output = run_round(round3_task, [first_timer_r3], "R3", r3_model, task_callback)
    round_outputs.append(r3_output)

    # Round 4 — Buyer verdict
    log.info("=" * 40)
    log.info("ROUND 4 — Buyer Final Verdict")
    r4_model = ROUND_MODELS["buyer"]
    r4_llm = LLM(model=f"ollama/{r4_model}", base_url=LOCAL_BASE_URL)
    buyer = Agent(
        role=personas[2]["role"],
        goal=personas[2]["goal"],
        backstory=(
            personas[2]["backstory"]
            + "\n\nEVIDENCE PREFERENCE: You trust pricing comparisons and business user reviews."
        ),
        llm=r4_llm,
        tools=agent_tools,
        max_iter=SAFE_MAX_ITER,
        verbose=True,
    )
    round4_task = Task(
        description=f"""{context_block}You are evaluating for team-wide adoption: {product_description}

FULL DEBATE TRANSCRIPT:

ROUND 1 (First-Timer):
{r1_output[:3000]}

ROUND 2 (Daily Driver):
{r2_output[:3000]}

ROUND 3 (First-Timer Rebuttal):
{r3_output[:3000]}

YOUR ASSIGNMENT:
1. SETTLE EACH DISAGREEMENT with evidence.
2. BUSINESS-CRITICAL: Pricing, integrations, data portability, admin controls.
3. ONE BLIND SPOT both analysts missed.
4. FINAL VERDICT: YES/NO/YES WITH CONDITIONS. Score 1-100. Top 3 fixes as sprint tickets.

{real_evidence}""",
        expected_output="Settled disagreements, business assessment, blind spot, verdict with score and fixes.",
        agent=buyer,
    )
    r4_output = run_round(round4_task, [buyer], "R4", r4_model, task_callback)
    round_outputs.append(r4_output)

    ollama_stop_all()
    log_system_state("FINAL")
    log.info("=" * 60)
    log.info("THERMAL-SAFE WAR ROOM — Debate complete")

    return f"""
{'=' * 60}
THE WAR ROOM — FINAL REPORT (Thermal-Safe Mode)
{'=' * 60}

ROUND 1 — First-Timer Analysis
{'-' * 40}
{round_outputs[0]}

ROUND 2 — Daily Driver Challenge
{'-' * 40}
{round_outputs[1]}

ROUND 3 — First-Timer Rebuttal
{'-' * 40}
{round_outputs[2]}

ROUND 4 — Buyer Verdict
{'-' * 40}
{round_outputs[3]}
"""


if __name__ == "__main__":
    product = input("Enter product to analyze (name + description): ")
    print("\n🔥 THE WAR ROOM — Thermal-Safe Mode")
    print("   Loading one model at a time to prevent DGX shutdown\n")
    report = build_and_run_safe(product)
    print(report)
