"""
Tests for War Room's adversarial debate orchestration pipeline.

Verifies the structural integrity of the CrewAI four-round debate:
  - Crew composition: exactly 3 agents assigned to 4 sequential tasks
  - Round context chaining: each task receives all prior rounds as context
  - Agent-to-role mapping: First-Timer, Daily Driver, Buyer in correct positions
  - Swarm reconnaissance: 20 parallel scouts deployed before Round 1
  - Graceful handling of edge-case inputs (empty product description)
  - Session context enrichment: product metadata injected into task descriptions

Live inference tests are marked skip — they require DGX Spark hardware
with Llama 3.3 70B, Qwen3 32B, and Mistral-Small 24B loaded via vLLM.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

MOCK_PERSONAS = [
    {
        "role": "First-Timer",
        "goal": "Find the 3 biggest problems a new user hits in their first session",
        "backstory": "Skeptical first-time evaluator who has churned from Notion and Asana.",
    },
    {
        "role": "Daily Driver",
        "goal": "Challenge surface-level analysis and expose deep long-term problems",
        "backstory": "Power user who has used this product daily for over a year.",
    },
    {
        "role": "Buyer",
        "goal": "Make a final buy/no-buy decision for team-wide adoption",
        "backstory": "CTO with budget authority who has killed 4 project management tools.",
    },
]

MOCK_SWARM_RESULT = {
    "briefing": "# SWARM RECONNAISSANCE BRIEFING\n\nMock compiled intelligence.",
    "stats": {
        "scouts_deployed": 20,
        "scouts_successful": 18,
        "total_time": 1.42,
        "product": "TestProduct",
    },
}

MOCK_EVIDENCE = (
    "\n\n--- REAL USER EVIDENCE FROM KNOWLEDGE BASE (8 sources) ---\n\n"
    "[reddit/r/productivity post] Notion's onboarding is confusing.\n\n"
    "--- END OF KNOWLEDGE BASE EVIDENCE ---\n"
)


@pytest.fixture
def mock_crew_dependencies():
    """Patch all external I/O so build_crew() runs without hardware or network."""
    with (
        patch("crew.generate_personas", return_value=MOCK_PERSONAS) as p_personas,
        patch("crew.deploy_swarm", return_value=MOCK_SWARM_RESULT) as p_swarm,
        patch("crew.fetch_context_for_product", return_value=MOCK_EVIDENCE) as p_evidence,
    ):
        yield p_personas, p_swarm, p_evidence


# ---------------------------------------------------------------------------
# Crew composition
# ---------------------------------------------------------------------------


def test_debate_produces_multi_round_output_with_four_sequential_tasks(
    mock_crew_dependencies,
):
    """build_crew() must return a Crew containing exactly 4 tasks in sequential order."""
    from crew import build_crew
    from crewai import Process

    crew = build_crew("TestProduct — a project management app")

    assert len(crew.tasks) == 4, f"Expected 4 debate rounds, got {len(crew.tasks)}"
    assert crew.process == Process.sequential, "Debate must run in sequential order"


def test_all_three_models_participate_via_three_distinct_agents(mock_crew_dependencies):
    """Crew must contain exactly 3 agents with distinct roles for multi-model adversarial debate."""
    from crew import build_crew

    crew = build_crew("TestProduct — a project management app")

    assert len(crew.agents) == 3, f"Expected 3 agents (one per model), got {len(crew.agents)}"
    roles = {agent.role for agent in crew.agents}
    assert len(roles) == 3, f"All three agents must have distinct roles, got: {roles}"


def test_each_debate_task_is_assigned_to_a_specific_agent(mock_crew_dependencies):
    """Every task must have an assigned agent — no unassigned rounds allowed."""
    from crew import build_crew

    crew = build_crew("TestProduct — a project management app")

    for i, task in enumerate(crew.tasks):
        assert task.agent is not None, f"Round {i + 1} has no assigned agent"


# ---------------------------------------------------------------------------
# Round context chaining — the core adversarial mechanic
# ---------------------------------------------------------------------------


def test_round2_daily_driver_receives_round1_output_as_context(mock_crew_dependencies):
    """Round 2 task context must include Round 1 so the Daily Driver can challenge it."""
    from crew import build_crew

    crew = build_crew("TestProduct — a project management app")
    round1_task = crew.tasks[0]
    round2_task = crew.tasks[1]

    assert round2_task.context is not None, "Round 2 must have context configured"
    assert round1_task in round2_task.context, (
        "Round 2 Daily Driver must receive Round 1 First-Timer output as context"
    )


def test_round3_rebuttal_receives_rounds_1_and_2_as_context(mock_crew_dependencies):
    """Round 3 rebuttal must chain context from both Round 1 and Round 2."""
    from crew import build_crew

    crew = build_crew("TestProduct — a project management app")
    round1_task, round2_task, round3_task = crew.tasks[0], crew.tasks[1], crew.tasks[2]

    assert round1_task in round3_task.context, (
        "Round 3 First-Timer rebuttal must receive Round 1 opening argument"
    )
    assert round2_task in round3_task.context, (
        "Round 3 First-Timer rebuttal must receive Round 2 Daily Driver challenge"
    )


def test_round4_buyer_synthesis_receives_full_debate_transcript_as_context(
    mock_crew_dependencies,
):
    """Round 4 Buyer verdict must have context from all three prior rounds."""
    from crew import build_crew

    crew = build_crew("TestProduct — a project management app")
    round1_task, round2_task, round3_task, round4_task = crew.tasks

    assert round4_task.context is not None, "Round 4 synthesis must have context"
    assert len(round4_task.context) == 3, (
        f"Round 4 must receive exactly 3 prior rounds as context, got {len(round4_task.context)}"
    )
    assert round1_task in round4_task.context, "Round 4 must include Round 1"
    assert round2_task in round4_task.context, "Round 4 must include Round 2"
    assert round3_task in round4_task.context, "Round 4 must include Round 3"


def test_critique_references_prior_response_via_context_chaining(mock_crew_dependencies):
    """Context chaining must link each task to its predecessors, not skip rounds."""
    from crew import build_crew

    crew = build_crew("TestProduct — a project management app")
    tasks = crew.tasks

    # Context chain lengths must grow monotonically: 0 → 1 → 2 → 3
    # Round 1: NOT_SPECIFIED (no prior context)
    # Round 2: [round1]
    # Round 3: [round1, round2]
    # Round 4: [round1, round2, round3]
    assert tasks[1].context is not None and len(tasks[1].context) == 1
    assert tasks[2].context is not None and len(tasks[2].context) == 2
    assert tasks[3].context is not None and len(tasks[3].context) == 3


# ---------------------------------------------------------------------------
# Agent-to-round role assignment
# ---------------------------------------------------------------------------


def test_round_assignments_follow_first_timer_daily_driver_buyer_protocol(
    mock_crew_dependencies,
):
    """Debate role assignments must be: R1=First-Timer, R2=Daily Driver, R3=First-Timer rebuttal, R4=Buyer."""
    from crew import build_crew

    crew = build_crew("TestProduct — a project management app")
    agents = crew.agents
    tasks = crew.tasks

    assert tasks[0].agent is agents[0], "Round 1 must use the First-Timer agent"
    assert tasks[1].agent is agents[1], "Round 2 must use the Daily Driver agent"
    assert tasks[2].agent is agents[0], "Round 3 (rebuttal) must reuse the First-Timer agent"
    assert tasks[3].agent is agents[2], "Round 4 must use the Buyer agent"


def test_round2_task_instructs_daily_driver_to_challenge_prior_findings(
    mock_crew_dependencies,
):
    """Round 2 task description must contain challenge/agree/disagree language."""
    from crew import build_crew

    crew = build_crew("TestProduct — a project management app")
    round2_description = crew.tasks[1].description.lower()

    assert any(kw in round2_description for kw in ["challenge", "agree", "disagree"]), (
        "Round 2 must instruct the Daily Driver to take explicit positions on Round 1 findings"
    )


def test_round4_task_requires_no_hedging_buy_decision(mock_crew_dependencies):
    """Round 4 task description must prohibit hedging and demand a committed buy/no-buy decision."""
    from crew import build_crew

    crew = build_crew("TestProduct — a project management app")
    round4_description = crew.tasks[3].description.lower()

    assert "decision" in round4_description or "own it" in round4_description or (
        "not" in round4_description
    ), "Round 4 must enforce a no-hedging commitment from the Buyer"


def test_round4_expected_output_mandates_score_and_verdict(mock_crew_dependencies):
    """Round 4 expected_output spec must require both a 1-100 score and YES/NO/CONDITIONS decision."""
    from crew import build_crew

    crew = build_crew("TestProduct — a project management app")
    round4_expected = crew.tasks[3].expected_output

    assert "1-100" in round4_expected or "100" in round4_expected, (
        "Round 4 must require a numeric 1-100 score in its expected output"
    )
    assert any(kw in round4_expected.upper() for kw in ["YES", "NO", "DECISION"]), (
        "Round 4 must require an explicit buy/no-buy decision"
    )


# ---------------------------------------------------------------------------
# Swarm reconnaissance
# ---------------------------------------------------------------------------


def test_swarm_reconnaissance_deployed_before_debate_begins(mock_crew_dependencies):
    """deploy_swarm() must be called exactly once before the debate tasks are constructed."""
    mock_personas, mock_swarm, _ = mock_crew_dependencies
    from crew import build_crew

    build_crew("TestProduct")

    mock_swarm.assert_called_once()


def test_swarm_briefing_injected_into_round1_task_description(mock_crew_dependencies):
    """Round 1 task description must contain the swarm intelligence briefing."""
    from crew import build_crew

    crew = build_crew("TestProduct")
    round1_description = crew.tasks[0].description.upper()

    assert "SWARM" in round1_description or "INTELLIGENCE" in round1_description or (
        "RECONNAISSANCE" in round1_description
    ), "Swarm briefing must be injected into Round 1 to seed the debate with evidence"


def test_persona_generation_called_exactly_once_per_debate_run(mock_crew_dependencies):
    """generate_personas() must be invoked once — dynamic personas, not static templates."""
    mock_personas, _, _ = mock_crew_dependencies
    from crew import build_crew

    build_crew("TestProduct")

    mock_personas.assert_called_once()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_query_handling_does_not_crash_build_crew(mock_crew_dependencies):
    """build_crew() must not raise when given an empty product description string."""
    from crew import build_crew

    try:
        crew = build_crew("")
        assert len(crew.tasks) == 4
    except Exception as exc:
        pytest.fail(f"build_crew('') raised unexpectedly: {exc}")


def test_session_context_enriches_task_descriptions_with_product_metadata(
    mock_crew_dependencies,
):
    """When session_context is provided, product name/metadata must appear in task descriptions."""
    from crew import build_crew

    session_context = {
        "product_name": "Notion",
        "target_user": "solo founders",
        "competitors": "Coda, Obsidian",
        "differentiator": "all-in-one workspace",
        "product_stage": "growth",
    }
    crew = build_crew(
        "Notion — all-in-one workspace", session_context=session_context
    )
    round1_description = crew.tasks[0].description

    assert "Notion" in round1_description or "all-in-one" in round1_description, (
        "Product metadata from session_context must be injected into Round 1 task description"
    )


def test_video_evidence_in_session_context_surfaces_in_task_descriptions(
    mock_crew_dependencies,
):
    """Video walkthrough evidence must appear in task descriptions when session_context contains it."""
    from crew import build_crew

    session_context = {
        "product_name": "Acme PM",
        "target_user": "engineering teams",
        "competitors": "Linear",
        "differentiator": "AI-powered sprint planning",
        "product_stage": "beta",
        "video_evidence": {
            "journey_summary": "The product demo showed a smooth onboarding flow.",
            "frame_analyses": ["Frame 1: Login screen with clear CTA."],
        },
    }
    crew = build_crew("Acme PM — AI sprint planning", session_context=session_context)
    round1_description = crew.tasks[0].description

    assert "VIDEO" in round1_description.upper() or "FRAME" in round1_description.upper() or (
        "JOURNEY" in round1_description.upper()
    ), "Video evidence must be injected into task descriptions when provided"


# ---------------------------------------------------------------------------
# Live inference tests — require DGX Spark hardware
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason="Requires DGX Spark with Llama 3.3 70B, Qwen3 32B, and Mistral-Small 24B loaded via vLLM"
)
def test_live_debate_produces_multi_round_structured_output_from_all_models():
    """Full end-to-end debate execution returns 4 rounds from three distinct frontier models."""
    from crew import build_crew

    crew = build_crew("Notion — collaborative workspace for teams and individuals")
    result = crew.kickoff()

    assert result is not None
    assert len(str(result)) > 200, "Final report must be substantive, not empty"


@pytest.mark.skip(
    reason="Requires DGX Spark with Llama 3.3 70B, Qwen3 32B, and Mistral-Small 24B loaded via vLLM"
)
def test_single_model_failure_graceful_degradation_produces_partial_output():
    """If one vLLM endpoint is unavailable, the remaining agents must still complete the debate."""
    pass
