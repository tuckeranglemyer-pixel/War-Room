"""
vLLM / Ollama multi-model dispatch and DGX Spark thermal management.

Responsibilities:
  - ROUND_MODELS: maps debate roles to Ollama model tags
  - Hardware telemetry: GPU temp, GPU memory, CPU temp, RAM
  - Thermal gate: blocks until GPU cools below a safe threshold
  - Model lifecycle: load one model into VRAM, unload it after the round

Used by thermal_safe_debate_runner.py to run one model at a time and
prevent cumulative memory pressure from crashing the DGX Spark mid-debate.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Any, Optional

import psutil

log = logging.getLogger("vllm_dispatch")


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Thermal safety thresholds (tunable via env)
# ---------------------------------------------------------------------------

THERMAL_CEILING_C = _env_int("SAFE_THERMAL_CEILING", 75)
THERMAL_RESUME_C = _env_int("SAFE_THERMAL_RESUME", 65)
COOLDOWN_BETWEEN_ROUNDS_S = _env_int("SAFE_COOLDOWN_S", 30)
PRE_ROUND_PAUSE_S = _env_int("SAFE_PRE_ROUND_PAUSE_S", 15)
SAFE_SWARM_WORKERS = _env_int("SAFE_SWARM_WORKERS", 3)
SAFE_SWARM_SCOUTS = _env_int("SAFE_SWARM_SCOUTS", 10)
SAFE_MAX_ITER = _env_int("SAFE_MAX_ITER", 4)
SAFE_EVIDENCE_MAX_CHARS = _env_int("SAFE_EVIDENCE_MAX_CHARS", 12_000)
SKIP_SWARM = _env_bool("SAFE_SKIP_SWARM")

# ---------------------------------------------------------------------------
# DGX Spark model-to-role assignments (overridable via env)
# ---------------------------------------------------------------------------

ROUND_MODELS: dict[str, str] = {
    "first_timer": os.environ.get("FIRST_TIMER_MODEL", "llama3.1:8b"),
    "daily_driver": os.environ.get("DAILY_DRIVER_MODEL", "llama3.3:70b"),
    "buyer": os.environ.get("BUYER_MODEL", "mistral-small:24b"),
}

MODEL_SIZES_GB = {
    "llama3.3:70b": 42,
    "qwen3:32b": 20,
    "mistral-small:24b": 14,
    "llama3.1:8b": 5,
    "llama3.3:60b": 36,
}


# ---------------------------------------------------------------------------
# Hardware telemetry
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
    """Return CPU temperature if available via psutil sensors."""
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

    log.warning(
        "GPU at %s°C — exceeds %s°C ceiling. Pausing until <%s°C...",
        temp, THERMAL_CEILING_C, THERMAL_RESUME_C,
    )
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
# Ollama model lifecycle — load one model at a time
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
    """Stop every model Ollama currently has loaded in VRAM (uses `ollama ps`)."""
    try:
        out = subprocess.check_output(["ollama", "ps"], text=True, timeout=10)
        lines = [ln for ln in out.strip().split("\n")[1:] if ln.strip()]
        if not lines:
            log.info("ollama ps: no models loaded")
            return
        for line in lines:
            parts = line.split()
            if parts:
                ollama_stop_model(parts[0])
    except Exception as exc:
        log.warning("Could not stop running Ollama models: %s", exc)
