"""
Screenshot suite matcher.

Loads the 69-app UI screenshot analysis suite from screenshot_chunks.json,
embeds all documents once using sentence-transformers (all-MiniLM-L6-v2),
and provides cosine-similarity search for matching user-uploaded frames
against competitor UI patterns.

Embeddings are computed once on first call and cached in module-level
variables for the lifetime of the process.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

_SUITE_PATH = Path(__file__).parent.parent / "screenshot_chunks.json"

_model: Any = None
_chunks: list[dict] | None = None
_embeddings: Any = None  # np.ndarray shape (N, D)


def _load_suite() -> None:
    """Load chunks and compute embeddings on first call (lazy, cached)."""
    global _model, _chunks, _embeddings
    if _chunks is not None:
        return

    if not _SUITE_PATH.exists():
        return

    from sentence_transformers import SentenceTransformer  # noqa: PLC0415

    with open(_SUITE_PATH, encoding="utf-8") as fh:
        _chunks = json.load(fh)

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    docs = [c["document"] for c in _chunks]
    _embeddings = _model.encode(docs, normalize_embeddings=True)


def find_similar_screens(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Return the top-k screenshot chunks most similar to *query*.

    Args:
        query: Natural-language description to search against (typically a
            UX analysis of a user-uploaded frame).
        top_k: Number of results to return.

    Returns:
        List of dicts with keys: ``app``, ``filename``, ``similarity_score``,
        ``document``.  Empty list if the suite is not available.
    """
    _load_suite()
    if _chunks is None or _embeddings is None or _model is None:
        return []

    q_emb = _model.encode([query], normalize_embeddings=True)
    sims: np.ndarray = np.dot(_embeddings, q_emb.T).flatten()
    top_idx = np.argsort(sims)[::-1][:top_k]

    results = []
    for idx in top_idx:
        chunk = _chunks[idx]
        app = chunk["metadata"]["app"]
        filename = chunk["metadata"]["filename"]
        results.append(
            {
                "app": app,
                "filename": filename,
                # Constructed once here; passed through every downstream module unchanged.
                "image_path": f"data/{app}/screenshots/{filename}",
                "similarity_score": float(sims[idx]),
                "document": chunk["document"],
            }
        )
    return results
