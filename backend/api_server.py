"""
War Room — FastAPI server with WebSocket streaming.

Endpoints:
    POST /analyze — start a debate in a background thread; returns ``session_id``.
    WS /ws/{session_id} — stream one JSON message per completed round, then verdict or error.
    POST /api/ingest/video — optional walkthrough ingestion into ChromaDB (requires ffmpeg, OpenAI).
"""

from __future__ import annotations

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
from typing import Any, AsyncIterator, Callable

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

from .settings import API_HOST, API_PORT
from .debate_orchestrator import build_crew

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maps sequential round index (0-3) to the canonical agent_role slug.
ROUND_ROLES = ["first_timer", "daily_driver", "first_timer", "buyer"]

SESSIONS: dict[str, DebateSession] = {}
# In-memory store for video evidence produced by /api/ingest/video.
# Keyed by the upload session_id; consumed by /analyze via _run_debate.
VIDEO_EVIDENCE: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=4)

# ---------------------------------------------------------------------------
# Video pipeline — clients & constants
# ---------------------------------------------------------------------------

_openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))


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
# Session
# ---------------------------------------------------------------------------


class DebateSession:
    """Bridge between CrewAI task callbacks and WebSocket delivery for one debate run."""

    def __init__(
        self,
        session_id: str,
        product_description: str,
        loop: asyncio.AbstractEventLoop,
        upload_session_id: str = "",
        target_user: str = "",
        competitors: str = "",
        differentiator: str = "",
        product_stage: str = "",
    ) -> None:
        """Initialize a new debate session with product context and an async event loop.

        Args:
            session_id: Unique UUID for this debate run.
            product_description: Free-text product name and description.
            loop: Running asyncio event loop used for thread-safe queue puts.
            upload_session_id: Optional session UUID from a prior /api/ingest/video call.
            target_user: Who the product is for (from the wizard).
            competitors: Products it competes with.
            differentiator: Key competitive advantage claim.
            product_stage: Current development stage of the product.
        """
        self.session_id = session_id
        self.product_description = product_description
        self.loop = loop
        self.upload_session_id = upload_session_id  # ingest session from /api/ingest/video
        self.target_user = target_user
        self.competitors = competitors
        self.differentiator = differentiator
        self.product_stage = product_stage
        # Queue is the bridge between the background thread and the WebSocket coroutine.
        # None is the sentinel value that signals end-of-stream.
        self.queue: asyncio.Queue[dict | None] = asyncio.Queue()
        self._round_index = 0

    def build_task_callback(self) -> Callable[[Any], None]:
        """Return a CrewAI ``task_callback`` that enqueues round output for WebSocket delivery.

        Returns:
            A callable suitable for ``Crew(..., task_callback=...)``.
        """

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
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Shut down the thread pool when the app stops.

    Args:
        app: FastAPI application instance.

    Yields:
        Control back to FastAPI after startup.
    """
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
    """Request payload for POST /analyze."""

    product_description: str
    session_id: str = ""  # upload session_id from POST /api/ingest/video; empty string = no upload
    target_user: str = ""
    competitors: str = ""
    differentiator: str = ""
    product_stage: str = ""


class AnalyzeResponse(BaseModel):
    """Response payload from POST /analyze containing the new debate session UUID."""

    session_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Start a War Room debate for the given product and return a ``session_id``.

    The client should open ``WS /ws/{session_id}`` to receive streaming output
    as each of the four rounds completes.

    Args:
        request: Payload with ``product_description``.

    Returns:
        ``AnalyzeResponse`` containing the new session UUID.
    """
    session_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    session = DebateSession(
        session_id,
        request.product_description,
        loop,
        upload_session_id=request.session_id,
        target_user=request.target_user,
        competitors=request.competitors,
        differentiator=request.differentiator,
        product_stage=request.product_stage,
    )
    SESSIONS[session_id] = session

    # Fire-and-forget: the background thread enqueues messages as rounds complete.
    # The discarded future is intentional; errors are caught inside _run_debate.
    _ = loop.run_in_executor(_executor, _run_debate, session)

    return AnalyzeResponse(session_id=session_id)


