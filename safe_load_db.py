"""
Thermal-safe ChromaDB ingestion with progress checkpointing and resumption.

Processes chunks in small batches with cooldown pauses and temperature monitoring.
If the DGX crashes mid-load, re-running this script resumes from the last checkpoint
instead of restarting from zero.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

import chromadb
import psutil

from config import CHROMA_DB_PATH, COLLECTION_NAME

CHUNKS_PATH = Path("chroma_db/data/_processed/all_chunks.json")
CHECKPOINT_PATH = Path("chroma_db/.load_checkpoint.json")

SAFE_BATCH_SIZE = 100
SLEEP_BETWEEN_BATCHES_S = 2
THERMAL_CEILING_C = 85
THERMAL_RESUME_C = 75

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("safe_load_db.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("safe_load_db")


# ---------------------------------------------------------------------------
# Hardware monitoring (mirrors safe_crew.py)
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


def log_system_state(label: str) -> None:
    """Log GPU temp, GPU mem, and RAM usage."""
    gpu_temp = get_gpu_temp()
    gpu_mem = get_gpu_memory()
    ram = psutil.virtual_memory()
    log.info(
        "[%s] GPU: %s°C | GPU Mem: %s/%s MiB | RAM: %.1f/%.1f GB (%s%%)",
        label,
        gpu_temp or "N/A",
        gpu_mem["used_mib"],
        gpu_mem["total_mib"],
        ram.used / (1024 ** 3),
        ram.total / (1024 ** 3),
        ram.percent,
    )


def wait_for_thermal_safe() -> None:
    """Block until GPU temperature drops below THERMAL_RESUME_C."""
    temp = get_gpu_temp()
    if temp is None or temp < THERMAL_CEILING_C:
        return

    log.warning("GPU at %s°C — pausing until <%s°C", temp, THERMAL_RESUME_C)
    while True:
        time.sleep(5)
        temp = get_gpu_temp()
        if temp is None or temp < THERMAL_RESUME_C:
            log.info("GPU cooled to %s°C — resuming", temp)
            return
        log.info("  Cooling... %s°C", temp)


# ---------------------------------------------------------------------------
# Checkpoint management
# ---------------------------------------------------------------------------

def save_checkpoint(batch_end: int, total: int, collection_name: str) -> None:
    """Persist ingestion progress so we can resume after a crash."""
    data = {
        "batch_end": batch_end,
        "total": total,
        "collection_name": collection_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_PATH, "w") as fh:
        json.dump(data, fh)


def load_checkpoint() -> Optional[dict]:
    """Load the last saved checkpoint, or None if no checkpoint exists."""
    if not CHECKPOINT_PATH.exists():
        return None
    try:
        with open(CHECKPOINT_PATH) as fh:
            return json.load(fh)
    except Exception:
        return None


def clear_checkpoint() -> None:
    """Remove checkpoint file after successful completion."""
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()


# ---------------------------------------------------------------------------
# Data loading helpers (from load_db.py)
# ---------------------------------------------------------------------------

def load_chunks() -> list[dict]:
    """Load chunk records from the processed JSON file."""
    log.info("Loading chunks from %s...", CHUNKS_PATH)
    with open(CHUNKS_PATH, encoding="utf-8") as handle:
        data = json.load(handle)
    chunks = data["chunks"]
    log.info("  -> %d chunks found", len(chunks))
    return chunks


def sanitize_metadata(meta: dict) -> dict:
    """Normalize metadata values to ChromaDB-allowed scalars."""
    return {
        k: (v if isinstance(v, (str, int, float, bool)) else str(v) if v is not None else "")
        for k, v in meta.items()
    }


def deduplicate(chunks: list[dict]) -> list[dict]:
    """Drop duplicate chunk IDs, keeping first occurrence."""
    seen: set[str] = set()
    unique: list[dict] = []
    for chunk in chunks:
        if chunk["id"] not in seen:
            seen.add(chunk["id"])
            unique.append(chunk)
    dropped = len(chunks) - len(unique)
    if dropped:
        log.info("  Deduped: dropped %d duplicates -> %d unique", dropped, len(unique))
    return unique


# ---------------------------------------------------------------------------
# Safe collection builder with checkpointing
# ---------------------------------------------------------------------------

def build_collection_safe(chunks: list[dict]) -> None:
    """Ingest chunks into ChromaDB with small batches, cooldown, and checkpointing.

    If a checkpoint exists from a previous interrupted run, resumes from where
    it left off instead of re-creating the collection.
    """
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    checkpoint = load_checkpoint()
    resume_from = 0

    if checkpoint and checkpoint.get("collection_name") == COLLECTION_NAME:
        resume_from = checkpoint["batch_end"]
        log.info(
            "RESUMING from checkpoint: %d/%d chunks already loaded (saved %s)",
            resume_from,
            checkpoint["total"],
            checkpoint["timestamp"],
        )
        try:
            collection = client.get_collection(name=COLLECTION_NAME)
        except Exception:
            log.warning("Collection not found despite checkpoint — starting fresh")
            resume_from = 0
            collection = None

    if resume_from == 0:
        try:
            client.delete_collection(COLLECTION_NAME)
            log.info("  Dropped existing '%s' collection", COLLECTION_NAME)
        except Exception:
            pass
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("  Created collection '%s'", COLLECTION_NAME)

    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [sanitize_metadata(c["metadata"]) for c in chunks]

    total = len(chunks)
    start = time.time()

    log_system_state("LOAD-START")

    for batch_start in range(resume_from, total, SAFE_BATCH_SIZE):
        batch_end = min(batch_start + SAFE_BATCH_SIZE, total)

        wait_for_thermal_safe()

        try:
            collection.add(
                ids=ids[batch_start:batch_end],
                documents=texts[batch_start:batch_end],
                metadatas=metadatas[batch_start:batch_end],
            )
        except Exception as exc:
            log.error(
                "BATCH FAILED at [%d:%d] — saving checkpoint and aborting: %s",
                batch_start, batch_end, exc,
            )
            save_checkpoint(batch_start, total, COLLECTION_NAME)
            raise

        save_checkpoint(batch_end, total, COLLECTION_NAME)

        elapsed = time.time() - start
        pct = batch_end / total * 100
        eta = (elapsed / (batch_end - resume_from)) * (total - batch_end) if batch_end > resume_from else 0

        log.info(
            "  [%6d/%d] %5.1f%%  elapsed=%ds  eta=%ds",
            batch_end, total, pct, int(elapsed), int(eta),
        )

        if batch_end < total:
            if batch_end % (SAFE_BATCH_SIZE * 5) == 0:
                log_system_state(f"BATCH-{batch_end}")
            time.sleep(SLEEP_BETWEEN_BATCHES_S)

    clear_checkpoint()
    elapsed_total = time.time() - start
    log.info(
        "Loaded %d chunks into '%s' in %.1fs",
        total, COLLECTION_NAME, elapsed_total,
    )
    log.info("   Collection count: %d", collection.count())
    log_system_state("LOAD-COMPLETE")


if __name__ == "__main__":
    log.info("=" * 60)
    log.info("SAFE LOAD DB — Thermal-safe ChromaDB ingestion")
    log.info("  Batch size: %d (was 500)", SAFE_BATCH_SIZE)
    log.info("  Cooldown: %ds between batches", SLEEP_BETWEEN_BATCHES_S)
    log.info("  Thermal ceiling: %d°C (pause until %d°C)", THERMAL_CEILING_C, THERMAL_RESUME_C)
    log.info("  Checkpoint file: %s", CHECKPOINT_PATH)
    log.info("=" * 60)

    loaded = load_chunks()
    loaded = deduplicate(loaded)
    build_collection_safe(loaded)
