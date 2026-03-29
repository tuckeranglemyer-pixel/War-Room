"""
Hardware Pre-flight Check — GO/NO-GO verdict before running any analysis.

Wraps the detailed DGX Spark diagnostic from src.inference.dgx_preflight_check
into a JSON-serializable dict suitable for API responses. The detailed CLI
diagnostic (with human-readable output) is still available via:

    python -m src.inference.dgx_preflight_check

This module is designed to be called from the FastAPI /api/preflight endpoint
and by AdaptiveRunner before starting an analysis session.

Verdict logic:
  GO       — All checks pass; Tier 2 (Sequential) recommended.
  CAUTION  — Warnings present but no blockers; Tier 3 (Micro) recommended.
  NO-GO    — Blocking issues; do not start inference.

Usage:
    python -m src.orchestration.hardware_preflight
"""

from __future__ import annotations

import json
from typing import Any

from src.orchestration.adaptive_runner import (
    THERMAL_CEILING,
    THERMAL_RESUME,
    HardwareMonitor,
)


def preflight_check() -> dict[str, Any]:
    """Run all hardware checks and return a structured GO/NO-GO verdict.

    Returns:
        Dict with keys: verdict, tier_recommendation, issues, warnings,
        recommendations, and health (raw telemetry snapshot).
    """
    monitor = HardwareMonitor()
    health = monitor.full_health_check()

    issues: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    # --- GPU temperature ---
    temp = health["gpu_temp"]
    if temp == -1:
        warnings.append("GPU temperature unreadable — nvidia-smi unavailable or no NVIDIA GPU")
        recommendations.append("Verify nvidia-smi is installed and GPU is detected")
    elif temp >= THERMAL_CEILING:
        issues.append(f"GPU temperature {temp}°C exceeds safe ceiling ({THERMAL_CEILING}°C)")
        recommendations.append(
            f"Wait for GPU to cool below {THERMAL_RESUME}°C before starting analysis. "
            f"Monitor with: nvidia-smi -l 2"
        )
    elif temp >= THERMAL_RESUME:
        warnings.append(f"GPU temperature {temp}°C is warm (target below {THERMAL_RESUME}°C)")
        recommendations.append("Consider waiting 5-10 minutes before starting for optimal safety")

    # --- GPU memory ---
    gpu_mem = health["gpu_memory"]
    if gpu_mem["free_mib"] != -1 and gpu_mem["free_mib"] < 20_000:
        issues.append(
            f"GPU memory critically low: {gpu_mem['free_mib']:,} MiB free "
            f"(need ~20,000 MiB for qwen3:32b)"
        )
        recommendations.append("Unload all models: run `ollama ps` then `ollama stop <model>` for each")

    # --- System RAM ---
    ram = health["ram"]
    if ram["percent"] != -1:
        if ram["percent"] >= 80:
            issues.append(f"System RAM at {ram['percent']}% — critically high")
            recommendations.append("Unload all Ollama models and restart any memory-intensive processes")
        elif ram["percent"] >= 60:
            warnings.append(f"System RAM at {ram['percent']}% — elevated (Tier 3 recommended)")

    # --- Loaded models ---
    loaded = health["loaded_models"]
    if len(loaded) > 1:
        issues.append(
            f"{len(loaded)} models currently loaded in VRAM simultaneously — "
            "this is the root cause of DGX power-loss crashes"
        )
        for model in loaded:
            recommendations.append(f"Run: ollama stop {model}")
    elif len(loaded) == 1:
        warnings.append(
            f"Model {loaded[0]} is still loaded — AdaptiveRunner will unload it before starting, "
            "but pre-clearing saves 5-10s of startup time"
        )

    # --- Determine verdict and tier recommendation ---
    if issues:
        verdict = "NO-GO"
        tier_recommendation = 3
    elif warnings:
        verdict = "CAUTION"
        tier_recommendation = 3
    else:
        verdict = "GO"
        tier_recommendation = 2

    return {
        "verdict": verdict,
        "tier_recommendation": tier_recommendation,
        "issues": issues,
        "warnings": warnings,
        "recommendations": recommendations,
        "health": health,
        "thermal_thresholds": {
            "ceiling_c": THERMAL_CEILING,
            "resume_c": THERMAL_RESUME,
        },
    }


if __name__ == "__main__":
    result = preflight_check()
    print(json.dumps(result, indent=2))
    print(f"\nVerdict: {result['verdict']} — Tier {result['tier_recommendation']} recommended")
    if result["issues"]:
        print("\nBlocking issues:")
        for issue in result["issues"]:
            print(f"  - {issue}")
    if result["recommendations"]:
        print("\nRecommended actions:")
        for rec in result["recommendations"]:
            print(f"  -> {rec}")
