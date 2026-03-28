"""
Video Frame Extractor
=====================
Extracts key frames from downloaded product tour videos using ffmpeg scene detection.
Run AFTER 05_download_videos.py.

Requires: ffmpeg installed (brew install ffmpeg / apt install ffmpeg)
"""

import subprocess
import os
import json
import glob


def extract_scene_frames(video_path, output_dir, threshold=0.3):
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr", "-q:v", "2",
        f"{output_dir}/frame_%04d.jpg", "-y",
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return len(glob.glob(f"{output_dir}/frame_*.jpg"))


def extract_uniform_frames(video_path, output_dir, interval=3):
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps=1/{interval}", "-q:v", "2",
        f"{output_dir}/frame_%04d.jpg", "-y",
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return len(glob.glob(f"{output_dir}/frame_*.jpg"))


def get_duration(video_path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(json.loads(result.stdout).get("format", {}).get("duration", 0))
    except:
        return 0


if __name__ == "__main__":
    print("🎬 Video Frame Extractor\n")
    total = 0
    
    for app_dir in sorted(glob.glob("data/*/videos")):
        app_key = app_dir.split("/")[1]
        videos = glob.glob(f"{app_dir}/*.mp4") + glob.glob(f"{app_dir}/*.webm") + glob.glob(f"{app_dir}/*.mkv")
        if not videos:
            continue
        
        print(f"  {app_key}...")
        for video_path in videos:
            name = os.path.splitext(os.path.basename(video_path))[0]
            out = f"data/{app_key}/video_frames/{name}"
            dur = get_duration(video_path)
            
            n = extract_scene_frames(video_path, out, 0.3)
            if n < 5 and dur > 30:
                n = extract_uniform_frames(video_path, out, 3)
            if n > 100:
                n = extract_scene_frames(video_path, out, 0.5)
            
            # Save manifest
            frames = sorted(glob.glob(f"{out}/frame_*.jpg"))
            with open(f"{out}/manifest.json", "w") as f:
                json.dump({"video": video_path, "duration": dur, "frames": [os.path.basename(x) for x in frames]}, f, indent=2)
            
            print(f"    {n} frames → {out}/")
            total += n
    
    print(f"\n🎉 DONE. {total} total frames extracted.")
