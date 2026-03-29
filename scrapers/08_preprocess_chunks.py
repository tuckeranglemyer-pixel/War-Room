"""
Pre-Processor: Raw Data → RAG-Ready Chunks
============================================
Run AFTER all scraping is done. Produces data/_processed/all_chunks.json
which is THE file you bring to the hackathon.
"""

import json
import os
import re
import hashlib
from datetime import datetime


def make_id(text: str, prefix: str = "") -> str:
    """Generate a short deterministic ID from text via MD5 hash.

    Args:
        text: Source string to hash.
        prefix: Optional prefix prepended with an underscore separator.

    Returns:
        A 10-character hex digest, optionally prefixed (e.g. ``"reddit_abc123def4"``).
    """
    h = hashlib.md5(text.encode()).hexdigest()[:10]
    return f"{prefix}_{h}" if prefix else h


def chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> list:
    """Split long text into overlapping chunks suitable for vector embedding.

    Splits on sentence boundaries (``". "``) when possible to preserve semantic
    coherence. Returns a single-element list when ``text`` fits within ``max_chars``.

    Args:
        text: Raw text to split.
        max_chars: Maximum character length per chunk.
        overlap: Number of trailing characters from the previous chunk to prepend
            to the next, providing context continuity across chunk boundaries.

    Returns:
        List of non-empty string chunks.
    """
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end < len(text):
            last_period = text[start:end].rfind('. ')
            if last_period > max_chars * 0.5:
                end = start + last_period + 1
        chunks.append(text[start:end].strip())
        start = end - overlap
    return chunks


def process_reddit(app_key: str) -> list:
    """Convert scraped Reddit posts and comments for one app into RAG-ready chunks.

    Reads ``data/{app_key}/reviews/reddit.json``, skips bodies shorter than 30 chars,
    and splits long posts/comments via ``chunk_text``. Each chunk carries source
    metadata (subreddit, score, URL).

    Args:
        app_key: Short app identifier matching the data directory (e.g. ``"notion"``).

    Returns:
        List of chunk dicts with ``id``, ``text``, and ``metadata`` keys.
        Returns an empty list if the source file does not exist.
    """
    chunks = []
    path = f"data/{app_key}/reviews/reddit.json"
    if not os.path.exists(path):
        return chunks
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for post in data.get("posts", []):
        if post.get("body") and len(post["body"]) > 30:
            text = f"[Reddit Post] {post['title']}\n\n{post['body']}"
            for i, piece in enumerate(chunk_text(text)):
                chunks.append({
                    "id": make_id(piece, f"reddit_{app_key}"),
                    "text": piece,
                    "metadata": {
                        "app": app_key, "source": "reddit", "type": "post",
                        "subreddit": post.get("subreddit", ""),
                        "score": post.get("score", 0),
                        "url": post.get("url", ""),
                    }
                })
        for comment in post.get("comments", []):
            body = comment.get("body", "")
            if len(body) > 50:
                context = f"[Reddit Comment on: {post['title']}]\n\n{body}"
                for i, piece in enumerate(chunk_text(context)):
                    chunks.append({
                        "id": make_id(piece, f"rcmt_{app_key}"),
                        "text": piece,
                        "metadata": {
                            "app": app_key, "source": "reddit", "type": "comment",
                            "subreddit": post.get("subreddit", ""),
                            "score": comment.get("score", 0),
                        }
                    })
    return chunks


def process_hackernews(app_key: str) -> list:
    """Convert scraped Hacker News items for one app into RAG-ready chunks.

    Strips HTML tags from comment text and labels each chunk as either
    ``[HN Story]`` or ``[HN Comment]`` with story title context.

    Args:
        app_key: Short app identifier matching the data directory (e.g. ``"linear"``).

    Returns:
        List of chunk dicts with ``id``, ``text``, and ``metadata`` keys.
        Returns an empty list if the source file does not exist.
    """
    chunks = []
    path = f"data/{app_key}/reviews/hackernews.json"
    if not os.path.exists(path):
        return chunks
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for item in data.get("items", []):
        text = item.get("text", "") or item.get("title", "")
        if len(text) > 30:
            clean = re.sub(r'<[^>]+>', '', text)
            prefix = "[HN Story]" if item.get("type") == "story" else "[HN Comment]"
            story_title = item.get("story_title", item.get("title", ""))
            context = f"{prefix} (re: {story_title})\n\n{clean}"
            for piece in chunk_text(context):
                chunks.append({
                    "id": make_id(piece, f"hn_{app_key}"),
                    "text": piece,
                    "metadata": {
                        "app": app_key, "source": "hackernews",
                        "type": item.get("type", "comment"),
                        "hn_url": item.get("hn_url", ""),
                    }
                })
    return chunks


