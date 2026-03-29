"""
YouTube Product Tour Downloader — 20 PM Apps
==============================================
STEP 1: Run this script with empty URLs → it prints YouTube search links
STEP 2: Open each link, find a 3-8 min product tour, copy URL
STEP 3: Paste URLs into VIDEOS dict below
STEP 4: Run again to download

pip install yt-dlp
"""

import subprocess
import os

# ============================================================
# PASTE VIDEO URLs HERE AS YOU FIND THEM
# ============================================================
VIDEOS = {
    "asana": [],
    "monday": [],
    "clickup": [],
    "trello": [],
    "jira": [],
    "notion": [],
    "todoist": [],
    "basecamp": [],
    "linear": [],
    "airtable": [],
    "wrike": [],
    "smartsheet": [],
    "teamwork": [],
    "hive": [],
    "height": [],
    "shortcut": [],
    "plane": [],
    "taskade": [],
    "nifty": [],
    "ticktick": [],
}

SEARCH_QUERIES = {
    "asana": "Asana product tour demo 2024",
    "monday": "Monday.com product tour demo 2024",
    "clickup": "ClickUp 3.0 product tour demo",
    "trello": "Trello demo walkthrough 2024",
    "jira": "Jira software demo walkthrough 2024",
    "notion": "Notion product tour walkthrough 2024",
    "todoist": "Todoist app tour demo 2024",
    "basecamp": "Basecamp product tour demo",
    "linear": "Linear app demo walkthrough",
    "airtable": "Airtable demo walkthrough 2024",
    "wrike": "Wrike product tour demo 2024",
    "smartsheet": "Smartsheet demo walkthrough 2024",
    "teamwork": "Teamwork.com product tour demo",
    "hive": "Hive project management demo 2024",
    "height": "Height app demo product tour",
    "shortcut": "Shortcut project management demo",
    "plane": "Plane.so demo product tour",
    "taskade": "Taskade demo walkthrough 2024",
    "nifty": "Nifty PM demo product tour",
    "ticktick": "TickTick app tour demo 2024",
}


def download_video(app_key: str, url: str, index: int = 0) -> None:
    """Download a single YouTube product tour video via yt-dlp.

    Saves the video as an MP4 at ``data/{app_key}/videos/{app_key}_tour_{index}.mp4``.
    Prefers the best 1080p-or-lower MP4+M4A stream combination; falls back to best
    available if that muxed format is unavailable.

    Args:
        app_key: Short app identifier used to name the output directory and file.
        url: Full YouTube video URL to download.
        index: Zero-based index appended to the output filename to avoid overwrites
            when multiple videos are downloaded for the same app.
    """
    output_dir = f"data/{app_key}/videos"
    os.makedirs(output_dir, exist_ok=True)
    output_template = f"{output_dir}/{app_key}_tour_{index}.%(ext)s"
    
    cmd = [
        "yt-dlp",
        "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", output_template,
        "--no-playlist",
        url,
    ]
    
    print(f"  ⬇️  {url}")
    try:
        subprocess.run(cmd, check=True)
        print(f"  ✅ Saved → {output_dir}/")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed: {e}")
    except FileNotFoundError:
        print("  ❌ yt-dlp not found. Run: pip install yt-dlp")


if __name__ == "__main__":
    total_urls = sum(len(urls) for urls in VIDEOS.values())
    
    if total_urls == 0:
        print("📺 YouTube Product Tour Downloader")
        print("   No URLs yet. Here are your search links:\n")
        for app_key, query in SEARCH_QUERIES.items():
            url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            print(f"  {app_key:15s} → {url}")
        print(f"\n   Open each link, find a good 3-8 min tour,")
        print(f"   copy the URL, paste into VIDEOS dict above, run again.")
    else:
        print(f"📺 Downloading {total_urls} videos...\n")
        for app_key, urls in VIDEOS.items():
            for i, url in enumerate(urls):
                download_video(app_key, url, i)
        
        missing = [k for k, v in VIDEOS.items() if not v]
        if missing:
            print(f"\n⚠️  Still need: {', '.join(missing)}")
        print(f"\n🎉 DONE.")
