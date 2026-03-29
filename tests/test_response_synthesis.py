"""
Tests for War Room's response synthesis and verdict assembly pipeline.

The synthesis stage is Round 4: the Buyer agent reads the full debate
transcript, adjudicates every disagreement, and produces a structured verdict:
  - YES / NO / YES WITH CONDITIONS buy decision
  - 1-100 evidence-backed score
  - TOP 3 FIXES as actionable PM sprint tickets
  - Competitive positioning summary

The verdict parser (_parse_verdict) extracts machine-readable fields from
the Buyer's free-text output so the WebSocket layer can deliver structured
JSON to the frontend without any additional LLM calls.

Tests also cover the WebSocket streaming mechanism (DebateSession callback)
that delivers each round's output to the client in real time.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _parse_verdict: structured field extraction from free-text Round 4 output
# ---------------------------------------------------------------------------


def test_verdict_parser_extracts_integer_score_from_slash_100_notation():
    """_parse_verdict must extract a score written as 'N/100'."""
    from src.orchestration.response_synthesizer import _parse_verdict

    raw = "After reviewing all evidence, this product earns a score of 72/100."
    result = _parse_verdict(raw)

    assert result["score"] == 72, f"Expected score=72, got {result['score']}"


def test_verdict_parser_extracts_score_from_out_of_100_notation():
    """_parse_verdict must extract a score written as 'N out of 100'."""
    from src.orchestration.response_synthesizer import _parse_verdict

    raw = "Final assessment: 65 out of 100. Significant improvements required."
    result = _parse_verdict(raw)

    assert result["score"] == 65, f"Expected score=65, got {result['score']}"


def test_verdict_parser_returns_zero_score_when_no_numeric_score_present():
    """_parse_verdict must default to score=0 when no parseable score appears."""
    from src.orchestration.response_synthesizer import _parse_verdict

    raw = "The result is ambiguous. The product has strengths and weaknesses."
    result = _parse_verdict(raw)

    assert result["score"] == 0, f"Expected score=0 for unparseable input, got {result['score']}"


def test_verdict_parser_extracts_yes_buy_decision():
    """_parse_verdict must recognize an explicit YES buy decision."""
    from src.orchestration.response_synthesizer import _parse_verdict

    raw = "BUY DECISION: YES. This product is ready for team adoption. Score: 82/100."
    result = _parse_verdict(raw)

    assert result["decision"] == "YES", f"Expected decision=YES, got {result['decision']}"


def test_verdict_parser_extracts_no_buy_decision():
    """_parse_verdict must recognize an explicit NO buy decision."""
    from src.orchestration.response_synthesizer import _parse_verdict

    raw = "BUY DECISION: NO. The failure rate is unacceptable. Score: 38/100."
    result = _parse_verdict(raw)

    assert result["decision"] == "NO", f"Expected decision=NO, got {result['decision']}"


def test_verdict_parser_prefers_yes_with_conditions_over_plain_yes():
    """_parse_verdict must select 'YES WITH CONDITIONS' when both YES and conditions appear."""
    from src.orchestration.response_synthesizer import _parse_verdict

    raw = "BUY DECISION: YES WITH CONDITIONS. Fix the mobile app first. Score: 61/100."
    result = _parse_verdict(raw)

    assert result["decision"] == "YES WITH CONDITIONS", (
        f"Parser must prefer 'YES WITH CONDITIONS' over 'YES', got: {result['decision']}"
    )


def test_verdict_parser_defaults_to_unknown_when_no_decision_keyword_present():
    """_parse_verdict must return 'UNKNOWN' when no YES/NO keyword is found."""
    from src.orchestration.response_synthesizer import _parse_verdict

    # Carefully constructed to avoid 'NO' as substring (e.g. 'not', 'know', 'nobody')
    raw = "The result is ambiguous. Score: 55/100. Further evaluation required."
    result = _parse_verdict(raw)

    assert result["decision"] == "UNKNOWN", (
        f"Expected decision=UNKNOWN for ambiguous input, got {result['decision']}"
    )


def test_verdict_parser_extracts_top_3_fixes_from_newline_separated_numbered_list():
    """_parse_verdict must extract 3 fix items from a properly formatted TOP 3 FIXES section."""
    from src.orchestration.response_synthesizer import _parse_verdict

    raw = (
        "BUY DECISION: YES WITH CONDITIONS. Score: 68/100.\n\n"
        "TOP 3 FIXES:\n"
        "1. Redesign the onboarding flow — first-timer confusion drives 40% week-1 churn.\n"
        "2. Fix mobile push spam — power users disable all alerts within 2 weeks.\n"
        "3. Add CSV data export — vendor lock-in concern blocks enterprise procurement.\n\n"
        "Competitive positioning: strong vs Asana on price, weak vs Linear on developer UX."
    )
    result = _parse_verdict(raw)

    assert len(result["top_3_fixes"]) == 3, (
        f"Expected 3 fixes, got {len(result['top_3_fixes'])}: {result['top_3_fixes']}"
    )
    assert any("onboarding" in fix.lower() for fix in result["top_3_fixes"]), (
        "Fix 1 (onboarding) must appear in top_3_fixes"
    )


def test_verdict_parser_returns_fallback_fix_when_no_top_3_section_present():
    """_parse_verdict must return a non-empty fallback fix list when TOP 3 FIXES is absent."""
    from src.orchestration.response_synthesizer import _parse_verdict

    raw = "BUY DECISION: YES. Score: 75/100. The product is solid overall."
    result = _parse_verdict(raw)

    assert len(result["top_3_fixes"]) >= 1, "top_3_fixes must never be empty"
    assert result["top_3_fixes"][0] != "", "Fallback fix message must be non-empty"


def test_verdict_parser_always_preserves_full_raw_output_in_full_report():
    """_parse_verdict must store the complete Round 4 text in 'full_report' unchanged."""
    from src.orchestration.response_synthesizer import _parse_verdict

    raw = "BUY DECISION: YES. Score: 80/100.\n\nTOP 3 FIXES:\n1. Fix search.\n2. Improve onboarding.\n3. Add SSO."
    result = _parse_verdict(raw)

    assert result["full_report"] == raw, (
        "full_report must be the exact raw Round 4 output with no truncation"
    )


def test_verdict_result_dict_contains_all_four_required_keys():
    """_parse_verdict must always return all four required keys regardless of input quality."""
    from src.orchestration.response_synthesizer import _parse_verdict

    result = _parse_verdict("Anything at all.")

    assert "score" in result, "Verdict must include 'score'"
    assert "decision" in result, "Verdict must include 'decision'"
    assert "top_3_fixes" in result, "Verdict must include 'top_3_fixes'"
    assert "full_report" in result, "Verdict must include 'full_report'"


def test_verdict_score_is_always_an_integer():
    """_parse_verdict score must always be an int (never a string or None)."""
    from src.orchestration.response_synthesizer import _parse_verdict

    for raw in [
        "Score: 90/100. YES.",
        "No score present.",
        "",
    ]:
        result = _parse_verdict(raw)
        assert isinstance(result["score"], int), (
            f"score must be int, got {type(result['score'])} for input: {raw!r}"
        )


def test_verdict_top_3_fixes_is_always_a_list():
    """_parse_verdict top_3_fixes must always be a list (never None or a string)."""
    from src.orchestration.response_synthesizer import _parse_verdict

    for raw in ["YES. Score: 70/100. TOP 3 FIXES:\n1. A\n2. B\n3. C", "Nothing."]:
        result = _parse_verdict(raw)
        assert isinstance(result["top_3_fixes"], list), (
            f"top_3_fixes must be list, got {type(result['top_3_fixes'])}"
        )


# ---------------------------------------------------------------------------
# Round 4 synthesis task structure — verify the crew is wired for synthesis
# ---------------------------------------------------------------------------


@pytest.fixture
def crew_for_synthesis():
    """Return a built Crew with mocked deps for Round 4 structural inspection."""
    mock_personas = [
        {"role": "First-Timer", "goal": "Find problems", "backstory": "New user."},
        {"role": "Daily Driver", "goal": "Expose issues", "backstory": "Power user."},
        {"role": "Buyer", "goal": "Final verdict", "backstory": "CTO."},
    ]
    mock_swarm = {
        "briefing": "# Swarm Briefing\nMock intelligence.",
        "stats": {
            "scouts_deployed": 20,
            "scouts_successful": 18,
            "total_time": 1.0,
            "product": "TestProduct",
        },
    }
    with (
        patch("src.orchestration.adversarial_debate_engine.generate_personas", return_value=mock_personas),
        patch("src.orchestration.adversarial_debate_engine.deploy_swarm", return_value=mock_swarm),
        patch("src.orchestration.adversarial_debate_engine.fetch_context_for_product", return_value="[mock RAG evidence]"),
    ):
        from src.orchestration.adversarial_debate_engine import build_crew

        return build_crew("TestProduct — a project management tool")


def test_synthesis_incorporates_all_three_prior_model_outputs_via_context(
    crew_for_synthesis,
):
    """Round 4 synthesis must receive outputs from all 3 prior rounds as context."""
    round4 = crew_for_synthesis.tasks[3]

    assert round4.context is not None, "Round 4 synthesis must have context configured"
    assert len(round4.context) == 3, (
        f"Synthesis must receive all 3 prior round outputs as context, "
        f"got {len(round4.context)}"
    )


def test_synthesis_identifies_disagreements_via_buyer_adjudication_mandate(
    crew_for_synthesis,
):
    """Round 4 task description must instruct the Buyer to settle R1/R2 disagreements."""
    round4_description = crew_for_synthesis.tasks[3].description.lower()

    assert any(kw in round4_description for kw in ["disagree", "settle", "debate"]), (
        "Round 4 must explicitly instruct the Buyer to adjudicate disagreements between agents"
    )


def test_synthesis_produces_actionable_conclusion_with_explicit_buy_decision(
    crew_for_synthesis,
):
    """Round 4 expected_output must require an explicit buy decision, not a balanced review."""
    round4_expected = crew_for_synthesis.tasks[3].expected_output.upper()

    assert any(kw in round4_expected for kw in ["YES", "NO", "DECISION"]), (
        "Round 4 must require an explicit YES/NO/CONDITIONS decision — no hedging allowed"
    )


def test_synthesis_task_requires_competitive_positioning_output(crew_for_synthesis):
    """Round 4 verdict must include competitive positioning relative to alternatives."""
    round4_expected = crew_for_synthesis.tasks[3].expected_output.lower()

    assert "competi" in round4_expected, (
        "Synthesis verdict must include competitive positioning analysis"
    )


def test_synthesis_task_mandates_prioritized_fix_recommendations(crew_for_synthesis):
    """Round 4 expected output must require prioritized, actionable fix recommendations."""
    round4_expected = crew_for_synthesis.tasks[3].expected_output.lower()

    assert "fix" in round4_expected or "priorit" in round4_expected, (
        "Round 4 must produce actionable, prioritized fix recommendations"
    )


def test_synthesis_task_requires_evidence_backed_score(crew_for_synthesis):
    """Round 4 verdict must include a numerically scored assessment, not just a text opinion."""
    round4_expected = crew_for_synthesis.tasks[3].expected_output

    assert "1-100" in round4_expected or "100" in round4_expected, (
        "Round 4 must require a 1-100 numeric score defensible with evidence"
    )


def test_synthesis_is_performed_by_buyer_agent_not_first_timer_or_daily_driver(
    crew_for_synthesis,
):
    """Round 4 synthesis must be assigned to the Buyer agent, not the analysts."""
    buyer_agent = crew_for_synthesis.agents[2]
    round4_agent = crew_for_synthesis.tasks[3].agent

    assert round4_agent is buyer_agent, (
        "Only the Buyer agent (Mistral-Small 24B on DGX) should produce the final synthesis"
    )


# ---------------------------------------------------------------------------
# DebateSession WebSocket streaming — real-time round delivery
# ---------------------------------------------------------------------------


def test_debate_session_callback_emits_round_message_with_required_fields():
    """build_task_callback must enqueue a message with round, agent_name, content, status."""
    from src.api.server import DebateSession

    loop = asyncio.new_event_loop()
    try:
        session = DebateSession(
            session_id="test-uuid-synthesis-1",
            product_description="TestProduct",
            loop=loop,
        )
        callback = session.build_task_callback()

        mock_output = MagicMock()
        mock_output.agent = "First-Timer Skeptic"
        mock_output.raw = "Round 1 analysis: onboarding fails at step 2."

        callback(mock_output)

        message = loop.run_until_complete(session.queue.get())

        assert message["round"] == 1, f"First callback must produce round=1, got {message['round']}"
        assert message["agent_name"] == "First-Timer Skeptic"
        assert message["content"] == "Round 1 analysis: onboarding fails at step 2."
        assert message["status"] == "complete"
    finally:
        loop.close()


def test_debate_session_callback_increments_round_index_on_each_invocation():
    """Each successive task_callback call must increment the round number by 1."""
    from src.api.server import DebateSession

    loop = asyncio.new_event_loop()
    try:
        session = DebateSession(
            session_id="test-uuid-synthesis-2",
            product_description="TestProduct",
            loop=loop,
        )
        callback = session.build_task_callback()

        for i in range(4):
            mock_output = MagicMock()
            mock_output.agent = f"Agent {i}"
            mock_output.raw = f"Output for round {i + 1}."
            callback(mock_output)

        rounds = []
        for _ in range(4):
            msg = loop.run_until_complete(session.queue.get())
            rounds.append(msg["round"])

        assert rounds == [1, 2, 3, 4], (
            f"Round numbers must increment as 1, 2, 3, 4 — got {rounds}"
        )
    finally:
        loop.close()


def test_debate_session_initializes_with_empty_queue_and_zero_round_index():
    """A fresh DebateSession must start with an empty queue and round index of 0."""
    from src.api.server import DebateSession

    loop = asyncio.new_event_loop()
    try:
        session = DebateSession(
            session_id="test-uuid-synthesis-3",
            product_description="TestProduct",
            loop=loop,
        )

        assert session.queue.empty(), "Queue must be empty before debate begins"
        assert session._round_index == 0, "Round index must start at 0"
    finally:
        loop.close()


def test_debate_session_stores_product_description_and_session_id():
    """DebateSession must preserve session_id and product_description for downstream use."""
    from src.api.server import DebateSession

    loop = asyncio.new_event_loop()
    try:
        session = DebateSession(
            session_id="abc-123",
            product_description="Notion — workspace for teams",
            loop=loop,
        )

        assert session.session_id == "abc-123"
        assert session.product_description == "Notion — workspace for teams"
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Live synthesis tests — require DGX Spark hardware
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason="Requires DGX Spark with Llama 3.3 70B, Qwen3 32B, and Mistral-Small 24B loaded via vLLM"
)
def test_live_synthesis_incorporates_all_model_outputs_and_produces_verdict():
    """Full live debate must produce a Round 4 verdict referencing all prior model outputs."""
    pass


@pytest.mark.skip(
    reason="Requires DGX Spark with Llama 3.3 70B, Qwen3 32B, and Mistral-Small 24B loaded via vLLM"
)
def test_live_synthesis_identifies_and_adjudicates_real_disagreements():
    """When models disagree on evidence, Round 4 Buyer must explicitly resolve the dispute."""
    pass


@pytest.mark.skip(
    reason="Requires DGX Spark with Llama 3.3 70B, Qwen3 32B, and Mistral-Small 24B loaded via vLLM"
)
def test_live_synthesis_produces_parseable_score_and_decision_in_structured_output():
    """Live Round 4 output must yield a parseable score and YES/NO/CONDITIONS via _parse_verdict."""
    pass
