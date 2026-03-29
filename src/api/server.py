# War Room API — FastAPI + WebSocket + SSE streaming server
"""
War Room — FastAPI server with WebSocket streaming.

Endpoints:
    POST /analyze        — start a debate in a background thread; returns session_id
    WS   /ws/{session_id} — stream one JSON message per completed round, then verdict or error
    POST /api/ingest/video — walkthrough video ingestion into ChromaDB (requires ffmpeg + OpenAI)

The DebateSession class bridges CrewAI task callbacks and WebSocket delivery.
The background thread calls session.build_task_callback() which enqueues
each round result; the WebSocket coroutine drains the queue in real time.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import shutil
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Callable

import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.api.video_processor import (
    check_ffmpeg,
    extract_key_frames,
    generate_journey_summary,
    process_video_frames,
)
from src.inference.model_config import (
    API_HOST,
    API_PORT,
    BUYER_MODEL,
    DAILY_DRIVER_MODEL,
    FALLBACK_MODEL,
    FIRST_TIMER_MODEL,
)
import src.config as _cfg
from src.orchestration.adaptive_runner import AdaptiveRunner
from src.orchestration.adversarial_debate_engine import build_crew
from src.orchestration.response_synthesizer import parse_verdict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_log = logging.getLogger(__name__)

ROUND_ROLES = ["first_timer", "daily_driver", "first_timer", "buyer"]

ROLE_MODELS: dict[str, str] = {
    "first_timer": FIRST_TIMER_MODEL,
    "daily_driver": DAILY_DRIVER_MODEL,
    "buyer": BUYER_MODEL,
}

# Persistent directory for session frames — created once at module load so static mount works.
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

SESSIONS: dict[str, DebateSession] = {}
VIDEO_EVIDENCE: dict[str, dict] = {}
ANALYSIS_STATUS: dict[str, str] = {}  # session_id → "pending" | "complete" | "failed"
_executor = ThreadPoolExecutor(max_workers=4)

# Per-session log buffers for SSE streaming — list buffers past messages so a late-connecting
# client replays them; async queues deliver to an active SSE subscriber in real time.
_analysis_log_buffers: dict[str, list[str]] = {}
_analysis_log_queues: dict[str, asyncio.Queue[str | None]] = {}


async def _push_analysis_log(session_id: str, analyst: str, message: str) -> None:
    """Buffer a log line and deliver it to any active SSE subscriber for this session."""
    entry = json.dumps({"analyst": analyst, "message": message})
    _analysis_log_buffers.setdefault(session_id, []).append(entry)
    if session_id in _analysis_log_queues:
        await _analysis_log_queues[session_id].put(entry)

_rate_limits: defaultdict[str, list[float]] = defaultdict(list)

# Products with real evidence in ChromaDB — all other submissions are rejected.
SUPPORTED_PRODUCTS = [
    "notion", "asana", "clickup", "monday", "linear",
    "todoist", "trello", "jira", "basecamp", "airtable",
    "google calendar", "obsidian", "evernote", "roam research",
    "coda", "confluence", "teamwork", "wrike", "smartsheet", "height",
]


def is_supported_product(name: str) -> bool:
    """Return True if *name* fuzzy-matches any entry in SUPPORTED_PRODUCTS (case-insensitive)."""
    normalized = name.strip().lower()
    return any(normalized == p or p in normalized or normalized in p for p in SUPPORTED_PRODUCTS)


# ---------------------------------------------------------------------------
# Daily budget guard — circuit breaker for runaway API costs
# ---------------------------------------------------------------------------

MAX_DAILY_ANALYSES = 100
_daily_analysis_count = 0
_daily_reset_time = time.time()


def check_budget_guard() -> bool:
    """Increment the daily analysis counter and return True if budget is still available.

    Resets the counter automatically after 24 hours. Returns False when the
    daily cap is reached, signalling the caller to serve demo fallback instead
    of running real inference.
    """
    global _daily_analysis_count, _daily_reset_time
    if time.time() - _daily_reset_time > 86400:
        _daily_analysis_count = 0
        _daily_reset_time = time.time()
    if _daily_analysis_count >= MAX_DAILY_ANALYSES:
        return False
    _daily_analysis_count += 1
    return True


def check_rate_limit(ip: str, max_requests: int = 3, window: int = 3600) -> bool:
    """Per-IP rate limiter — defaults to 3 analysis requests per hour for public launch."""
    now = time.time()
    _rate_limits[ip] = [t for t in _rate_limits[ip] if now - t < window]
    if len(_rate_limits[ip]) >= max_requests:
        return False
    _rate_limits[ip].append(now)
    return True


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
        product_name: str = "",
        upload_session_id: str = "",
        target_user: str = "",
        competitors: str = "",
        differentiator: str = "",
        product_stage: str = "",
        evidence_tier: str = "full",
    ) -> None:
        """Initialize a debate session and its inter-thread communication queue."""
        self.session_id = session_id
        self.product_description = product_description
        self.product_name = product_name
        self.loop = loop
        self.upload_session_id = upload_session_id
        self.target_user = target_user
        self.competitors = competitors
        self.differentiator = differentiator
        self.product_stage = product_stage
        self.evidence_tier = evidence_tier
        self.queue: asyncio.Queue[dict | None] = asyncio.Queue()
        self._round_index = 0

    def build_task_callback(self) -> Callable[[Any], None]:
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
                "model": ROLE_MODELS.get(agent_role, FALLBACK_MODEL),
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
    """Run ffmpeg check at startup; shut down the thread pool on exit."""
    check_ffmpeg()
    yield
    _executor.shutdown(wait=False)


app = FastAPI(
    title="War Room API",
    description=(
        "Adversarial multi-agent product QA: `POST /analyze` returns a `session_id`; "
        "open `WS /ws/{session_id}` for round-by-round JSON. "
        "**Interactive docs:** [/docs](/docs) (Swagger UI), [/redoc](/redoc)."
    ),
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "meta", "description": "Health and API discovery."},
        {"name": "debate", "description": "CrewAI debate pipeline and streaming."},
        {"name": "video", "description": "Video frame extraction and vision analysis."},
        {"name": "analysis", "description": "Parallel 3-model analysis pipeline and report delivery."},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve user session frames: GET /sessions/{session_id}/frames/frame_NNNN.jpg
app.mount("/sessions", StaticFiles(directory=str(SESSIONS_DIR)), name="sessions")

# Serve competitor screenshots: GET /data/{app}/screenshots/{filename}
# Only mounted when the data/ directory exists (may be absent during local dev).
_DATA_DIR = Path("data")
if _DATA_DIR.exists():
    app.mount("/data", StaticFiles(directory=str(_DATA_DIR)), name="screenshots")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """Request payload for POST /analyze."""

    product_description: str
    product_name: str = ""
    session_id: str = ""
    target_user: str = ""
    competitors: str = ""
    differentiator: str = ""
    product_stage: str = ""


class AnalyzeResponse(BaseModel):
    """Response payload from POST /analyze containing the new debate session UUID."""

    session_id: str
    demo_mode: bool = False
    message: str = ""
    evidence_tier: str = "full"  # "full" = RAG-grounded, "general" = model knowledge only


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    """API discovery — links to OpenAPI UIs (judges often check ``/docs``)."""
    return {
        "service": "war-room",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi_json": "/openapi.json",
    }


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness probe for orchestrators and hackathon demos."""
    return {"status": "ok", "service": "war-room-api"}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["debate"])
