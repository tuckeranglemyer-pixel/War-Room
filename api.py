"""
War Room — FastAPI server with WebSocket streaming.

Flow:
  POST /analyze       → starts a debate session in a background thread, returns session_id
  WS   /ws/{id}       → streams one JSON message per round as it completes, then a verdict
"""

import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

from crew import build_crew
from tools import _chroma_client

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maps sequential round index (0-3) to the canonical agent_role slug
ROUND_ROLES = ["first_timer", "daily_driver", "first_timer", "buyer"]

SESSIONS: dict[str, "DebateSession"] = {}
_executor = ThreadPoolExecutor(max_workers=4)

# ---------------------------------------------------------------------------
# Video pipeline — clients & constants
# ---------------------------------------------------------------------------

_openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# Lazy reference — resolved at first use so a missing collection doesn't crash import.
_pm_tools_collection = None

VIDEO_FRAME_PROMPT = """You are a UX researcher watching a user navigate a product for the first time. This is frame {frame_number} of {total_frames} in their session.

PRODUCT BEING EVALUATED: {product_name}

USER PROFILE:
- Team size: {team_size}
- Current tools: {current_tools}
- Budget: {budget}
- Main problem they're trying to solve: {main_problem}
- What they want to use this product for: {use_case}

PREVIOUS SCREENS IN THIS SESSION:
{previous_screens_summary}

ANALYZE THIS FRAME:

1. SCREEN IDENTIFICATION: What exact screen/view/modal is the user on?
2. USER JOURNEY MOMENT: What step are they at? (onboarding? exploring? configuring? stuck?)
3. WHAT JUST CHANGED: Compared to previous screens, what action did the user take to get here?
4. FRICTION POINTS: What on this screen would confuse THIS specific user (given their profile)?
5. COMPARED TO THEIR CURRENT TOOLS: How does this screen compare to doing the same thing in {current_tools}?
6. EVIDENCE FOR DEBATE:
   - First-Timer perspective: Would a new user find this screen intuitive? Rate 1-10.
   - Daily Driver perspective: Would this screen hold up after months of daily use? Rate 1-10.
   - Buyer perspective: Does this screen suggest the product can scale to a {team_size}-person team? Rate 1-10.

Write 2-3 paragraphs of detailed analysis. Be specific about exact UI elements."""

