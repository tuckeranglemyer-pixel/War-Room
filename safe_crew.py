"""
Safe CrewAI orchestration for The War Room — DGX Spark thermal-safe variant.

Loads only ONE model at a time, monitors temperature/memory between rounds,
pauses if thermal limits are hit, and unloads models between rounds to prevent
cumulative memory pressure from causing hardware shutdowns.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Any, Callable, Optional

import psutil
from crewai import Agent, Crew, LLM, Process, Task

from config import (
    CHROMA_DB_PATH,
    COLLECTION_NAME,
    LOCAL_BASE_URL,
    MAX_SCOUTS,
    RAG_RESULTS_PER_QUERY,
)
from meta_prompt import generate_personas
from tools import fetch_context_for_product, search_pm_knowledge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("safe_crew.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("safe_crew")

THERMAL_CEILING_C = 85
THERMAL_RESUME_C = 75
COOLDOWN_BETWEEN_ROUNDS_S = 10
SAFE_SWARM_WORKERS = 5
SAFE_SWARM_SCOUTS = 15

# DGX model names — adjust to match your Ollama tags
ROUND_MODELS: dict[str, str] = {
    "first_timer": os.environ.get("FIRST_TIMER_MODEL", "llama3.1:8b"),
    "daily_driver": os.environ.get("DAILY_DRIVER_MODEL", "llama3.3:70b"),
    "buyer": os.environ.get("BUYER_MODEL", "mistral-small:24b"),
}


# ---------------------------------------------------------------------------
# Hardware monitoring helpers
# ---------------------------------------------------------------------------

def get_gpu_temp() -> Optional[float]:
    """Return current GPU temperature in Celsius via nvidia-smi, or None."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            text=True,
            timeout=5,
        )
        return float(out.strip().split("\n")[0])
    except Exception:
        return None


def get_gpu_memory() -> dict[str, Any]:
    """Return GPU memory stats in MiB via nvidia-smi."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,memory.free",
             "--format=csv,noheader,nounits"],
            text=True,
            timeout=5,
        )
        parts = [int(x.strip()) for x in out.strip().split(",")]
        return {"used_mib": parts[0], "total_mib": parts[1], "free_mib": parts[2]}
    except Exception:
        return {"used_mib": -1, "total_mib": -1, "free_mib": -1}


def get_cpu_temp() -> Optional[float]:
    """Return CPU temperature if available (Linux sensors or macOS)."""
    try:
        temps = psutil.sensors_temperatures()
        for name in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
            if name in temps and temps[name]:
                return temps[name][0].current
    except Exception:
        pass
    return None


def log_system_state(label: str) -> dict[str, Any]:
    """Log and return a snapshot of GPU temp, GPU mem, CPU temp, and RAM."""
    gpu_temp = get_gpu_temp()
    gpu_mem = get_gpu_memory()
    cpu_temp = get_cpu_temp()
    ram = psutil.virtual_memory()

    state = {
        "label": label,
        "gpu_temp_c": gpu_temp,
        "gpu_mem_used_mib": gpu_mem["used_mib"],
        "gpu_mem_total_mib": gpu_mem["total_mib"],
        "gpu_mem_free_mib": gpu_mem["free_mib"],
        "cpu_temp_c": cpu_temp,
        "ram_used_gb": round(ram.used / (1024 ** 3), 1),
        "ram_total_gb": round(ram.total / (1024 ** 3), 1),
        "ram_pct": ram.percent,
    }
    log.info(
        "[%s] GPU: %s°C | GPU Mem: %s/%s MiB | CPU: %s°C | RAM: %s/%s GB (%s%%)",
        label,
        gpu_temp or "N/A",
        gpu_mem["used_mib"],
        gpu_mem["total_mib"],
        cpu_temp or "N/A",
        state["ram_used_gb"],
        state["ram_total_gb"],
        ram.percent,
    )
    return state


def wait_for_thermal_safe() -> None:
    """Block until GPU temperature drops below THERMAL_RESUME_C."""
    temp = get_gpu_temp()
    if temp is None:
        log.warning("Cannot read GPU temp — skipping thermal gate")
        return
    if temp < THERMAL_CEILING_C:
        return

    log.warning("GPU at %s°C — exceeds %s°C ceiling. Pausing until <%s°C...",
                temp, THERMAL_CEILING_C, THERMAL_RESUME_C)
    while True:
        time.sleep(5)
        temp = get_gpu_temp()
        if temp is None:
            log.warning("Lost GPU temp sensor — proceeding cautiously")
            return
        log.info("  Cooling... GPU at %s°C (target <%s°C)", temp, THERMAL_RESUME_C)
        if temp < THERMAL_RESUME_C:
            log.info("GPU cooled to %s°C — resuming", temp)
            return


# ---------------------------------------------------------------------------
# Ollama model management — load one at a time
# ---------------------------------------------------------------------------

def ollama_load_model(model_tag: str) -> None:
    """Pull model into Ollama cache and warm it with a trivial prompt."""
    log.info("Loading model: %s", model_tag)
    try:
        subprocess.run(["ollama", "pull", model_tag], check=True, timeout=600)
    except subprocess.TimeoutExpired:
        log.warning("ollama pull timed out for %s — model may already be cached", model_tag)
    except Exception as exc:
        log.error("Failed to pull %s: %s", model_tag, exc)


def ollama_stop_model(model_tag: str) -> None:
    """Unload a model from Ollama's VRAM via `ollama stop`."""
    log.info("Unloading model: %s", model_tag)
    try:
        subprocess.run(["ollama", "stop", model_tag], check=True, timeout=30)
        time.sleep(2)
    except Exception as exc:
        log.warning("Could not stop %s (may already be unloaded): %s", model_tag, exc)