async def analyze(http_request: Request, body: AnalyzeRequest) -> AnalyzeResponse:
    """Start a War Room debate for the given product and return a session_id."""
    try:
        client_ip = http_request.client.host if http_request.client else "unknown"
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Rate limit reached: 3 analyses per IP per hour. Try again later.",
            )

        effective_name = (body.product_name or body.product_description).strip()
        evidence_tier = "full" if is_supported_product(effective_name) else "general"

    if not check_budget_guard():
        return AnalyzeResponse(
            session_id="",
            demo_mode=True,
            message="High demand — showing demo analysis. Full analyses resume shortly.",
            evidence_tier=evidence_tier,
        )

    session_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    try:
        session = DebateSession(
            session_id,
            body.product_description,
            loop,
            product_name=body.product_name,
            upload_session_id=body.session_id,
            target_user=body.target_user,
            competitors=body.competitors,
            differentiator=body.differentiator,
            product_stage=body.product_stage,
            evidence_tier=evidence_tier,
        )
        SESSIONS[session_id] = session
        _ = loop.run_in_executor(_executor, _run_debate, session)
        return AnalyzeResponse(session_id=session_id, evidence_tier=evidence_tier)
    except Exception as exc:
        SESSIONS.pop(session_id, None)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start debate session: {exc}",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _log.exception("POST /analyze failed")
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc


