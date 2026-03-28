"""
War Room — FastAPI server with WebSocket streaming.

Flow:
  POST /analyze       → starts a debate session in a background thread, returns session_id
  WS   /ws/{id}       → streams one JSON message per round as it completes, then a verdict
"""

import asyncio
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from crew import build_crew

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maps sequential round index (0-3) to the canonical agent_role slug
ROUND_ROLES = ["first_timer", "daily_driver", "first_timer", "buyer"]

SESSIONS: dict[str, "DebateSession"] = {}
_executor = ThreadPoolExecutor(max_workers=4)


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
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
