"""One-time script to populate ChromaDB pm_tools collection from all_chunks.json."""
import json
import time
from pathlib import Path

import chromadb

CHUNKS_PATH = Path("chroma_db/data/_processed/all_chunks.json")
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "pm_tools"
BATCH_SIZE = 500


def load_chunks() -> list[dict]:
    print(f"Loading chunks from {CHUNKS_PATH}...")
    with open(CHUNKS_PATH) as f:
        data = json.load(f)
    chunks = data["chunks"]
    print(f"  → {len(chunks):,} chunks found")
    return chunks


def sanitize_metadata(meta: dict) -> dict:
    """ChromaDB requires metadata values to be str, int, float, or bool — not None."""
    return {
        k: (v if isinstance(v, (str, int, float, bool)) else str(v) if v is not None else "")
        for k, v in meta.items()
    }


def deduplicate(chunks: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique = []
    for chunk in chunks:
        if chunk["id"] not in seen:
            seen.add(chunk["id"])
            unique.append(chunk)
    dropped = len(chunks) - len(unique)
    if dropped:
        print(f"  Deduped: dropped {dropped:,} duplicate IDs → {len(unique):,} unique")
    return unique


def build_collection(chunks: list[dict]) -> None:
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Drop and recreate to ensure clean state
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
    chunks = load_chunks()
    chunks = deduplicate(chunks)
    build_collection(chunks)