@app.websocket("/ws/{session_id}")
async def websocket_debate(websocket: WebSocket, session_id: str) -> None:
    """Stream debate rounds to the client over WebSocket."""
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
            if message is None:
                break
            await websocket.send_text(json.dumps(message))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # pragma: no cover — defensive; client may drop mid-send
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "message": f"Stream error: {exc}"})
            )
        except Exception as e:
            _log.error(f"Error: {e}")
    finally:
        await websocket.close()
        SESSIONS.pop(session_id, None)


# ---------------------------------------------------------------------------
# Background debate runner
# ---------------------------------------------------------------------------


def _run_debate(session: DebateSession) -> None:
    """Execute the full four-round crew in a thread-pool worker."""
    try:
        has_context = any([
            session.upload_session_id,
            session.target_user,
            session.competitors,
            session.differentiator,
            session.product_stage,
        ])
        session_context: dict[str, Any] | None = None
        # product_name is the short landing-page name; product_description is the full
        # description typed in the wizard. Fall back gracefully for older clients that
        # don't send product_name.
        effective_name = session.product_name or session.product_description
        if has_context:
            session_context = {
                "product_name": effective_name,
                "product_description": session.product_description,
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

        asyncio.run_coroutine_threadsafe(
            session.queue.put({"type": "log", "agent": "system", "message": f"Starting debate pipeline for {effective_name}..."}),
            session.loop,
        )

        # Pass the short product name as first arg so RAG key extraction works correctly.
        # The full description is available to build_crew via session_context.
        crew = build_crew(
            effective_name,
            task_callback=session.build_task_callback(),
            session_context=session_context,
            evidence_tier=session.evidence_tier,
        )
        result = crew.kickoff()
        verdict = parse_verdict(str(result))
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
        asyncio.run_coroutine_threadsafe(session.queue.put(None), session.loop)


# ---------------------------------------------------------------------------
# Video ingestion endpoint
# ---------------------------------------------------------------------------


@app.post("/api/ingest/video", tags=["video"])
async def ingest_video(
    product_name: str = Form(...),
    file: UploadFile = File(...),
    product_description: str = Form(""),
    target_user: str = Form(""),
    competitors: str = Form(""),
    differentiator: str = Form(""),
    product_stage: str = Form(""),
) -> dict[str, Any]:
    """Ingest a walkthrough video: frame extraction, GPT-4o vision analysis, journey synthesis."""
    session_id = str(uuid.uuid4())
    session_context = {
        "session_id": session_id,
        "product_description": product_description or "Unknown",
        "target_user": target_user or "Unknown",
        "competitors": competitors or "Unknown",
        "differentiator": differentiator or "Unknown",
        "product_stage": product_stage or "Unknown",
    }

    session_dir = SESSIONS_DIR / session_id
    frames_dir = session_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    video_suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
    video_path = str(session_dir / f"input{video_suffix}")
    with open(video_path, "wb") as fh:
        shutil.copyfileobj(file.file, fh)

    frames = extract_key_frames(video_path, str(frames_dir))
    try:
        frames_extracted = len(frames)

        if frames_extracted == 0:
            return {
                "session_id": session_id,
                "error": "No frames could be extracted. Verify the video file and that ffmpeg is installed.",
                "frames_extracted": 0,
                "key_frames_analyzed": 0,
                "chunks_added": 0,
            }

        frame_chunks, all_descriptions, ux_frames = process_video_frames(
            frames, product_name, session_context
        )
        journey_report = generate_journey_summary(
            product_name, all_descriptions, session_context
        )
        frame_analyses = [chunk["text"] for chunk in frame_chunks]

        # Match each frame's UX analysis against the 69-app competitor screenshot suite
        screenshot_matches: list[dict[str, Any]] = []
        try:
            from screenshot_suite.matcher import find_similar_screens  # noqa: PLC0415

            for ux_frame in ux_frames:
                if ux_frame["ux_analysis"]:
                    matches = find_similar_screens(ux_frame["ux_analysis"], top_k=3)
                    screenshot_matches.append(
                        {
                            "frame_number": ux_frame["frame_number"],
                            "user_analysis": ux_frame["ux_analysis"],
                            # image_path carried forward so synthesis can stamp it on cards
                            "user_image_path": ux_frame.get("image_path", ""),
                            "matched_competitors": matches,
                        }
                    )
        except Exception as exc:
            print(f"   WARNING: Screenshot matching failed: {exc}")

        VIDEO_EVIDENCE[session_id] = {
            # Product context stored here so the analysis endpoint can read it
            # even when synthesize_evidence doesn't echo these fields back.
            "product_name": product_name,
            "product_description": product_description,
            "target_user": target_user,
            "competitors": competitors,
            "differentiator": differentiator,
            "product_stage": product_stage,
            "frames_dir": str(frames_dir),
            "journey_summary": journey_report,
            "frame_analyses": frame_analyses,
            "screenshot_matches": screenshot_matches,
        }

        # Synthesise comparison cards + agent brief from screenshot matches
        synthesis: dict[str, Any] = {}
        try:
            from screenshot_suite.synthesis import synthesize_evidence  # noqa: PLC0415

            synthesis = synthesize_evidence(
                session_id=session_id,
                video_evidence=VIDEO_EVIDENCE[session_id],
                user_context={
                    "productDescription": product_description,
                    "target_user": target_user,
                    "competitors": competitors,
                    "differentiator": differentiator,
                    "product_stage": product_stage,
                },
            )
            VIDEO_EVIDENCE[session_id]["synthesis"] = synthesis
            VIDEO_EVIDENCE[session_id]["comparison_cards"] = synthesis.get("comparison_cards", [])
        except Exception as exc:
            print(f"   WARNING: Evidence synthesis failed: {exc}")

        return {
            "session_id": session_id,
            "frames_extracted": frames_extracted,
            "key_frames_analyzed": frames_extracted,
            "frames_dir": str(frames_dir),
            "journey_summary": journey_report,
            "frame_analyses": frame_analyses,
            "screenshot_matches_count": len(screenshot_matches),
            "comparison_cards_count": len(synthesis.get("comparison_cards", [])),
            "apps_compared": synthesis.get("apps_compared", []),
            "dominant_themes": synthesis.get("dominant_themes", []),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Comparison cards endpoint
# ---------------------------------------------------------------------------


@app.get("/api/comparisons/{session_id}", tags=["video"])
async def get_comparisons(session_id: str, request: Request) -> dict[str, Any]:
    """Return structured side-by-side comparison cards for a completed video ingest.

    Cards are generated during POST /api/ingest/video and cached in memory.
    Each card pairs a user frame analysis against the closest competitor
    screenshot from the 69-app suite, with curated reviews and actionable insight.
    Both sides include an ``image_url`` field the frontend can use directly.

    Raises:
        404: Session not found or synthesis not yet complete.
    """
    try:
        evidence = VIDEO_EVIDENCE.get(session_id)
        if not evidence:
            raise HTTPException(status_code=404, detail="Session not found.")
        cards = evidence.get("comparison_cards")
        if not cards:
            raise HTTPException(
                status_code=404,
                detail="No comparison cards found for this session. "
                "Either the video had no matching competitor screens or synthesis failed.",
            )
        synthesis = evidence.get("synthesis", {})

        base_url = str(request.base_url).rstrip("/")
        enriched_cards = copy.deepcopy(cards)
        for card in enriched_cards:
            user_side = card.get("user_side", {})
            if user_side.get("image_path"):
                user_side["image_url"] = f"{base_url}/{user_side['image_path']}"
            comp_side = card.get("competitor_side", {})
            if comp_side.get("image_path"):
                comp_side["image_url"] = f"{base_url}/{comp_side['image_path']}"

        return {
            "session_id": session_id,
            "cards": enriched_cards,
            "total_comparisons": len(enriched_cards),
            "apps_compared": synthesis.get("apps_compared", []),
            "dominant_themes": synthesis.get("dominant_themes", []),
            "summary": synthesis.get("agent_brief", ""),
        }
    except HTTPException:
        raise
    except Exception as exc:
        _log.exception("GET /api/comparisons/%s failed", session_id)
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc


# ---------------------------------------------------------------------------
# Parallel analysis pipeline
# ---------------------------------------------------------------------------


async def _run_analysis_bg(session_id: str, evidence: dict) -> None:
    """Background coroutine: run the adaptive analysis pipeline and write deliverable.json."""
    import logging  # noqa: PLC0415
    _log = logging.getLogger(__name__)
    ANALYSIS_STATUS[session_id] = "pending"

    synthesis = evidence.get("synthesis", {})
    comparison_cards = evidence.get("comparison_cards", [])

    def _field(key: str, default: str = "") -> str:
        return synthesis.get(key) or evidence.get(key, default)

    async def log_fn(analyst: str, message: str) -> None:
        await _push_analysis_log(session_id, analyst, message)

    runner = AdaptiveRunner()
    try:
        await runner.run_analysis(
            session_id=session_id,
            product_name=_field("product_name", "Unknown Product"),
            product_description=_field("product_description"),
            target_user=_field("target_user"),
            differentiator=_field("differentiator"),
            product_stage=_field("product_stage"),
            competitors=_field("competitors"),
            comparison_cards_json=json.dumps(comparison_cards),
            agent_brief=synthesis.get("agent_brief", ""),
            curated_evidence_json=json.dumps(
                [card.get("curated_themes", []) for card in comparison_cards]
            ),
            frame_analyses_json=json.dumps(evidence.get("frame_analyses", [])),
            screenshot_matches_json=json.dumps(evidence.get("screenshot_matches", [])),
            log_fn=log_fn,
        )
        ANALYSIS_STATUS[session_id] = "complete"
        await _push_analysis_log(session_id, "system", "Analysis complete ✓")
        _log.info("Background analysis complete for session %s", session_id)
    except Exception as exc:
        ANALYSIS_STATUS[session_id] = "failed"
        await _push_analysis_log(session_id, "system", f"Error: {exc}")
        _log.error("Background analysis failed for session %s: %s", session_id, exc)
    finally:
        # Signal SSE stream to close
        if session_id in _analysis_log_queues:
            await _analysis_log_queues[session_id].put(None)


@app.post("/api/analyze/{session_id}", tags=["analysis"])
async def run_analysis(session_id: str, background_tasks: BackgroundTasks) -> JSONResponse:
    """Start the hardware-adaptive analysis pipeline for a completed video ingest session.

    Returns 202 Accepted immediately and runs the 4-round LLM pipeline as a
    background task. Poll GET /api/report/{session_id} until it returns 200 —
    it responds with {"status": "analyzing"} (202) while the pipeline is running.

    Raises:
        404: No video evidence found for this session_id (run ingest first).
    """
    evidence = VIDEO_EVIDENCE.get(session_id)
    if not evidence:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No video evidence found for session {session_id}. "
                "Run POST /api/ingest/video first."
            ),
        )

    ANALYSIS_STATUS[session_id] = "pending"
    background_tasks.add_task(_run_analysis_bg, session_id, evidence)

    return JSONResponse(
        status_code=202,
        content={
            "session_id": session_id,
            "status": "analyzing",
            "report_url": f"/api/report/{session_id}",
        },
    )