@app.websocket("/ws/{session_id}")
async def websocket_debate(websocket: WebSocket, session_id: str) -> None:
    """Stream debate rounds to the client over WebSocket.

    Emits one JSON object per round (rounds 1–4), then a final verdict object.
    Closes after the verdict or on error.

    Args:
        websocket: Accepted WebSocket connection.
        session_id: UUID returned from ``POST /analyze``.

    Returns:
        None (connection closed in ``finally``).
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
    """Execute the full four-round crew in a thread-pool worker.

    CrewAI invokes ``task_callback`` after each sequential task, which enqueues
    the round result onto ``session.queue`` for the WebSocket to forward.

    Args:
        session: Active debate session with product text and event loop reference.
    """
    try:
        # Build session_context whenever there is founder context or a video upload.
        has_context = any([
            session.upload_session_id,
            session.target_user,
            session.competitors,
            session.differentiator,
            session.product_stage,
        ])
        session_context: dict[str, Any] | None = None
        if has_context:
            session_context = {
                "product_name": session.product_description,
                "target_user": session.target_user,
                "competitors": session.competitors,
                "differentiator": session.differentiator,
                "product_stage": session.product_stage,
            }
            if session.upload_session_id:
                session_context["session_id"] = session.upload_session_id
                video_evidence = VIDEO_EVIDENCE.get(session.upload_session_id)
                if video_evidence:
                    session_context["video_evidence"] = video_evidence

        crew = build_crew(
            session.product_description,
            task_callback=session.build_task_callback(),
            session_context=session_context,
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


def _parse_verdict(raw: str) -> dict[str, Any]:
    """Best-effort extraction of score, decision, and fixes from Round 4 text.

    Args:
        raw: Final crew output as a string.

    Returns:
        Dict with ``score``, ``decision``, ``top_3_fixes``, and ``full_report`` keys.
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
    """Log whether ffmpeg is available (required for video frame extraction).

    Returns:
        None
    """
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
    """Extract frames at scene changes (with fps fallback) for vision analysis.

    Args:
        video_path: Path to the uploaded video file.
        output_dir: Directory to write ``frame_*.jpg`` files.
        threshold: Scene-change sensitivity for ffmpeg ``select`` filter.

    Returns:
        Sorted list of frame paths (capped at 30 for cost control).
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
    """Send a single frame to GPT-4o Vision and return the assistant text.

    Args:
        frame_path: JPEG path on disk.
        prompt: Full user prompt including product and session context.

    Returns:
        Model response text (may be empty if the API returns no content).
    """
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
    session_context: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Analyze frames sequentially with rolling context for each vision call.

    Args:
        frames: Key frame image paths from ``extract_key_frames``.
        product_name: Product under evaluation.
        session_context: User profile fields and ``session_id`` for metadata.

    Returns:
        Tuple of (Chroma-ready chunk dicts, raw per-frame descriptions).
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
            product_description=session_context.get("product_description", "Unknown"),
            target_user=session_context.get("target_user", "Unknown"),
            competitors=session_context.get("competitors", "Unknown"),
            differentiator=session_context.get("differentiator", "Unknown"),
            product_stage=session_context.get("product_stage", "Unknown"),
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
    session_context: dict[str, Any],
) -> str:
    """Synthesize frame analyses into one journey report (text-only GPT-4o).

    Args:
        product_name: Product under evaluation.
        all_descriptions: Per-frame vision outputs in order.
        session_context: User profile fields for the prompt.

    Returns:
        Journey report string for ChromaDB and the debate.
    """
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


# ---------------------------------------------------------------------------
# Video ingestion — endpoint
# ---------------------------------------------------------------------------


@app.post("/api/ingest/video")
async def ingest_video(
    product_name: str = Form(...),
    file: UploadFile = File(...),
    product_description: str = Form(""),
    target_user: str = Form(""),
    competitors: str = Form(""),
    differentiator: str = Form(""),
    product_stage: str = Form(""),
) -> dict[str, Any]:
    """Ingest a walkthrough video: frame extraction, GPT-4o vision analysis, journey synthesis.

    Args:
        product_name: Product name from the landing page.
        file: Uploaded video file.
        product_description: What the product does (from wizard step 1).
        target_user: Who the product is for.
        competitors: Products it competes with.
        differentiator: Key competitive advantage.
        product_stage: Current stage of development.

    Returns:
        Session metadata, frame counts, and analyzed content.
    """
    session_id = str(uuid.uuid4())
    session_context = {
        "session_id": session_id,
        "product_description": product_description or "Unknown",
        "target_user": target_user or "Unknown",
        "competitors": competitors or "Unknown",
        "differentiator": differentiator or "Unknown",
        "product_stage": product_stage or "Unknown",
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

        # Store evidence in-memory so /analyze can inject it into agent prompts.
        frame_analyses = [chunk["text"] for chunk in frame_chunks]
        VIDEO_EVIDENCE[session_id] = {
            "journey_summary": journey_report,
            "frame_analyses": frame_analyses,
        }

        return {
            "session_id": session_id,
            "frames_extracted": frames_extracted,
            "key_frames_analyzed": frames_extracted,
            "journey_summary": journey_report,
            "frame_analyses": frame_analyses,
        }

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("backend.api_server:app", host=API_HOST, port=API_PORT, reload=True)
