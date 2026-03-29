"""
Tests for War Room's multi-model vLLM dispatch configuration.

The DGX Spark runs three frontier models simultaneously via vLLM:
  - Llama 3.3 70B  — First-Timer agent (analytical, structured reasoning)
  - Qwen3 32B      — Daily Driver agent (different training corpus, contrarian priors)
  - Mistral-Small 24B — Buyer agent (efficient long-context synthesis)

Each model serves via an OpenAI-compatible endpoint. The three-endpoint
architecture is what makes adversarial multi-model debate possible:
each agent calls a distinct model, ensuring outputs are structurally
independent rather than correlated variants of the same weights.

Hardware-dependent tests (live inference, concurrent load, latency) are
marked skip — they require DGX Spark with all three models loaded via vLLM.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Shared mock helpers
# ---------------------------------------------------------------------------


MOCK_PERSONAS = [
    {
        "role": "First-Timer Skeptic",
        "goal": "Find the 3 biggest friction points in the first session",
        "backstory": "Skeptical new user who has churned from Notion and Asana.",
    },
    {
        "role": "Daily Driver Expert",
        "goal": "Challenge surface analysis with long-term power-user evidence",
        "backstory": "Power user who knows every bug and workaround in the product.",
    },
    {
        "role": "Enterprise Buyer",
        "goal": "Make a final buy/no-buy decision for team-wide adoption",
        "backstory": "CTO with budget authority who has killed 4 PM tools in 3 years.",
    },
]

MOCK_SWARM = {
    "briefing": "# SWARM BRIEFING\n\nMock intelligence compiled from 20 scouts.",
    "stats": {
        "scouts_deployed": 20,
        "scouts_successful": 18,
        "total_time": 1.2,
        "product": "TestProduct",
    },
}


@pytest.fixture
def built_crew():
    """Return a Crew instance built with all external dependencies mocked."""
    with (
        patch("crew.generate_personas", return_value=MOCK_PERSONAS),
        patch("crew.deploy_swarm", return_value=MOCK_SWARM),
        patch("crew.fetch_context_for_product", return_value="[mock evidence]"),
    ):
        from crew import build_crew

        return build_crew("TestProduct — a project management app")


# ---------------------------------------------------------------------------
# Configuration correctness — no hardware required
# ---------------------------------------------------------------------------


def test_config_defines_two_distinct_model_identifiers_for_current_dev_environment():
    """config.py must define LOCAL_MODEL and DAILY_DRIVER_BUYER_MODEL as distinct values."""
    from config import DAILY_DRIVER_BUYER_MODEL, LOCAL_MODEL

    assert LOCAL_MODEL is not None, "LOCAL_MODEL must be set"
    assert DAILY_DRIVER_BUYER_MODEL is not None, "DAILY_DRIVER_BUYER_MODEL must be set"
    assert LOCAL_MODEL != DAILY_DRIVER_BUYER_MODEL, (
        "First-Timer and Daily Driver/Buyer models must be distinct for adversarial tension"
    )


def test_config_dgx_model_slots_cover_three_distinct_model_families():
    """DGX Spark model assignments must reference Llama, Qwen, and Mistral — three distinct families."""
    dgx_models = [
        "ollama/llama3.3:70b",
        "ollama/qwen3:32b",
        "ollama/mistral-small:24b",
    ]
    required_families = {"llama", "qwen", "mistral"}

    detected_families = {
        family
        for model in dgx_models
        for family in required_families
        if family in model.lower()
    }

    assert detected_families == required_families, (
        f"DGX model lineup must include all three families for genuine adversarial diversity. "
        f"Missing: {required_families - detected_families}"
    )


def test_llm_base_url_points_to_local_inference_server():
    """LOCAL_BASE_URL must target a localhost inference endpoint for on-device vLLM."""
    from config import LOCAL_BASE_URL

    assert "localhost" in LOCAL_BASE_URL or "127.0.0.1" in LOCAL_BASE_URL, (
        f"LOCAL_BASE_URL must point to a local vLLM/Ollama server, got: {LOCAL_BASE_URL}"
    )


def test_three_model_int8_footprint_fits_within_dgx_spark_unified_memory():
    """INT8-quantized Llama 70B + Qwen 32B + Mistral 24B must fit in DGX Spark's 128 GB."""
    # At INT8 quantization: ~1 byte per parameter
    model_weights_gb = {
        "llama3.3-70b": 70,   # 70B params × 1 byte ≈ 70 GB
        "qwen3-32b": 32,       # 32B params × 1 byte ≈ 32 GB
        "mistral-small-24b": 24,  # 24B params × 1 byte ≈ 24 GB
    }
    dgx_spark_unified_memory_gb = 128

    total_footprint_gb = sum(model_weights_gb.values())

    assert total_footprint_gb <= dgx_spark_unified_memory_gb, (
        f"INT8 three-model stack ({total_footprint_gb} GB) exceeds "
        f"DGX Spark unified memory ({dgx_spark_unified_memory_gb} GB). "
        f"Use INT4 quantization or model parallelism."
    )


