"""
App Store + Google Play Store Review Scraper — 20 PM Apps
==========================================================
pip install google-play-scraper app-store-scraper
"""

import json
import os
import time

from google_play_scraper import reviews as gplay_reviews, Sort
from app_store_scraper import AppStore

# Google Play package IDs (some smaller apps may not have mobile apps — they'll fail gracefully)
PLAY_STORE_IDS = {
    "asana": "com.asana.app",
    "monday": "com.monday.monday",
    "clickup": "com.clickup.mobile",
    "trello": "com.trello",
    "jira": "com.atlassian.android.jira.core",
    "notion": "notion.id",
    "todoist": "com.todoist",
    "basecamp": "com.basecamp.bc3",
    "linear": "com.linear",
    "airtable": "com.formagrid.airtable",
    "wrike": "com.wrike",
    "smartsheet": "com.smartsheet.android",
    "teamwork": "com.teamwork.projects",
    "hive": "com.hive.android",
    "shortcut": "io.clubhouse.clubhouse",
    "taskade": "com.taskade.mobile",
    "nifty": "com.niftypm.app",
    "ticktick": "com.ticktick.task",
    # height and plane likely don't have mobile apps
}

# Apple App Store (name slug + numeric ID)
APP_STORE_IDS = {
    "asana": {"name": "asana-work-in-one-place", "id": 489969512},
    "monday": {"name": "monday-com-work-management", "id": 1290128888},
    "clickup": {"name": "clickup-project-management", "id": 1436764971},
    "trello": {"name": "trello-organize-anything", "id": 461504587},
    "jira": {"name": "jira-cloud-by-atlassian", "id": 1475897096},
    "notion": {"name": "notion-notes-docs-ai", "id": 1232780281},
    "todoist": {"name": "todoist-to-do-list-planner", "id": 585829637},
    "basecamp": {"name": "basecamp-project-management", "id": 1015603248},
    "linear": {"name": "linear-plan-build-ship", "id": 1507926311},
    "airtable": {"name": "airtable", "id": 914172636},
    "wrike": {"name": "wrike-manage-projects-tasks", "id": 585098011},
    "smartsheet": {"name": "smartsheet", "id": 568421135},
    "teamwork": {"name": "teamwork-com-projects", "id": 726455070},
    "hive": {"name": "hive-manage-projects-tasks", "id": 1481106247},
    "taskade": {"name": "taskade-ai-productivity", "id": 1264713923},
    "ticktick": {"name": "ticktick-to-do-list-planner", "id": 626144601},
    # height, shortcut, plane, nifty may not have iOS apps
}


def scrape_play_store(app_key: str, package_id: str) -> list:
    """Fetch up to 200 Google Play reviews for the given package.

    Args:
        app_key: Short app identifier used only for error messages.
        package_id: Google Play package ID (e.g. ``"notion.id"``).

    Returns:
        List of review dicts with ``rating``, ``text``, ``thumbs_up``, and ``date``
        keys; empty list if scraping fails.
    """
    try:
        result, _ = gplay_reviews(
            package_id,
            lang='en',
            country='us',
            sort=Sort.MOST_RELEVANT,
            count=200,
        )
        reviews = []
        for r in result:
            reviews.append({
                "rating": r["score"],
                "text": r["content"],
                "thumbs_up": r["thumbsUpCount"],
                "date": r["at"].isoformat() if r.get("at") else None,
            })
        return reviews
    except Exception as e:
        print(f"    ⚠️  Play Store skip ({app_key}): {e}")
        return []


def scrape_app_store(app_key: str, app_info: dict) -> list:
    """Fetch up to 200 Apple App Store reviews for the given app.

    Args:
        app_key: Short app identifier used only for error messages.
        app_info: Dict with ``name`` (slug) and ``id`` (numeric) keys for the App Store.

    Returns:
        List of review dicts with ``rating``, ``title``, ``text``, and ``date``
        keys; empty list if scraping fails.
    """
    try:
        scraper = AppStore(
            country="us",
            app_name=app_info["name"],
            app_id=app_info["id"],
        )
        scraper.review(how_many=200)
        reviews = []
        for r in scraper.reviews:
            reviews.append({
                "rating": r.get("rating"),
                "title": r.get("title", ""),
                "text": r.get("review", ""),
                "date": r["date"].isoformat() if r.get("date") else None,
            })
        return reviews
    except Exception as e:
        print(f"    ⚠️  App Store skip ({app_key}): {e}")
        return []


if __name__ == "__main__":
    print("📱 App Store + Play Store Scraper — 20 PM Apps\n")
    
    all_apps = sorted(set(list(PLAY_STORE_IDS.keys()) + list(APP_STORE_IDS.keys())))
    total = 0
    
    for app_key in all_apps:
        print(f"\n  {app_key}...")
        combined = {"app": app_key, "play_store_reviews": [], "app_store_reviews": []}
        
        if app_key in PLAY_STORE_IDS:
            play = scrape_play_store(app_key, PLAY_STORE_IDS[app_key])
            combined["play_store_reviews"] = play
            print(f"    Play Store: {len(play)} reviews")
            total += len(play)
            time.sleep(1)
        
        if app_key in APP_STORE_IDS:
            ios = scrape_app_store(app_key, APP_STORE_IDS[app_key])
            combined["app_store_reviews"] = ios
            print(f"    App Store:  {len(ios)} reviews")
            total += len(ios)
            time.sleep(1)
        
        os.makedirs(f"data/{app_key}/reviews", exist_ok=True)
        with open(f"data/{app_key}/reviews/appstores.json", "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 DONE. Total app store reviews: {total}")