def process_appstores(app_key: str) -> list:
    """Convert Google Play and Apple App Store reviews for one app into RAG-ready chunks.

    Each review is prefixed with its star rating for easy filtering during RAG retrieval.
    Reviews shorter than 20 characters are skipped.

    Args:
        app_key: Short app identifier matching the data directory (e.g. ``"trello"``).

    Returns:
        List of chunk dicts with ``id``, ``text``, and ``metadata`` keys.
        Returns an empty list if the source file does not exist.
    """
    chunks = []
    path = f"data/{app_key}/reviews/appstores.json"
    if not os.path.exists(path):
        return chunks
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for review in data.get("play_store_reviews", []):
        text = review.get("text", "")
        if len(text) > 20:
            context = f"[Google Play Review - {review.get('rating', '?')}/5]\n\n{text}"
            chunks.append({
                "id": make_id(context, f"gplay_{app_key}"),
                "text": context,
                "metadata": {
                    "app": app_key, "source": "google_play", "type": "review",
                    "rating": review.get("rating"),
                }
            })
    
    for review in data.get("app_store_reviews", []):
        text = review.get("text", "")
        if len(text) > 20:
            title = review.get("title", "")
            context = f"[App Store Review - {review.get('rating', '?')}/5] {title}\n\n{text}"
            chunks.append({
                "id": make_id(context, f"ios_{app_key}"),
                "text": context,
                "metadata": {
                    "app": app_key, "source": "app_store", "type": "review",
                    "rating": review.get("rating"),
                }
            })
    return chunks


def process_g2(app_key: str) -> list:
    """Convert G2 business reviews for one app into RAG-ready chunks.

    Separates ``likes`` and ``dislikes`` fields into distinct chunks so retrieval
    queries for positive vs. negative sentiment are more precise.

    Args:
        app_key: Short app identifier matching the data directory (e.g. ``"asana"``).

    Returns:
        List of chunk dicts with ``id``, ``text``, and ``metadata`` keys.
        Returns an empty list if the source file does not exist.
    """
    chunks = []
    path = f"data/{app_key}/reviews/g2.json"
    if not os.path.exists(path):
        return chunks
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for review in data.get("reviews", []):
        rating = review.get("rating", "?")
        for field, label in [("likes", "What they like"), ("dislikes", "What they dislike")]:
            text = review.get(field, "")
            if text and len(text) > 20:
                context = f"[G2 Review - {rating}/5 - {label}]\n\n{text}"
                chunks.append({
                    "id": make_id(context, f"g2_{app_key}"),
                    "text": context,
                    "metadata": {
                        "app": app_key, "source": "g2",
                        "type": "review_positive" if field == "likes" else "review_negative",
                        "rating": rating,
                        "reviewer_role": review.get("reviewer_role", ""),
                    }
                })
    return chunks


def process_metadata(app_key: str) -> list:
    """Build a single structured overview chunk from an app's metadata JSON file.

    Concatenates category, use case, key features, pricing, target audience, and
    competitors into a prose sentence suitable for embedding. Used by agents for
    competitive-positioning queries.

    Args:
        app_key: Short app identifier matching the data directory (e.g. ``"jira"``).

    Returns:
        A one-element list containing the metadata chunk dict, or an empty list
        if the source file does not exist.
    """
    path = f"data/{app_key}/metadata.json"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    
    text = (
        f"{meta['name']} is a {meta['category'].replace('_', ' ')} tool. "
        f"{meta['primary_use_case']}. "
        f"Key features: {', '.join(meta.get('key_features', [])[:8])}. "
        f"Pricing: {meta.get('pricing_range', 'N/A')}. "
        f"Target: {', '.join(meta.get('target_audience', []))}. "
        f"Competitors: {', '.join(meta.get('competitors', []))}."
    )
    return [{
        "id": f"meta_{app_key}",
        "text": text,
        "metadata": {
            "app": app_key, "source": "metadata", "type": "app_overview",
            "category": meta.get("category", ""),
        }
    }]


if __name__ == "__main__":
    print("⚙️  Pre-Processor: Raw → RAG Chunks\n")
    
    all_chunks = []
    stats = {}
    apps = sorted([d for d in os.listdir("data") if os.path.isdir(f"data/{d}") and d != "_processed"])
    
    for app_key in apps:
        reddit = process_reddit(app_key)
        hn = process_hackernews(app_key)
        appstore = process_appstores(app_key)
        g2 = process_g2(app_key)
        meta = process_metadata(app_key)
        
        app_chunks = reddit + hn + appstore + g2 + meta
        total = len(app_chunks)
        stats[app_key] = {"total": total, "reddit": len(reddit), "hn": len(hn), "appstore": len(appstore), "g2": len(g2)}
        all_chunks.extend(app_chunks)
        
        print(f"  {app_key:15s} → {total:5d} chunks  (reddit:{len(reddit)} hn:{len(hn)} appstore:{len(appstore)} g2:{len(g2)})")
    
    # Save master file
    os.makedirs("data/_processed", exist_ok=True)
    master = {
        "generated_at": datetime.now().isoformat(),
        "total_chunks": len(all_chunks),
        "total_apps": len(apps),
        "stats": stats,
        "chunks": all_chunks,
    }
    with open("data/_processed/all_chunks.json", "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2, ensure_ascii=False)
    
    # Per-app files
    for app_key in apps:
        app_chunks = [c for c in all_chunks if c["metadata"]["app"] == app_key]
        with open(f"data/_processed/{app_key}_chunks.json", "w", encoding="utf-8") as f:
            json.dump({"app": app_key, "chunks": app_chunks}, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"  TOTAL: {len(all_chunks)} chunks across {len(apps)} apps")
    print(f"  Master file: data/_processed/all_chunks.json")
    print(f"{'='*60}")
    print(f"\n✅ Bring all_chunks.json + the screenshots folder to Saturday.")