def ollama_stop_all() -> None:
    """Stop every model Ollama currently has loaded."""
    try:
        out = subprocess.check_output(["ollama", "list"], text=True, timeout=10)
        for line in out.strip().split("\n")[1:]:
            tag = line.split()[0]
            if tag:
                ollama_stop_model(tag)
    except Exception as exc:
        log.warning("Could not enumerate running models: %s", exc)


# ---------------------------------------------------------------------------
# Safe swarm (reduced parallelism)
# ---------------------------------------------------------------------------

def safe_deploy_swarm(product_name: str) -> dict[str, Any]:
    """Deploy swarm with reduced worker count to limit concurrent GPU load."""
    from swarm import deploy_swarm

    log.info("Deploying safe swarm (%d scouts, %d workers)", SAFE_SWARM_SCOUTS, SAFE_SWARM_WORKERS)
    return deploy_swarm(
        product_name,
        max_scouts=SAFE_SWARM_SCOUTS,
        max_workers=SAFE_SWARM_WORKERS,
    )


# ---------------------------------------------------------------------------
# Round runner — one model loaded per round
# ---------------------------------------------------------------------------

def run_round(
    task: Task,
    crew_agents: list[Agent],
    round_label: str,
    model_tag: str,
    task_callback: Optional[Callable[..., None]] = None,
) -> str:
    """Execute a single debate round with isolated model loading.

    Returns the task output text.
    """
    log_system_state(f"PRE-{round_label}")
    wait_for_thermal_safe()

    ollama_stop_all()
    time.sleep(3)
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
    log.info("Cooling pause: %ds between rounds", COOLDOWN_BETWEEN_ROUNDS_S)
    time.sleep(COOLDOWN_BETWEEN_ROUNDS_S)
    log_system_state(f"COOLED-{round_label}")

    return output


# ---------------------------------------------------------------------------
# Main build & run
# ---------------------------------------------------------------------------

