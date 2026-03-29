"""
War Room — Video processing pipeline.

Handles walkthrough video ingestion: frame extraction via ffmpeg, per-frame
GPT-4o vision analysis (debate-oriented + UX matching), and journey report
synthesis.  Imported by server.py; no FastAPI dependencies here.
"""

from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path
from typing import Any

from openai import OpenAI

# ---------------------------------------------------------------------------
# OpenAI client (used for GPT-4o vision calls)
# ---------------------------------------------------------------------------

_openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

VIDEO_FRAME_PROMPT = """You are a product analyst watching a founder demo their product. This is frame {frame_number} of {total_frames} in their walkthrough.

PRODUCT BEING EVALUATED: {product_name}

PRODUCT CONTEXT:
- What it does: {product_description}
- Target user: {target_user}
- Competes with: {competitors}
- Key differentiator: {differentiator}
- Stage: {product_stage}

PREVIOUS SCREENS IN THIS SESSION:
{previous_screens_summary}

ANALYZE THIS FRAME:

1. SCREEN IDENTIFICATION: What exact screen/view/modal is shown?
2. PRODUCT JOURNEY MOMENT: What step are they demonstrating? (onboarding? core feature? edge case? stuck?)
3. WHAT JUST CHANGED: Compared to previous screens, what action was taken to get here?
4. FRICTION POINTS: What on this screen might confuse or frustrate the target user ({target_user})?
5. COMPARED TO COMPETITORS: How does this screen compare to doing the same thing in {competitors}?
6. EVIDENCE FOR DEBATE:
   - First-Timer perspective: Would a new user find this screen intuitive? Rate 1-10.
   - Daily Driver perspective: Would this screen hold up for power users of {competitors}? Rate 1-10.
   - Buyer perspective: Does this screen validate the differentiator claim "{differentiator}"? Rate 1-10.

Write 2-3 paragraphs of detailed analysis. Be specific about exact UI elements."""

UX_MATCH_PROMPT = """You are a senior UX analyst. Analyze this screenshot with EXTREME specificity.
Cover: 1) Screen ID (app, exact view), 2) Layout & visual hierarchy, 3) Every interactive element,
4) UX friction points (be brutal), 5) UX strengths, 6) Onboarding impact (cognitive load 1-10),
7) Competitor comparison. Write 4-6 detailed paragraphs. Be specific enough to reconstruct the screen."""

JOURNEY_SUMMARY_PROMPT = """You analyzed {total_frames} frames from a founder walking through {product_name}.

PRODUCT CONTEXT:
- What it does: {product_description}
- Target user: {target_user}
- Competes with: {competitors}
- Key differentiator: {differentiator}
- Stage: {product_stage}

FRAME-BY-FRAME ANALYSIS:
{all_frame_descriptions}

Now synthesize a JOURNEY REPORT:

1. PRODUCT EXPERIENCE: Rate the overall UX quality 1-10. Where does the product shine? Where does it struggle?

2. KEY FRICTION MOMENTS: The 3 worst moments in the walkthrough, ranked by severity. For each:
   - Which frame(s)
   - What went wrong
   - How {competitors} handles this better or worse

3. KEY STRENGTH MOMENTS: The 3 best moments where the product impressed or validated its differentiator.

4. COMPETITIVE POSITIONING: Based on this walkthrough, how well does {product_name} differentiate from {competitors} for {target_user}? Rate 1-10.

5. VERDICT PREVIEW: Based ONLY on what you saw in the video (not general knowledge), does this product deliver on its differentiator claim "{differentiator}"? YES/NO/CONDITIONAL — and why.

This journey report will be used as primary evidence in an adversarial product debate. Be specific and cite frame numbers."""


# ---------------------------------------------------------------------------
# ffmpeg availability check
# ---------------------------------------------------------------------------


