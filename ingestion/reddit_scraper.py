"""
Reddit Scraper — NO AUTH REQUIRED
===================================
Uses Reddit's public JSON API (just append .json to any URL).
Slower due to rate limits but zero setup needed.
"""

import requests
import json
import os
import time

APPS = {
    "asana": ["Asana"],
    "monday": ["Monday.com"],
    "clickup": ["ClickUp"],
    "trello": ["Trello"],
    "jira": ["Jira"],
    "notion": ["Notion"],
    "todoist": ["Todoist"],
    "basecamp": ["Basecamp"],
    "linear": ["Linear+app"],
    "airtable": ["Airtable"],
    "wrike": ["Wrike"],
    "smartsheet": ["Smartsheet"],
    "teamwork": ["Teamwork.com"],
    "hive": ["Hive+project+management"],
    "height": ["Height+app+project"],
    "shortcut": ["Shortcut+project+management"],
    "plane": ["Plane.so"],
    "taskade": ["Taskade"],
    "nifty": ["Nifty+project+management"],
    "ticktick": ["TickTick"],
}

SEARCH_SUFFIXES = [
    "+review",
    "+vs",
    "+UX",
    "+onboarding",
    "+alternative",
    "+frustrating",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def search_reddit(query: str, limit: int = 25) -> list:
    """Query Reddit's public search JSON endpoint and return raw post children.

    Handles HTTP 429 rate-limit responses with a 60-second back-off retry.

    Args:
        query: URL-encoded search string (spaces replaced with ``+``).
        limit: Maximum number of results to request (default 25).

    Returns:
        List of post ``children`` dicts from the Reddit JSON response, or an
        empty list on error or non-200 status.
    """
    url = f"https://www.reddit.com/search.json?q={query}&sort=relevance&limit={limit}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 429:
            print("    Rate limited, waiting 60s...")
            time.sleep(60)
            resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"    HTTP {resp.status_code} for: {query}")
            return []
        data = resp.json()
        return data.get("data", {}).get("children", [])
    except Exception as e:
        print(f"    Error: {e}")
        return []


def get_comments(permalink: str, limit: int = 15) -> list:
    """Fetch the top comments for a Reddit post via the public JSON API.

    Args:
        permalink: Reddit post permalink path (e.g. ``"/r/productivity/comments/..."``).
        limit: Maximum number of comments to retrieve (default 15).

    Returns:
        List of comment dicts with ``body``, ``score``, and ``author`` keys;
        empty list on request failure or if comments are missing.
    """
    url = f"https://www.reddit.com{permalink}.json?limit={limit}&sort=best"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if len(data) < 2:
            return []
        comments = []
        for child in data[1].get("data", {}).get("children", []):
            if child.get("kind") != "t1":
                continue
            body = child.get("data", {}).get("body", "")
            if len(body) > 20:
                comments.append({
                    "body": body,
                    "score": child["data"].get("score", 0),
                    "author": child["data"].get("author", "[deleted]"),
                })
        return comments
    except:
        return []


def scrape_app(app_key: str, app_names: list) -> int:
    """Scrape Reddit posts for a single app using the no-auth public JSON API.

    Iterates over name variants and search suffixes, deduplicates by post ID,
    fetches comments for qualifying posts, and writes results to
    ``data/{app_key}/reviews/reddit.json``.

    Args:
        app_key: Short identifier for the app (e.g. ``"notion"``).
        app_names: List of URL-encoded name variants (spaces replaced with ``+``).

    Returns:
        Total number of unique posts collected.
    """
    print(f"\n{'='*60}")
    print(f"  {app_key}")
    print(f"{'='*60}")
    
    all_posts = {}
    
    for name in app_names:
        for suffix in SEARCH_SUFFIXES:
            query = f"{name}{suffix}"
            print(f"    Searching: {query}")
            
            results = search_reddit(query, limit=25)
            
            for item in results:
                post = item.get("data", {})
                post_id = post.get("id", "")
                if post_id in all_posts:
                    continue
                if not post.get("selftext") and post.get("score", 0) < 5:
                    continue
                
                time.sleep(2)
                comments = get_comments(post.get("permalink", ""))
                
                all_posts[post_id] = {
                    "id": post_id,
                    "title": post.get("title", ""),
                    "body": post.get("selftext", ""),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "subreddit": post.get("subreddit", ""),
                    "url": f"https://reddit.com{post.get('permalink', '')}",
                    "created_utc": post.get("created_utc", 0),
                    "comments": comments,
                }
            
            time.sleep(2)
    
    posts_list = sorted(all_posts.values(), key=lambda x: x["score"], reverse=True)
    
    os.makedirs(f"data/{app_key}/reviews", exist_ok=True)
    output_path = f"data/{app_key}/reviews/reddit.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "app": app_key,
            "source": "reddit",
            "total_posts": len(posts_list),
            "total_comments": sum(len(p["comments"]) for p in posts_list),
            "posts": posts_list,
        }, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ {len(posts_list)} posts, {sum(len(p['comments']) for p in posts_list)} comments")
    return len(posts_list)


if __name__ == "__main__":
    print("🔍 Reddit Scraper — NO AUTH REQUIRED")
    print(f"   {len(APPS)} apps × {len(SEARCH_SUFFIXES)} queries")
    print(f"   Slower due to rate limits (~2s between requests)\n")
    
    total = 0
    for app_key, app_names in APPS.items():
        count = scrape_app(app_key, app_names)
        total += count
    
    print(f"\n🎉 DONE. Total posts: {total}")