@app.get("/api/stream/logs/{session_id}", tags=["analysis"])
async def stream_analysis_logs(session_id: str, request: Request) -> StreamingResponse:
    """SSE endpoint — streams per-analyst log lines while analysis is running.

    Replays any messages buffered before the client connected, then delivers
    new messages in real time. Sends a ``null`` sentinel when analysis ends.
    Each event is a JSON object: ``{"analyst": "strategist"|..., "message": "..."}``.
    """
    buffered = list(_analysis_log_buffers.get(session_id, []))
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    _analysis_log_queues[session_id] = queue

    async def event_gen():
        # Replay buffered messages first
        for entry in buffered:
            yield f"data: {entry}\n\n"
        # Then stream live messages
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    yield "data: {\"analyst\":\"system\",\"message\":\"...\"}\n\n"
                    continue
                if msg is None:
                    break
                yield f"data: {msg}\n\n"
        finally:
            _analysis_log_queues.pop(session_id, None)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/report/{session_id}", tags=["analysis"])
async def get_report(session_id: str) -> JSONResponse:
    """Serve the final deliverable JSON for the one-pager.

    Returns 202 while the background analysis is still running so the frontend
    can poll instead of getting a hard 404.
    """
    report_path = Path(f"sessions/{session_id}/deliverable.json")
    if not report_path.exists():
        status = ANALYSIS_STATUS.get(session_id)
        if status == "pending":
            return JSONResponse(
                status_code=202,
                content={"status": "analyzing", "session_id": session_id},
            )
        raise HTTPException(status_code=404, detail="Report not found. Run analysis first.")
    with open(report_path) as f:
        return JSONResponse(content=json.load(f))