def build_and_run_safe(
    product_description: str,
    task_callback: Optional[Callable[..., None]] = None,
    session_context: Optional[dict[str, Any]] = None,
) -> str:
    """Run a full 4-round War Room debate with single-model-at-a-time safety.

    Returns the final Round 4 verdict text.
    """
    log.info("=" * 60)
    log.info("SAFE WAR ROOM — Starting thermal-safe debate")
    log.info("Product: %s", product_description)
    log_system_state("STARTUP")

    # --- Step 0: Unload everything before we begin ---
    ollama_stop_all()
    time.sleep(3)

    # --- Step 0b: Build session context block ---
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
        log.error("Persona generation failed: %s", exc)
        personas = generate_personas(product_description, persona_llm)

    ollama_stop_model(ft_model)
    time.sleep(5)

    # --- Step 2: Deploy safe swarm ---
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
    except Exception as exc:
        log.error("Evidence fetch failed: %s", exc)
        real_evidence = "[Evidence unavailable]"

    log_system_state("POST-EVIDENCE")

    # --- Step 4: Run each round with isolated model loading ---

    agent_tools = [search_pm_knowledge]
    round_outputs: list[str] = []

    # ---- ROUND 1: First-Timer (llama3.1:8b or llama3.3:70b) ----
    log.info("=" * 40)
    log.info("ROUND 1 — First-Timer Analysis")
    r1_model = ROUND_MODELS["first_timer"]
    r1_llm = LLM(model=f"ollama/{r1_model}", base_url=LOCAL_BASE_URL)

    first_timer = Agent(
        role=personas[0]["role"],
        goal=personas[0]["goal"],
        backstory=personas[0]["backstory"]
        + "\n\nEVIDENCE PREFERENCE: You trust App Store reviews and Reddit first impressions."
        + "\n\nCRITICAL TOOL RULE: You MUST use the search_pm_knowledge tool to gather real user evidence BEFORE making any argument.",
        llm=r1_llm,
        tools=agent_tools,
        max_iter=10,
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

    r1_output = run_round(
        round1_task, [first_timer], "R1", r1_model, task_callback,
    )
    round_outputs.append(r1_output)

    # ---- ROUND 2: Daily Driver ----
    log.info("=" * 40)
    log.info("ROUND 2 — Daily Driver Challenge")
    r2_model = ROUND_MODELS["daily_driver"]
    r2_llm = LLM(model=f"ollama/{r2_model}", base_url=LOCAL_BASE_URL)

    daily_driver = Agent(
        role=personas[1]["role"],
        goal=personas[1]["goal"],
        backstory=personas[1]["backstory"]
        + "\n\nEVIDENCE PREFERENCE: You trust G2 reviews and Hacker News discussions."
        + "\n\nCRITICAL TOOL RULE: You MUST use the search_pm_knowledge tool.",
        llm=r2_llm,
        tools=agent_tools,
        max_iter=10,
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

    r2_output = run_round(
        round2_task, [daily_driver], "R2", r2_model, task_callback,
    )
    round_outputs.append(r2_output)

    # ---- ROUND 3: First-Timer fires back ----
    log.info("=" * 40)
    log.info("ROUND 3 — First-Timer Rebuttal")
    r3_model = ROUND_MODELS["first_timer"]
    r3_llm = LLM(model=f"ollama/{r3_model}", base_url=LOCAL_BASE_URL)

    first_timer_r3 = Agent(
        role=personas[0]["role"],
        goal=personas[0]["goal"],
        backstory=personas[0]["backstory"]
        + "\n\nSTUBBORNNESS RULE: Do not concede without specific cited evidence.",
        llm=r3_llm,
        tools=agent_tools,
        max_iter=10,
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

    r3_output = run_round(
        round3_task, [first_timer_r3], "R3", r3_model, task_callback,
    )
    round_outputs.append(r3_output)

    # ---- ROUND 4: Buyer verdict ----
    log.info("=" * 40)
    log.info("ROUND 4 — Buyer Final Verdict")
    r4_model = ROUND_MODELS["buyer"]
    r4_llm = LLM(model=f"ollama/{r4_model}", base_url=LOCAL_BASE_URL)

    buyer = Agent(
        role=personas[2]["role"],
        goal=personas[2]["goal"],
        backstory=personas[2]["backstory"]
        + "\n\nEVIDENCE PREFERENCE: You trust pricing comparisons and business user reviews.",
        llm=r4_llm,
        tools=agent_tools,
        max_iter=10,
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

    r4_output = run_round(
        round4_task, [buyer], "R4", r4_model, task_callback,
    )
    round_outputs.append(r4_output)

    # --- Final cleanup ---
    ollama_stop_all()
    log_system_state("FINAL")

    log.info("=" * 60)
    log.info("SAFE WAR ROOM — Debate complete")

    final_report = f"""
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
    return final_report


if __name__ == "__main__":
    product = input("Enter product to analyze (name + description): ")
    print("\n🔥 THE WAR ROOM — Thermal-Safe Mode")
    print("   Loading one model at a time to prevent DGX shutdown\n")
    report = build_and_run_safe(product)
    print(report)
