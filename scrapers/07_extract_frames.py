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


def extract_scene_frames(video_path: str, output_dir: str, threshold: float = 0.3) -> int:
    """Extract frames at scene-change boundaries using ffmpeg's scene filter.

    Args:
        video_path: Absolute or relative path to the source video file.
        output_dir: Directory where extracted ``frame_*.jpg`` files are written.
        threshold: Scene-change sensitivity (0.0–1.0); lower values produce more frames.

    Returns:
        Number of frame images written to ``output_dir``.
    """
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr", "-q:v", "2",
        f"{output_dir}/frame_%04d.jpg", "-y",
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return len(glob.glob(f"{output_dir}/frame_*.jpg"))


def extract_uniform_frames(video_path: str, output_dir: str, interval: int = 3) -> int:
    """Extract one frame every ``interval`` seconds using ffmpeg's fps filter.

    Used as a fallback when scene-change detection yields fewer than 5 frames.

    Args:
        video_path: Absolute or relative path to the source video file.
        output_dir: Directory where extracted ``frame_*.jpg`` files are written.
        interval: Seconds between sampled frames (default: one frame every 3 s).

    Returns:
        Number of frame images written to ``output_dir``.
    """
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps=1/{interval}", "-q:v", "2",
        f"{output_dir}/frame_%04d.jpg", "-y",
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return len(glob.glob(f"{output_dir}/frame_*.jpg"))


def get_duration(video_path: str) -> float:
    """Return the duration of a video file in seconds via ffprobe.

    Args:
        video_path: Absolute or relative path to the video file.

    Returns:
        Duration as a float (seconds), or 0.0 if ffprobe fails or returns no data.
    """
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
