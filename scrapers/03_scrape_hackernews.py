"""
Hacker News Scraper — 20 PM Apps (Algolia API, no auth needed)
===============================================================
pip install requests
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
    "linear": ["Linear.app", "Linear app"],
    "airtable": ["Airtable"],
    "wrike": ["Wrike"],
    "smartsheet": ["Smartsheet"],
    "teamwork": ["Teamwork.com"],
    "hive": ["Hive project management"],
    "height": ["Height.app"],
    "shortcut": ["Shortcut.com", "Clubhouse PM"],
    "plane": ["Plane.so"],
    "taskade": ["Taskade"],
    "nifty": ["Nifty PM"],
    "ticktick": ["TickTick"],
}

BASE_URL = "https://hn.algolia.com/api/v1"


def search_hn(query, tag="comment", hits_per_page=50):
    resp = requests.get(f"{BASE_URL}/search", params={
        "query": query,
        "tags": tag,
        "hitsPerPage": hits_per_page,
    })
    resp.raise_for_status()
    return resp.json()


def scrape_app(app_key, app_names):
    print(f"\n  {app_key}...")
    all_hits = {}
    
    for name in app_names:
        for suffix in ["", " UX", " review", " alternative", " vs"]:
            try:
                result = search_hn(f"{name}{suffix}", tag="comment", hits_per_page=50)
                for hit in result.get("hits", []):
                    if hit["objectID"] not in all_hits:
                        text = hit.get("comment_text", "") or ""
                        if len(text) > 30:
                            import re
                            clean = re.sub(r'<[^>]+>', '', text)
                            all_hits[hit["objectID"]] = {
                                "id": hit["objectID"],
                                "type": "comment",
                                "text": clean,
                                "author": hit.get("author", ""),
                                "points": hit.get("points"),
                                "created_at": hit.get("created_at", ""),
                                "story_title": hit.get("story_title", ""),
                                "hn_url": f"https://news.ycombinator.com/item?id={hit['objectID']}",
                            }
                
                result = search_hn(f"{name}{suffix}", tag="story", hits_per_page=20)
                for hit in result.get("hits", []):
                    if hit["objectID"] not in all_hits:
                        all_hits[hit["objectID"]] = {
                            "id": hit["objectID"],
                            "type": "story",
                            "title": hit.get("title", ""),
                            "text": hit.get("story_text", "") or "",
                            "author": hit.get("author", ""),
                            "points": hit.get("points", 0),
                            "num_comments": hit.get("num_comments", 0),
                            "created_at": hit.get("created_at", ""),
                            "hn_url": f"https://news.ycombinator.com/item?id={hit['objectID']}",
                        }
                
                time.sleep(0.3)
            except Exception as e:
                print(f"    Error: {e}")
                time.sleep(1)
    
    hits_list = list(all_hits.values())
    
    os.makedirs(f"data/{app_key}/reviews", exist_ok=True)
    output_path = f"data/{app_key}/reviews/hackernews.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "app": app_key,
            "source": "hackernews",
            "total_items": len(hits_list),
            "items": hits_list,
        }, f, indent=2, ensure_ascii=False)
    
    print(f"    ✅ {len(hits_list)} items → {output_path}")
    return len(hits_list)


if __name__ == "__main__":
    print("🔍 Hacker News Scraper — No Auth Required\n")
    total = 0
    for app_key, app_names in APPS.items():
        count = scrape_app(app_key, app_names)
        total += count
    print(f"\n🎉 DONE. Total HN items: {total}")
