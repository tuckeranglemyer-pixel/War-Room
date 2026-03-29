"""
ChromaDB batch loader — one-time ingestion of the full pm_tools corpus.

Run after the chunking pipeline produces:
    chroma_db/data/_processed/all_chunks.json

This script drops and recreates the pm_tools collection, then bulk-inserts
all chunks in batches of 500. For crash-safe loading on DGX Spark hardware,
use chroma_safe_batch_loader.py instead (smaller batches + checkpointing).

Usage:
    python -m ingestion.chroma_batch_loader
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import chromadb

from src.inference.model_config import CHROMA_DB_PATH, COLLECTION_NAME

CHUNKS_PATH = Path("chroma_db/data/_processed/all_chunks.json")
BATCH_SIZE = 500


def load_chunks() -> list[dict]:
    """Load chunk records from the processed JSON file.

    Returns:
        The ``chunks`` list from the JSON document.

    Raises:
        FileNotFoundError: If CHUNKS_PATH does not exist.
        KeyError: If the JSON document lacks a ``chunks`` key.
    """
    print(f"Loading chunks from {CHUNKS_PATH}...")
    with open(CHUNKS_PATH, encoding="utf-8") as handle:
        data = json.load(handle)
    chunks = data["chunks"]
    print(f"  → {len(chunks):,} chunks found")
    return chunks


def sanitize_metadata(meta: dict) -> dict:
    """Normalize metadata values to ChromaDB-allowed scalars.

    Args:
        meta: Raw metadata dict possibly containing None or nested values.

    Returns:
        Flat dict with only str, int, float, or bool values.
    """
    return {
        k: (v if isinstance(v, (str, int, float, bool)) else str(v) if v is not None else "")
        for k, v in meta.items()
    }


def deduplicate(chunks: list[dict]) -> list[dict]:
    """Drop duplicate chunk IDs, keeping first occurrence.

    Args:
        chunks: Full chunk list from load_chunks.

    Returns:
        Deduplicated chunks in original order.
    """
    seen: set[str] = set()
    unique: list[dict] = []
    for chunk in chunks:
        if chunk["id"] not in seen:
            seen.add(chunk["id"])
            unique.append(chunk)
    dropped = len(chunks) - len(unique)
    if dropped:
        print(f"  Deduped: dropped {dropped:,} duplicate IDs → {len(unique):,} unique")
    return unique


def build_collection(chunks: list[dict]) -> None:
    """Recreate COLLECTION_NAME and bulk-insert all chunk documents.

    Args:
        chunks: Unique chunk dicts with ``id``, ``text``, and ``metadata`` keys.
    """
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Dropped existing '{COLLECTION_NAME}' collection")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"  Created collection '{COLLECTION_NAME}'")

    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [sanitize_metadata(c["metadata"]) for c in chunks]

    total = len(chunks)
    start = time.time()

    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        collection.add(
            ids=ids[batch_start:batch_end],
            documents=texts[batch_start:batch_end],
            metadatas=metadatas[batch_start:batch_end],
        )
        elapsed = time.time() - start
        pct = batch_end / total * 100
        eta = (elapsed / batch_end) * (total - batch_end) if batch_end > 0 else 0
        print(f"  [{batch_end:>6,}/{total:,}] {pct:5.1f}%  elapsed={elapsed:.0f}s  eta={eta:.0f}s")

    print(f"\n✅ Loaded {total:,} chunks into '{COLLECTION_NAME}' in {time.time() - start:.1f}s")
    print(f"   Collection count: {collection.count():,}")


if __name__ == "__main__":
    loaded = load_chunks()
    loaded = deduplicate(loaded)
    build_collection(loaded)