# ---------------------------------------------------------------------------
# Execution mode toggle
# ---------------------------------------------------------------------------


@app.get("/api/config/mode", tags=["meta"])
async def get_execution_mode() -> dict[str, str]:
    """Return the current execution mode ('dgx' or 'cloud')."""
    return {"mode": _cfg.EXECUTION_MODE}


@app.post("/api/config/mode/{mode}", tags=["meta"])
async def set_execution_mode(mode: str) -> dict[str, str]:
    """Switch execution mode at runtime without restarting the server.

    Args:
        mode: 'dgx' for local Ollama on DGX Spark, 'cloud' for OpenAI GPT-4o.

    Raises:
        400: Invalid mode value.
    """
    if mode not in ("dgx", "cloud"):
        raise HTTPException(status_code=400, detail="Mode must be 'dgx' or 'cloud'")
    _cfg.EXECUTION_MODE = mode
    _cfg.THERMAL_GOVERNOR_ENABLED = mode == "dgx"
    _cfg.COOLING_ENABLED = mode == "dgx"
    label = "DGX Spark — Local Ollama" if mode == "dgx" else "Cloud API — OpenAI GPT-4o"
    return {"mode": mode, "message": f"Switched to {label}"}


# ---------------------------------------------------------------------------
# Hardware pre-flight check
# ---------------------------------------------------------------------------


