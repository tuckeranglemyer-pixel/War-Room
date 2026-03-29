"""
DGX Spark pre-flight health checker.

Run before launching the debate to verify system readiness:
  - GPU temperature and free VRAM
  - CPU temperature and usage
  - RAM headroom
  - Disk space
  - Ollama model availability and currently loaded models

Prints a GO / NO-GO recommendation. If NO-GO, lists specific actions.

Usage:
    python -m src.inference.dgx_preflight_check
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

import psutil

GPU_TEMP_MAX_C = 70
GPU_TEMP_WARN_C = 60
GPU_MEM_MIN_FREE_MIB = 40_000
RAM_MAX_PCT = 80
DISK_MAX_PCT = 90

EXPECTED_MODELS = [
    "llama3.1:8b",
    "llama3.3:70b",
    "qwen3:32b",
    "mistral-small:24b",
]

MODEL_SIZES_GB = {
    "llama3.3:70b": 42,
    "qwen3:32b": 20,
    "mistral-small:24b": 14,
    "llama3.1:8b": 5,
    "llama3.3:60b": 36,
}


def section(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def ok(msg: str) -> str:
    return f"  ✅ {msg}"


def warn(msg: str) -> str:
    return f"  ⚠️  {msg}"


def fail(msg: str) -> str:
    return f"  ❌ {msg}"


# ---------------------------------------------------------------------------
# GPU
# ---------------------------------------------------------------------------


def check_gpu() -> dict[str, Any]:
    """Query nvidia-smi for temperature, memory, and power draw."""
    result: dict[str, Any] = {
        "available": False,
        "temp_c": None,
        "mem_used_mib": None,
        "mem_total_mib": None,
        "mem_free_mib": None,
        "gpu_name": None,
        "power_w": None,
        "issues": [],
    }

    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,temperature.gpu,memory.used,memory.total,memory.free,power.draw",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=10,
        )
        parts = [p.strip() for p in out.strip().split(",")]
        result["available"] = True
        result["gpu_name"] = parts[0]
        result["temp_c"] = float(parts[1])
        result["mem_used_mib"] = int(parts[2])
        result["mem_total_mib"] = int(parts[3])
        result["mem_free_mib"] = int(parts[4])
        try:
            result["power_w"] = float(parts[5])
        except (ValueError, IndexError):
            pass
    except FileNotFoundError:
        result["issues"].append("nvidia-smi not found — no NVIDIA GPU detected")
    except Exception as exc:
        result["issues"].append(f"nvidia-smi error: {exc}")

    return result


def print_gpu(gpu: dict[str, Any]) -> list[str]:
    """Print GPU status and return a list of blocking issues."""
    section("GPU STATUS")
    issues: list[str] = list(gpu["issues"])

    if not gpu["available"]:
        print(fail("No NVIDIA GPU detected"))
        return issues

    print(f"  GPU: {gpu['gpu_name']}")
    if gpu["power_w"] is not None:
        print(f"  Power draw: {gpu['power_w']:.0f} W")

    temp = gpu["temp_c"]
    if temp is not None:
        if temp >= GPU_TEMP_MAX_C:
            print(fail(f"Temperature: {temp}°C — TOO HOT (max {GPU_TEMP_MAX_C}°C)"))
            issues.append(f"GPU temp {temp}°C exceeds {GPU_TEMP_MAX_C}°C")
        elif temp >= GPU_TEMP_WARN_C:
            print(warn(f"Temperature: {temp}°C — warm (warn at {GPU_TEMP_WARN_C}°C)"))
        else:
            print(ok(f"Temperature: {temp}°C"))

    used = gpu["mem_used_mib"]
    total = gpu["mem_total_mib"]
    free = gpu["mem_free_mib"]
    if total and total > 0:
        print(f"  Memory: {used:,} / {total:,} MiB ({free:,} MiB free)")
        if free < GPU_MEM_MIN_FREE_MIB:
            print(fail(f"Free GPU memory {free:,} MiB < {GPU_MEM_MIN_FREE_MIB:,} MiB minimum"))
            issues.append(f"GPU memory too low: {free:,} MiB free")
        else:
            print(ok(f"GPU memory OK ({free:,} MiB free)"))

    return issues


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------


def check_cpu() -> dict[str, Any]:
    """Check CPU temperature and usage."""
    result: dict[str, Any] = {
        "temp_c": None,
        "usage_pct": psutil.cpu_percent(interval=1),
        "cores": psutil.cpu_count(),
    }
    try:
        temps = psutil.sensors_temperatures()
        for name in ("coretemp", "k10temp", "cpu_thermal", "acpitz", "thermal"):
            if name in temps and temps[name]:
                result["temp_c"] = temps[name][0].current
                break
    except Exception:
        pass
    return result


def print_cpu(cpu: dict[str, Any]) -> list[str]:
    """Print CPU status and return blocking issues."""
    section("CPU STATUS")
    issues: list[str] = []
    print(f"  Cores: {cpu['cores']}")
    print(f"  Usage: {cpu['usage_pct']}%")
    if cpu["temp_c"] is not None:
        temp = cpu["temp_c"]
        if temp > 90:
            print(fail(f"Temperature: {temp}°C — CRITICAL"))
            issues.append(f"CPU temp {temp}°C is critical")
        elif temp > 75:
            print(warn(f"Temperature: {temp}°C — elevated"))
        else:
            print(ok(f"Temperature: {temp}°C"))
    else:
        print(warn("Temperature: unavailable (sensors not supported on this OS)"))
    return issues


# ---------------------------------------------------------------------------
# RAM
# ---------------------------------------------------------------------------


def print_ram() -> list[str]:
    """Print RAM status and return blocking issues."""
    section("RAM STATUS")
    issues: list[str] = []
    ram = psutil.virtual_memory()
    total_gb = ram.total / (1024 ** 3)
    used_gb = ram.used / (1024 ** 3)
    avail_gb = ram.available / (1024 ** 3)
    print(f"  Total:     {total_gb:.1f} GB")
    print(f"  Used:      {used_gb:.1f} GB ({ram.percent}%)")
    print(f"  Available: {avail_gb:.1f} GB")
    if ram.percent > RAM_MAX_PCT:
        print(fail(f"RAM usage {ram.percent}% exceeds {RAM_MAX_PCT}% threshold"))
        issues.append(f"RAM at {ram.percent}%")
    else:
        print(ok(f"RAM usage {ram.percent}% — within limits"))
    return issues


# ---------------------------------------------------------------------------
# Disk
# ---------------------------------------------------------------------------


def print_disk() -> list[str]:
    """Print disk status and return blocking issues."""
    section("DISK STATUS")
    issues: list[str] = []
    disk = shutil.disk_usage("/")
    total_gb = disk.total / (1024 ** 3)
    used_gb = disk.used / (1024 ** 3)
    free_gb = disk.free / (1024 ** 3)
    pct = (disk.used / disk.total) * 100
    print(f"  Total: {total_gb:.1f} GB")
    print(f"  Used:  {used_gb:.1f} GB ({pct:.0f}%)")
    print(f"  Free:  {free_gb:.1f} GB")
    if pct > DISK_MAX_PCT:
        print(fail(f"Disk usage {pct:.0f}% exceeds {DISK_MAX_PCT}%"))
        issues.append(f"Disk at {pct:.0f}%")
    else:
        print(ok(f"Disk usage {pct:.0f}% — OK"))
    return issues


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------


def check_ollama() -> dict[str, Any]:
    """Check which Ollama models are available and currently loaded in VRAM."""
    result: dict[str, Any] = {
        "running": False,
        "available_models": [],
        "loaded_models": [],
        "issues": [],
    }
    try:
        subprocess.check_output(["ollama", "--version"], text=True, timeout=5)
        result["running"] = True
    except Exception:
        result["issues"].append("Ollama not found or not running")
        return result

    try:
        out = subprocess.check_output(["ollama", "list"], text=True, timeout=10)
        for line in out.strip().split("\n")[1:]:
            parts = line.split()
            if parts:
                result["available_models"].append(parts[0])
    except Exception as exc:
        result["issues"].append(f"Could not list models: {exc}")

    try:
        out = subprocess.check_output(["ollama", "ps"], text=True, timeout=10)
        for line in out.strip().split("\n")[1:]:
            parts = line.split()
            if parts:
                result["loaded_models"].append(parts[0])
    except Exception:
        pass

    return result


def print_ollama(ollama: dict[str, Any]) -> list[str]:
    """Print Ollama status and return blocking issues."""
    section("OLLAMA STATUS")
    issues: list[str] = list(ollama["issues"])

    if not ollama["running"]:
        print(fail("Ollama is not running"))
        return issues

    print(ok("Ollama is running"))
    print(f"  Available models: {len(ollama['available_models'])}")
    for m in ollama["available_models"]:
        size = MODEL_SIZES_GB.get(m, "?")
        print(f"    - {m} (~{size} GB)")

    if ollama["loaded_models"]:
        total_loaded_gb = sum(MODEL_SIZES_GB.get(m, 0) for m in ollama["loaded_models"])
        print(f"\n  Currently LOADED in VRAM ({total_loaded_gb} GB estimated):")
        for m in ollama["loaded_models"]:
            size = MODEL_SIZES_GB.get(m, "?")
            print(f"    - {m} (~{size} GB)")
        if len(ollama["loaded_models"]) > 1:
            print(warn(
                f"{len(ollama['loaded_models'])} models loaded simultaneously — "
                "run `ollama stop <model>` to free memory"
            ))
            issues.append(f"{len(ollama['loaded_models'])} models loaded in VRAM simultaneously")
    else:
        print(ok("No models currently loaded in VRAM"))

    missing = [m for m in EXPECTED_MODELS if m not in ollama["available_models"]]
    if missing:
        print(warn(f"Missing expected models: {', '.join(missing)}"))
    else:
        print(ok("All expected debate models available"))

    return issues


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def print_verdict(all_issues: list[str]) -> None:
    """Print final GO / NO-GO with remediation steps."""
    section("VERDICT")
    if not all_issues:
        print(ok("ALL CHECKS PASSED — GO FOR LAUNCH"))
        print("\n  Safe to run: python -m src.orchestration.thermal_safe_debate_runner")
    else:
        print(fail(f"NO-GO — {len(all_issues)} issue(s) detected:\n"))
        for i, issue in enumerate(all_issues, 1):
            print(f"    {i}. {issue}")
        print("\n  Recommended actions:")
        print("    1. Run `ollama stop <model>` to unload unused models")
        print("    2. Wait for GPU to cool (check with: nvidia-smi -l 2)")
        print("    3. Close unnecessary processes")
        print("    4. Use thermal_safe_debate_runner instead of adversarial_debate_engine")
        print("    5. If temp won't drop, add external cooling or reduce workload")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 50)
    print("  DGX SPARK PRE-FLIGHT CHECK")
    print("  War Room — System Readiness Diagnostic")
    print("=" * 50)

    all_issues: list[str] = []
    gpu = check_gpu()
    all_issues.extend(print_gpu(gpu))
    cpu = check_cpu()
    all_issues.extend(print_cpu(cpu))
    all_issues.extend(print_ram())
    all_issues.extend(print_disk())
    ollama = check_ollama()
    all_issues.extend(print_ollama(ollama))
    print_verdict(all_issues)
    print()


if __name__ == "__main__":
    main()