def check_ffmpeg() -> None:
    """Log whether ffmpeg is available (required for video frame extraction)."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("ffmpeg found — video ingestion ready.")
    except FileNotFoundError:
        print(
            "WARNING: ffmpeg not found. Video ingestion will not work. "
            "Install: https://ffmpeg.org/download.html"
        )


# ---------------------------------------------------------------------------
# Frame extraction
# ---------------------------------------------------------------------------


def extract_key_frames(video_path: str, output_dir: str, threshold: float = 0.3) -> list[Path]:
    """Extract frames at scene changes (fps fallback if fewer than 5 found)."""
    frame_pattern = os.path.join(output_dir, "frame_%04d.jpg")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-frame_pts", "1",
        frame_pattern,
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    frames = sorted(Path(output_dir).glob("frame_*.jpg"))

    if len(frames) < 5:
        for f in frames:
            f.unlink(missing_ok=True)
        cmd_fallback = ["ffmpeg", "-i", video_path, "-vf", "fps=1/2", frame_pattern]
        subprocess.run(cmd_fallback, capture_output=True, text=True)
        frames = sorted(Path(output_dir).glob("frame_*.jpg"))

    if len(frames) > 10:
        step = len(frames) // 10
        frames = frames[::step][:10]

    return frames


# ---------------------------------------------------------------------------
# GPT-4o vision calls
# ---------------------------------------------------------------------------


def call_gpt4o_vision(frame_path: Path, prompt: str) -> str:
    """Send a single frame to GPT-4o Vision and return the assistant text."""
    with open(frame_path, "rb") as fh:
        image_b64 = base64.b64encode(fh.read()).decode("utf-8")

    response = _openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=1200,
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Multi-frame processing pipeline
# ---------------------------------------------------------------------------


def process_video_frames(
    frames: list[Path],
    product_name: str,
    session_context: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    list[str],
    list[dict[str, Any]],
]:
    """Analyze frames sequentially with rolling context for each vision call.

    Runs two GPT-4o passes per frame:
    1. VIDEO_FRAME_PROMPT — persona-aware analysis for debate injection.
    2. UX_MATCH_PROMPT — generic UX analysis for screenshot similarity matching.

    Returns:
        chunks: Debate-ready text chunks (debate_analysis per frame).
        all_descriptions: Debate analyses for journey summary generation.
        ux_frames: List of dicts with debate_analysis, ux_analysis, frame_number.
    """
    previous_screens: list[str] = []
    chunks: list[dict] = []
    all_descriptions: list[str] = []
    ux_frames: list[dict[str, Any]] = []
    session_id = session_context.get("session_id", "")

    for i, frame_path in enumerate(frames):
        previous_summary = (
            "\n".join(previous_screens[-5:])
            if previous_screens
            else "This is the first screen in the session."
        )

        debate_prompt = VIDEO_FRAME_PROMPT.format(
            frame_number=i + 1,
            total_frames=len(frames),
            product_name=product_name,
            product_description=session_context.get("product_description", "Unknown"),
            target_user=session_context.get("target_user", "Unknown"),
            competitors=session_context.get("competitors", "Unknown"),
            differentiator=session_context.get("differentiator", "Unknown"),
            product_stage=session_context.get("product_stage", "Unknown"),
            previous_screens_summary=previous_summary,
        )
        description = call_gpt4o_vision(frame_path, debate_prompt)
        all_descriptions.append(description)
        previous_screens.append(f"Frame {i + 1}: {description[:150]}...")

        ux_analysis = ""
        try:
            ux_analysis = call_gpt4o_vision(
                frame_path,
                f"This is a screenshot of a product.\n\n{UX_MATCH_PROMPT}",
            )
        except Exception as exc:
            print(f"   WARNING: UX match analysis failed for frame {i + 1}: {exc}")

        chunks.append(
            {
                "text": f"[Video Frame {i + 1}/{len(frames)}: {product_name}]\n\n{description}",
                "metadata": {
                    "app": product_name.lower().split()[0],
                    "source": "user_upload",
                    "type": "video_frame",
                    "frame_number": i + 1,
                    "total_frames": len(frames),
                    "session_id": session_id,
                },
            }
        )
        ux_frames.append(
            {
                "frame_number": i + 1,
                "image_path": f"sessions/{session_id}/frames/{frame_path.name}",
                "debate_analysis": description,
                "ux_analysis": ux_analysis,
            }
        )

    return chunks, all_descriptions, ux_frames


# ---------------------------------------------------------------------------
# Journey synthesis
# ---------------------------------------------------------------------------


def generate_journey_summary(
    product_name: str,
    all_descriptions: list[str],
    session_context: dict[str, Any],
) -> str:
    """Synthesize frame analyses into one journey report via GPT-4o."""
    numbered = "\n\n".join(
        f"Frame {i + 1}:\n{desc}" for i, desc in enumerate(all_descriptions)
    )
    prompt = JOURNEY_SUMMARY_PROMPT.format(
        total_frames=len(all_descriptions),
        product_name=product_name,
        product_description=session_context.get("product_description", "Unknown"),
        target_user=session_context.get("target_user", "Unknown"),
        competitors=session_context.get("competitors", "Unknown"),
        differentiator=session_context.get("differentiator", "Unknown"),
        product_stage=session_context.get("product_stage", "Unknown"),
        all_frame_descriptions=numbered,
    )
    response = _openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )
    return response.choices[0].message.content or ""