JOURNEY_SUMMARY_PROMPT = """You analyzed {total_frames} frames from a user walking through {product_name} for the first time.

USER PROFILE:
- Team: {team_size} people, currently using {current_tools}
- Budget: {budget}
- Problem: {main_problem}
- Use case: {use_case}

FRAME-BY-FRAME ANALYSIS:
{all_frame_descriptions}

Now synthesize a JOURNEY REPORT:

1. ONBOARDING FLOW: Rate the overall first-time experience 1-10. Where did the user get stuck? Where did it flow well?

2. KEY FRICTION MOMENTS: The 3 worst moments in the journey, ranked by severity. For each:
   - Which frame(s)
   - What went wrong
   - How {current_tools} handles this better or worse

3. KEY STRENGTH MOMENTS: The 3 best moments where the product impressed.

4. MIGRATION ASSESSMENT: Based on this walkthrough, how painful would it be for a {team_size}-person team to migrate from {current_tools} to {product_name}? Rate 1-10.

5. VERDICT PREVIEW: Based ONLY on what you saw in the video (not general knowledge), would you recommend this product for this user's specific situation? YES/NO/CONDITIONAL — and why.

This journey report will be used as primary evidence in an adversarial product debate. Be specific and cite frame numbers."""


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class DebateSession:
    """Holds the async queue and loop reference for one debate run."""

    def __init__(
        self,
        session_id: str,
        product_description: str,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.session_id = session_id
        self.product_description = product_description
        self.loop = loop
        # Queue is the bridge between the background thread and the WebSocket coroutine.
        # None is the sentinel value that signals end-of-stream.
        self.queue: asyncio.Queue[dict | None] = asyncio.Queue()
        self._round_index = 0

    def build_task_callback(self):
        """Return a CrewAI task_callback that enqueues round output for WebSocket delivery."""

        def callback(task_output: Any) -> None:
            round_num = self._round_index + 1
            agent_role = (
                ROUND_ROLES[self._round_index]
                if self._round_index < len(ROUND_ROLES)
                else "unknown"
            )
            self._round_index += 1

            message: dict = {
                "round": round_num,
                "agent_name": task_output.agent,
                "agent_role": agent_role,
                "model": "mistral:7b",
                "status": "complete",
                "content": task_output.raw,
            }
            asyncio.run_coroutine_threadsafe(self.queue.put(message), self.loop)

        return callback


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    _executor.shutdown(wait=False)


app = FastAPI(title="War Room API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    product_description: str


class AnalyzeResponse(BaseModel):
    session_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Start a War Room debate for the given product and return a session_id.

    The client should immediately open WS /ws/{session_id} to receive
    streaming output as each of the 4 rounds completes.
    """
    session_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    session = DebateSession(session_id, request.product_description, loop)
    SESSIONS[session_id] = session

    # Fire-and-forget: the background thread enqueues messages as rounds complete.
    # The discarded future is intentional; errors are caught inside _run_debate.
    _ = loop.run_in_executor(_executor, _run_debate, session)

    return AnalyzeResponse(session_id=session_id)


@app.websocket("/ws/{session_id}")
async def websocket_debate(websocket: WebSocket, session_id: str) -> None:
    """
    Stream debate rounds to the client.

    Emits one JSON object per round (rounds 1-4), then a final verdict object.
    Closes after the verdict or on error.
    """
    await websocket.accept()

    session = SESSIONS.get(session_id)
    if session is None:
        await websocket.send_text(
            json.dumps({"type": "error", "message": "Session not found"})
        )
        await websocket.close()
        return

    try:
        while True:
            message = await session.queue.get()
            if message is None:  # end-of-stream sentinel
                break
            await websocket.send_text(json.dumps(message))
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
        SESSIONS.pop(session_id, None)


# ---------------------------------------------------------------------------
# Background debate runner
# ---------------------------------------------------------------------------


def _run_debate(session: DebateSession) -> None:
    """
    Execute the full 4-round crew synchronously inside a thread-pool worker.

    CrewAI calls task_callback after each sequential task, which enqueues
    the round result onto session.queue for the WebSocket to forward.
    """
    try:
        crew = build_crew(
            session.product_description,
            task_callback=session.build_task_callback(),
        )
        result = crew.kickoff()

        verdict = _parse_verdict(str(result))
        asyncio.run_coroutine_threadsafe(
            session.queue.put({"type": "verdict", **verdict}),
            session.loop,
        )
    except Exception as exc:
        asyncio.run_coroutine_threadsafe(
            session.queue.put({"type": "error", "message": str(exc)}),
            session.loop,
        )
    finally:
        # Always send the sentinel so the WebSocket loop exits cleanly.
        asyncio.run_coroutine_threadsafe(session.queue.put(None), session.loop)


# ---------------------------------------------------------------------------
# Verdict parser
# ---------------------------------------------------------------------------


def _parse_verdict(raw: str) -> dict:
    """
    Best-effort extraction of structured fields from Round 4's raw text output.

    Falls back gracefully when the LLM doesn't follow the expected format.
    """
    # Score: integer 1-100 followed by "/100" or "out of 100" or "score"
    score_match = re.search(
        r"\b([1-9][0-9]?|100)\b(?=\s*(?:/100|out of 100|score))",
        raw,
        re.IGNORECASE,
    )
    score = int(score_match.group(1)) if score_match else 0

    # Decision: prefer the most specific match first
    decision = "UNKNOWN"
    for candidate in ("YES WITH CONDITIONS", "YES", "NO"):
        if candidate in raw.upper():
            decision = candidate
            break

    # Top 3 fixes: numbered list items under a "TOP 3 FIXES" header
    fixes: list[str] = []
    fixes_section = re.search(
        r"TOP 3 FIXES[:\s]*(.*?)(?:\n\n|\Z)",
        raw,
        re.IGNORECASE | re.DOTALL,
    )
    if fixes_section:
        items = re.findall(
            r"(?:^|\n)\s*\d+[.)]\s+(.+?)(?=\n\s*\d+[.)]|\Z)",
            fixes_section.group(1),
            re.DOTALL,
        )
        fixes = [item.strip() for item in items[:3]]
    if not fixes:
        fixes = ["See full report for recommended fixes."]

    return {
        "score": score,
        "decision": decision,
        "top_3_fixes": fixes,
        "full_report": raw,
    }


# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------


@app.on_event("startup")
def check_ffmpeg() -> None:
    """Warn at startup if ffmpeg is missing — video ingestion requires it."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("ffmpeg found — video ingestion ready.")
    except FileNotFoundError:
        print(
            "WARNING: ffmpeg not found. Video ingestion will not work. "
            "Install: https://ffmpeg.org/download.html"
        )


# ---------------------------------------------------------------------------
# Video ingestion — frame extraction
# ---------------------------------------------------------------------------


def extract_key_frames(video_path: str, output_dir: str, threshold: float = 0.3) -> list[Path]:
    """Extract frames at scene changes so we capture transitions, modals, and new views.

    Falls back to 0.5 fps sampling when scene detection yields fewer than 5 frames.
    Caps output at 30 frames to control downstream API costs.
    """
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
        # Wipe partial results before the fallback run.
        for f in frames:
            f.unlink(missing_ok=True)
        cmd_fallback = [
            "ffmpeg", "-i", video_path,
            "-vf", "fps=1/2",
            frame_pattern,
        ]
        subprocess.run(cmd_fallback, capture_output=True, text=True)
        frames = sorted(Path(output_dir).glob("frame_*.jpg"))

    if len(frames) > 30:
        step = len(frames) // 30
        frames = frames[::step][:30]

    return frames


# ---------------------------------------------------------------------------
# Video ingestion — GPT-4o Vision helpers
# ---------------------------------------------------------------------------


def call_gpt4o_vision(frame_path: Path, prompt: str) -> str:
    """Send a single frame to GPT-4o Vision and return the text description."""
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


def process_video_frames(
    frames: list[Path],
    product_name: str,
    session_context: dict,
) -> tuple[list[dict], list[str]]:
    """Analyze frames sequentially so each prompt includes a running narrative of prior screens.

    Returns:
        chunks: list of dicts ready for ChromaDB insertion (text + metadata).
        all_descriptions: raw description strings, used later for the journey summary.
    """
    previous_screens: list[str] = []
    chunks: list[dict] = []
    all_descriptions: list[str] = []

    session_id = session_context.get("session_id", "")

    for i, frame_path in enumerate(frames):
        previous_summary = (
            "\n".join(previous_screens[-5:])
            if previous_screens
            else "This is the first screen in the session."
        )

        prompt = VIDEO_FRAME_PROMPT.format(
            frame_number=i + 1,
            total_frames=len(frames),
            product_name=product_name,
            team_size=session_context.get("team_size", "Unknown"),
            current_tools=session_context.get("current_tools", "Unknown"),
            budget=session_context.get("budget", "Unknown"),
            main_problem=session_context.get("main_problem", "Unknown"),
            use_case=session_context.get("use_case", "Unknown"),
            previous_screens_summary=previous_summary,
        )

        description = call_gpt4o_vision(frame_path, prompt)
        all_descriptions.append(description)

        # Keep only the first 150 chars in the running summary to stay within token budgets.
        previous_screens.append(f"Frame {i + 1}: {description[:150]}...")

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

    return chunks, all_descriptions


def generate_journey_summary(
    product_name: str,
    all_descriptions: list[str],
    session_context: dict,
) -> str:
    """Synthesize the full session into a single journey report via a text-only GPT-4o call."""
    numbered = "\n\n".join(
        f"Frame {i + 1}:\n{desc}" for i, desc in enumerate(all_descriptions)
    )

    prompt = JOURNEY_SUMMARY_PROMPT.format(
        total_frames=len(all_descriptions),
        product_name=product_name,
        team_size=session_context.get("team_size", "Unknown"),
        current_tools=session_context.get("current_tools", "Unknown"),
        budget=session_context.get("budget", "Unknown"),
        main_problem=session_context.get("main_problem", "Unknown"),
        use_case=session_context.get("use_case", "Unknown"),
        all_frame_descriptions=numbered,
    )

    response = _openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )
    return response.choices[0].message.content or ""


def _get_pm_tools_collection():
    """Return the pm_tools ChromaDB collection, initializing the module-level cache on first call."""
    global _pm_tools_collection
    if _pm_tools_collection is None:
        try:
            _pm_tools_collection = _chroma_client.get_collection("pm_tools")
        except Exception as exc:
            raise RuntimeError(f"Could not open pm_tools ChromaDB collection: {exc}") from exc
    return _pm_tools_collection


# ---------------------------------------------------------------------------
# Video ingestion — endpoint
# ---------------------------------------------------------------------------


@app.post("/api/ingest/video")
async def ingest_video(
    product_name: str = Form(...),
    file: UploadFile = File(...),
    team_size: str = Form(""),
    current_tools: str = Form(""),
    budget: str = Form(""),
    main_problem: str = Form(""),
    use_case: str = Form(""),
) -> dict:
    """Accept a product walkthrough video, extract key frames via scene-change detection,
    analyze each frame with GPT-4o Vision in narrative sequence, generate a journey summary,
    and embed all evidence into the pm_tools ChromaDB collection.

    Returns session metadata and counts for the frontend to display.
    """
    session_id = str(uuid.uuid4())
    session_context = {
        "session_id": session_id,
        "team_size": team_size or "Unknown",
        "current_tools": current_tools or "Unknown",
        "budget": budget or "Unknown",
        "main_problem": main_problem or "Unknown",
        "use_case": use_case or "Unknown",
    }

    tmp_dir = tempfile.mkdtemp(prefix="warroom_video_")
    try:
        # Persist upload to disk so ffmpeg can read it.
        video_suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
        video_path = os.path.join(tmp_dir, f"input{video_suffix}")
        with open(video_path, "wb") as fh:
            shutil.copyfileobj(file.file, fh)

        frames_dir = os.path.join(tmp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)

        frames = extract_key_frames(video_path, frames_dir)
        frames_extracted = len(frames)

        if frames_extracted == 0:
            return {
                "session_id": session_id,
                "error": "No frames could be extracted. Verify the video file and that ffmpeg is installed.",
                "frames_extracted": 0,
                "key_frames_analyzed": 0,
                "chunks_added": 0,
            }

        # Sequential frame analysis with rolling narrative context.
        frame_chunks, all_descriptions = process_video_frames(
            frames, product_name, session_context
        )

        # Full-session journey synthesis.
        journey_report = generate_journey_summary(
            product_name, all_descriptions, session_context
        )
        journey_chunk = {
            "text": f"[Journey Summary: {product_name} — Session {session_id}]\n\n{journey_report}",
            "metadata": {
                "app": product_name.lower().split()[0],
                "source": "user_upload",
                "type": "journey_summary",
                "session_id": session_id,
                "total_frames": frames_extracted,
            },
        }

        all_chunks = frame_chunks + [journey_chunk]

        # Embed everything into ChromaDB.
        collection = _get_pm_tools_collection()
        for idx, chunk in enumerate(all_chunks):
            doc_id = f"video_{session_id}_chunk_{idx:04d}"
            collection.add(
                documents=[chunk["text"]],
                metadatas=[chunk["metadata"]],
                ids=[doc_id],
            )

        return {
            "session_id": session_id,
            "frames_extracted": frames_extracted,
            "key_frames_analyzed": frames_extracted,
            "chunks_added": len(all_chunks),
            "total_collection": collection.count(),
        }

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