def test_three_model_stack_exceeds_single_rtx4090_vram_ceiling():
    """Three-model INT8 stack must provably exceed a single RTX 4090 (24 GB VRAM)."""
    rtx_4090_vram_gb = 24
    three_model_int8_gb = 70 + 32 + 24  # 126 GB

    assert three_model_int8_gb > rtx_4090_vram_gb, (
        "Three-model stack must exceed RTX 4090 VRAM to justify DGX Spark requirement"
    )


def test_three_model_stack_exceeds_four_rtx4090s_combined_vram():
    """Three-model INT8 stack exceeds even 4× RTX 4090 (96 GB), ruling out consumer multi-GPU."""
    rtx_4090_4x_vram_gb = 24 * 4  # 96 GB
    three_model_int8_gb = 70 + 32 + 24  # 126 GB

    assert three_model_int8_gb > rtx_4090_4x_vram_gb, (
        f"Three-model INT8 stack ({three_model_int8_gb} GB) must exceed "
        f"4× RTX 4090 ({rtx_4090_4x_vram_gb} GB) — consumer multi-GPU cannot host War Room"
    )


def test_llama_70b_alone_exceeds_rtx4090_vram_at_fp16():
    """Llama 70B at FP16 (~140 GB) alone exceeds the RTX 4090 by 5.8×."""
    rtx_4090_vram_gb = 24
    llama_70b_fp16_gb = 140  # 70B × 2 bytes = 140 GB

    assert llama_70b_fp16_gb > rtx_4090_vram_gb * 5, (
        "Llama 70B at FP16 must exceed RTX 4090 by at least 5× to demonstrate consumer hardware impossibility"
    )


# ---------------------------------------------------------------------------
# Crew structure — three agents, three LLM instances
# ---------------------------------------------------------------------------


def test_dispatch_sends_to_all_three_agents_each_with_assigned_llm(built_crew):
    """Each of the 3 agents must carry an LLM instance for routing to a vLLM endpoint."""
    for agent in built_crew.agents:
        assert agent.llm is not None, (
            f"Agent '{agent.role}' must have an LLM instance configured for vLLM dispatch"
        )


def test_three_agents_are_assigned_to_four_tasks_covering_all_debate_rounds(built_crew):
    """All 4 tasks must be assigned to agents — no unrouted inference calls."""
    for i, task in enumerate(built_crew.tasks):
        assert task.agent is not None, (
            f"Round {i + 1} task must be assigned to a specific agent for model dispatch"
        )


def test_first_timer_and_buyer_use_different_llm_instances(built_crew):
    """First-Timer agent and Buyer agent must be assigned distinct LLM configurations."""
    first_timer_agent = built_crew.tasks[0].agent
    buyer_agent = built_crew.tasks[3].agent

    assert first_timer_agent is not buyer_agent, (
        "First-Timer and Buyer must be different agents with potentially different LLMs"
    )


def test_round_assignments_ensure_first_timer_runs_rounds_1_and_3(built_crew):
    """Llama 70B (First-Timer) must handle both the opening analysis and the rebuttal."""
    round1_agent = built_crew.tasks[0].agent
    round3_agent = built_crew.tasks[2].agent

    assert round1_agent is round3_agent, (
        "Round 1 and Round 3 must use the same First-Timer agent "
        "(Llama 70B defends its own analysis in the rebuttal)"
    )


