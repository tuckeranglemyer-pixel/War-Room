"""
Lightweight tests that avoid importing CrewAI. See ``tests/`` for integration tests.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def _load_model_config():
    """Load ``src/inference/model_config.py`` without requiring ``src`` to be a package."""
    path = REPO_ROOT / "src" / "inference" / "model_config.py"
    spec = importlib.util.spec_from_file_location("war_room_model_config", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_config_exposes_expected_types() -> None:
    """Model config loads with stdlib + optional dotenv only."""
    mod = _load_model_config()
    assert isinstance(mod.LOCAL_MODEL, str) and len(mod.LOCAL_MODEL) > 0
    assert mod.COLLECTION_NAME == "pm_tools"
    assert isinstance(mod.RAG_RESULTS_PER_QUERY, int) and mod.RAG_RESULTS_PER_QUERY > 0


def test_crew_py_defines_build_crew() -> None:
    """Orchestration entrypoint exists at ``src/orchestration/`` (no CrewAI import)."""
    orchestration = REPO_ROOT / "src" / "orchestration"
    engine = orchestration / "adversarial_debate_engine.py"
    text = engine.read_text(encoding="utf-8")
    assert "def build_crew(" in text


def test_env_example_lists_config_keys() -> None:
    """``.env.example`` documents overridable settings."""
    raw = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "LOCAL_MODEL" in raw
    assert "API_PORT" in raw
    assert "CHROMA_DB_PATH" in raw
