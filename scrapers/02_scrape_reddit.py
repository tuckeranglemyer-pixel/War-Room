"""
Reddit Review Scraper — 20 Project Management Apps
====================================================
SETUP:
1. Go to https://www.reddit.com/prefs/apps/
2. Click "create another app" at the bottom
3. Select "script"
4. Name: "ux-research" | Redirect URI: http://localhost:8080
5. Copy client_id (under the app name) and client_secret
6. Paste them below

pip install praw
"""

import praw
import json
import os
import time

# ============ FILL THESE IN ============
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
# =======================================

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent="ux-research-scraper/1.0"
)

APPS = {
    "asana": ["Asana"],
    "monday": ["Monday.com", "Monday project management"],
    "clickup": ["ClickUp"],
    "trello": ["Trello"],
    "jira": ["Jira", "Jira software"],
    "notion": ["Notion", "Notion app"],
    "todoist": ["Todoist"],
    "basecamp": ["Basecamp"],
    "linear": ["Linear app", "Linear project management"],
    "airtable": ["Airtable"],
    "wrike": ["Wrike"],
    "smartsheet": ["Smartsheet"],
    "teamwork": ["Teamwork.com", "Teamwork project management"],
    "hive": ["Hive project management", "Hive app"],
    "height": ["Height app", "Height project management"],
    "shortcut": ["Shortcut app", "Shortcut project management", "Clubhouse project management"],
    "plane": ["Plane.so", "Plane project management"],
    "taskade": ["Taskade"],
    "nifty": ["Nifty project management", "Nifty PM"],
    "ticktick": ["TickTick"],
}

SEARCH_TEMPLATES = [
    "{} review",
    "{} vs",
    "switched from {}",
    "{} UX",
    "{} onboarding",
    "{} frustrating",
    "{} love",
    "{} alternative",
]

TARGET_SUBREDDITS = [
    "all",
    "SaaS",
    "startups",
    "productivity",
    "projectmanagement",
    "webdev",
    "userexperience",
]


def scrape_app(app_key: str, app_names: list) -> int:
    """Scrape Reddit posts and top comments for a single app and save to JSON.

    Searches ``TARGET_SUBREDDITS`` using each ``SEARCH_TEMPLATES`` query for every
    name variant in ``app_names``, deduplicates by post ID, and writes results to
    ``data/{app_key}/reviews/reddit.json``.

    Args:
        app_key: Short identifier for the app (e.g. ``"notion"``).
        app_names: List of search-friendly name variants (e.g. ``["Notion", "Notion app"]``).

    Returns:
        Total number of unique posts collected.
    """
    print(f"\n{'='*60}")
    print(f"Scraping: {app_key}")
    print(f"{'='*60}")
    
    all_posts = {}
    
    for name in app_names:
        for template in SEARCH_TEMPLATES:
            query = template.format(name)
            for subreddit_name in TARGET_SUBREDDITS:
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    for post in subreddit.search(query, limit=10, sort="relevance"):
                        if post.id in all_posts:
                            continue
                        
                        post.comment_sort = "best"
                        post.comments.replace_more(limit=0)
                        comments = []
                        for comment in post.comments[:15]:
                            if hasattr(comment, 'body') and len(comment.body) > 20:
                                comments.append({
                                    "body": comment.body,
                                    "score": comment.score,
                                    "author": str(comment.author) if comment.author else "[deleted]",
                                })
                        
                        all_posts[post.id] = {
                            "id": post.id,
                            "title": post.title,
                            "body": post.selftext,
                            "score": post.score,
                            "num_comments": post.num_comments,
                            "subreddit": str(post.subreddit),
                            "url": f"https://reddit.com{post.permalink}",
                            "created_utc": post.created_utc,
                            "comments": comments,
                        }
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"  Error on r/{subreddit_name} for '{query}': {e}")
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
    
    print(f"  ✅ {len(posts_list)} posts, {sum(len(p['comments']) for p in posts_list)} comments → {output_path}")
    return len(posts_list)


if __name__ == "__main__":
    print("🔍 Reddit Scraper — 20 PM Apps")
    print(f"   {len(APPS)} apps × {len(TARGET_SUBREDDITS)} subreddits × {len(SEARCH_TEMPLATES)} queries\n")
    
    total = 0
    for app_key, app_names in APPS.items():
        count = scrape_app(app_key, app_names)
        total += count
    
    print(f"\n🎉 DONE. Total posts: {total}")