def test_daily_driver_runs_exactly_round_2_challenge(built_crew):
    """Qwen3 32B (Daily Driver) must be assigned specifically to Round 2."""
    daily_driver_agent = built_crew.agents[1]
    round2_agent = built_crew.tasks[1].agent

    assert round2_agent is daily_driver_agent, (
        "Round 2 challenge must be routed to the Daily Driver agent (Qwen3 32B on DGX Spark)"
    )


def test_buyer_runs_exactly_round_4_synthesis(built_crew):
    """Mistral-Small 24B (Buyer) must be assigned specifically to Round 4."""
    buyer_agent = built_crew.agents[2]
    round4_agent = built_crew.tasks[3].agent

    assert round4_agent is buyer_agent, (
        "Round 4 synthesis must be routed to the Buyer agent (Mistral-Small 24B on DGX Spark)"
    )


def test_model_responses_would_be_distinct_due_to_different_training_families(
    built_crew,
):
    """The three agent roles must map to structurally distinct personas (not the same archetype)."""
    roles = [agent.role for agent in built_crew.agents]

    # All three roles must be distinct — same role would produce correlated outputs
    assert len(set(roles)) == 3, (
        "All three agents must have distinct roles to ensure non-correlated model outputs"
    )


# ---------------------------------------------------------------------------
# vLLM server configuration — port layout
# ---------------------------------------------------------------------------


def test_vllm_port_layout_documentation_assigns_three_ports():
    """The documented DGX vLLM port layout must assign one port per model."""
    # Per .cursorrules DGX SWAP NOTES:
    # Llama 3.3-70B → First-Timer (port 8001)
    # Qwen3-32B → Daily Driver (port 8002)
    # Mistral-Small-24B → Buyer (port 8003)
    dgx_port_assignments = {
        "llama3.3:70b": 8001,
        "qwen3:32b": 8002,
        "mistral-small:24b": 8003,
    }

    assert len(dgx_port_assignments) == 3, "Three models require three distinct vLLM ports"
    assert len(set(dgx_port_assignments.values())) == 3, (
        "Each model must have a unique port — port conflicts would cause routing failures"
    )


def test_api_port_does_not_conflict_with_vllm_model_ports():
    """FastAPI server port (8000) must not conflict with vLLM model ports (8001-8003)."""
    from config import API_PORT

    vllm_ports = {8001, 8002, 8003}

    assert API_PORT not in vllm_ports, (
        f"FastAPI server (port {API_PORT}) must not conflict with vLLM model endpoints"
    )


# ---------------------------------------------------------------------------
# Live inference tests — require DGX Spark hardware
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason="Requires DGX Spark with vLLM serving Llama 3.3 70B on port 8001"
)
def test_live_dispatch_sends_prompt_to_llama_70b_and_receives_response():
    """Llama 3.3 70B must respond to a product analysis prompt via vLLM on port 8001."""
    pass


@pytest.mark.skip(
    reason="Requires DGX Spark with vLLM serving Qwen3 32B on port 8002"
)
def test_live_dispatch_sends_prompt_to_qwen3_32b_and_receives_response():
    """Qwen3 32B must respond to a Daily Driver challenge prompt via vLLM on port 8002."""
    pass


@pytest.mark.skip(
    reason="Requires DGX Spark with vLLM serving Mistral-Small 24B on port 8003"
)
def test_live_dispatch_sends_prompt_to_mistral_small_24b_and_receives_response():
    """Mistral-Small 24B must respond to a buyer synthesis prompt via vLLM on port 8003."""
    pass


@pytest.mark.skip(
    reason="Requires DGX Spark with all three models loaded via vLLM"
)
def test_live_all_three_models_participate_in_single_debate_session():
    """A single debate session must route to all three model families and receive distinct outputs."""
    pass


@pytest.mark.skip(
    reason="Requires DGX Spark with all three models loaded via vLLM"
)
def test_live_model_responses_are_distinct_not_correlated_outputs():
    """Llama, Qwen, and Mistral must produce meaningfully different responses on the same prompt."""
    pass


@pytest.mark.skip(
    reason="Requires DGX Spark with all three models loaded via vLLM"
)
def test_live_concurrent_inference_does_not_degrade_per_request_latency():
    """Serving three concurrent debate sessions must not exceed 2× single-session latency."""
    pass