@app.get("/api/preflight", tags=["meta"])
async def run_preflight() -> dict[str, Any]:
    """Hardware GO/NO-GO check — run before any analysis on the DGX Spark.

    Reads GPU temperature, GPU memory, system RAM, and currently loaded Ollama
    models. Returns a structured verdict with blocking issues, warnings, and
    recommended remediation steps.

    Use this before POST /api/analyze/{session_id} to verify the hardware is
    in a safe state to run inference without triggering a thermal shutdown.
    """
    from src.orchestration.hardware_preflight import preflight_check  # noqa: PLC0415

    return preflight_check()


# ---------------------------------------------------------------------------
# Session cleanup
# ---------------------------------------------------------------------------


@app.delete("/api/sessions/{session_id}", tags=["video"])
async def cleanup_session(session_id: str) -> dict[str, Any]:
    """Delete the session directory and evict it from the in-memory evidence store.

    Not required for demo use; prevents disk bloat in long-running deployments.

    Raises:
        404: Session directory and in-memory record both absent.
    """
    session_dir = SESSIONS_DIR / session_id
    if not session_dir.exists() and session_id not in VIDEO_EVIDENCE:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)
    VIDEO_EVIDENCE.pop(session_id, None)
    SESSIONS.pop(session_id, None)
    return {"deleted": True, "session_id": session_id}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("src.api.server:app", host=API_HOST, port=API_PORT, reload=True)
