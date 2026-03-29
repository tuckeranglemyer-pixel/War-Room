"""
Evidence curator — smart themed RAG query generator for screenshot comparisons.

Given a user's frame UX analysis and a matched competitor screenshot, uses
GPT-4o-mini to extract shared UX themes, then runs targeted ChromaDB queries
(filtered by the specific competitor app) to pull real user reviews that
validate or contradict those exact UI patterns.

Flow:
    1. Theme extraction — GPT-4o-mini identifies 3-5 shared UX themes
    2. Targeted RAG — each theme's queries hit ChromaDB filtered to app=matched_app
    3. Score + dedup — reviews appearing across multiple queries get a relevance boost
    4. Return structured evidence per theme with classified sentiment
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import chromadb
from openai import OpenAI

# ---------------------------------------------------------------------------
# Module-level singletons (lazy-initialized)
# ---------------------------------------------------------------------------

_CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", "./chroma_db")
_COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "pm_tools")

_openai_client: OpenAI | None = None
_chroma_collection: Any = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    return _openai_client


def _get_collection() -> Any:
    global _chroma_collection
    if _chroma_collection is None:
        try:
            client = chromadb.PersistentClient(path=_CHROMA_DB_PATH)
            _chroma_collection = client.get_collection(_COLLECTION_NAME)
        except Exception:
            pass
    return _chroma_collection


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

THEME_EXTRACTION_PROMPT = """\
Given these two UX analyses — one of a user's product and one of a competitor — extract \
exactly 3-5 specific UX themes they share in common.

USER'S PRODUCT:
{user_analysis}

COMPETITOR ({app}):
{competitor_analysis}

The user's product targets: {target_user}
Their key differentiator is: {differentiator}
Their product stage is: {product_stage}

For each shared theme output:
- theme_name: 2-4 word label (e.g. "sidebar navigation density", "onboarding wizard flow")
- user_observation: what the user's product does for this theme (1 sentence)
- competitor_observation: what the competitor does for this theme (1 sentence)
- rag_queries: 2-3 search queries to find real user reviews about this EXACT theme in the competitor

Tailor theme analysis and rag_queries to what THIS type of user cares about most.
Keep rag_queries ultra-specific — not "asana reviews" but "asana sidebar overwhelming new users" \
or "asana navigation too many options confusing".

Output ONLY a valid JSON array. No markdown fences, no explanation.
[
  {{
    "theme_name": "...",
    "user_observation": "...",
    "competitor_observation": "...",
    "rag_queries": ["...", "..."]
  }}
]"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> Any:
    """Robustly extract a JSON value from LLM output that may include markdown fences."""
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for start_ch, end_ch in [("[", "]"), ("{", "}")]:
        start = text.find(start_ch)
        end = text.rfind(end_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def _query_reviews(query: str, app: str, n_results: int = 3) -> list[dict[str, Any]]:
    """Query ChromaDB filtered to a single app and return formatted result dicts."""
    collection = _get_collection()
    if collection is None:
        return []
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"app": app},
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return [{"text": doc, "metadata": meta} for doc, meta in zip(docs, metas)]
    except Exception:
        return []


def _classify_sentiment(text: str, metadata: dict[str, Any]) -> str:
    """Classify review sentiment using rating metadata first, then text heuristics."""
    rating = metadata.get("rating")
    if rating is not None:
        try:
            r = float(rating)
            if r >= 4.0:
                return "positive"
            if r <= 2.0:
                return "negative"
            return "mixed"
        except (ValueError, TypeError):
            pass
    lowered = text.lower()
    pos = {"love", "great", "excellent", "perfect", "amazing", "best", "easy", "intuitive", "helpful"}
    neg = {"hate", "terrible", "awful", "confusing", "difficult", "broken", "worst", "frustrating", "overwhelming", "slow"}
    pos_hits = sum(1 for w in pos if w in lowered)
    neg_hits = sum(1 for w in neg if w in lowered)
    if pos_hits > neg_hits:
        return "positive"
    if neg_hits > pos_hits:
        return "negative"
    return "neutral"


def _score_and_deduplicate(
    raw_results: list[tuple[str, dict[str, Any]]],
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Deduplicate reviews across queries, boosting those that appear multiple times.

    Args:
        raw_results: List of (query_string, result_dict) pairs.
        top_n: How many reviews to return after ranking.

    Returns:
        Ranked list of review dicts with relevance_score, source, and sentiment.
    """
    seen: dict[str, dict[str, Any]] = {}  # key = first 80 chars of text
    for _query, result in raw_results:
        text = result["text"]
        key = text[:80]
        if key in seen:
            # Boost reviews that match multiple queries — they're more on-topic
            seen[key]["relevance_score"] = min(1.0, seen[key]["relevance_score"] + 0.15)
        else:
            seen[key] = {
                "text": text,
                "source": result["metadata"].get("source", "unknown"),
                "sentiment": _classify_sentiment(text, result["metadata"]),
                "relevance_score": 0.70,
            }
    ranked = sorted(seen.values(), key=lambda x: x["relevance_score"], reverse=True)
    return ranked[:top_n]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def curate_evidence(
    user_context: dict[str, Any],
    user_frame_analysis: str,
    matched_screenshot: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return curated theme evidence combining UX theme extraction and targeted RAG.

    Args:
        user_context: Onboarding answers (target_user, differentiator, product_stage, …).
        user_frame_analysis: The ``ux_analysis`` string for the user's video frame
            (produced by UX_MATCH_PROMPT in server.py).
        matched_screenshot: A single result from ``matcher.find_similar_screens`` —
            must have keys: ``app``, ``filename``, ``similarity_score``, ``document``.

    Returns:
        List of theme dicts, each with: ``theme_name``, ``user_observation``,
        ``competitor_observation``, ``supporting_reviews``.
        Returns an empty list on any failure so the caller can degrade gracefully.
    """
    app = matched_screenshot.get("app", "unknown")
    competitor_analysis = matched_screenshot.get("document", "")

    # --- Step 1: Extract shared UX themes via GPT-4o-mini ---
    prompt = THEME_EXTRACTION_PROMPT.format(
        user_analysis=user_frame_analysis[:2000],
        app=app,
        competitor_analysis=competitor_analysis[:2000],
        target_user=user_context.get("target_user", "not specified"),
        differentiator=user_context.get("differentiator", "not specified"),
        product_stage=user_context.get("product_stage", "not specified"),
    )
    try:
        response = _get_openai().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
        themes_raw = _extract_json(raw)
        if not isinstance(themes_raw, list):
            themes_raw = []
    except Exception as exc:
        print(f"   WARNING: Theme extraction failed for {app}: {exc}")
        return []

    # --- Steps 2 + 3: Targeted RAG + dedup per theme ---
    results_out: list[dict[str, Any]] = []
    for theme in themes_raw[:5]:
        rag_queries: list[str] = theme.get("rag_queries", [])
        raw_results: list[tuple[str, dict[str, Any]]] = []
        for q in rag_queries[:3]:
            for review in _query_reviews(q, app, n_results=3):
                raw_results.append((q, review))

        supporting = _score_and_deduplicate(raw_results, top_n=5)

        results_out.append(
            {
                "theme_name": theme.get("theme_name", "unknown"),
                "user_observation": theme.get("user_observation", ""),
                "competitor_observation": theme.get("competitor_observation", ""),
                "supporting_reviews": supporting,
            }
        )

    return results_out
