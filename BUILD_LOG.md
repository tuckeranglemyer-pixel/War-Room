# Build Log — The War Room

## Hackathon Timeline (March 28-29, 2026)

### Hour 0-1 — Setup & API Contract
- GitHub repo initialized
- API contract defined: `POST /analyze`, `WS /ws/{session_id}`
- DGX Spark assigned at 225 Dyer St, Providence
- SSH blocked by venue WiFi — switched to direct monitor access

### Hour 1-4 — Core Pipeline
- `crew.py` first successful 4-round debate on llama3.1:8b
- CrewAI context chaining verified: R1→R2, R1+R2→R3, R1+R2+R3→R4
- ChromaDB loaded: 31,668 chunks verified via `collection.count()`
- Tool functions wired to ChromaDB with metadata filtering

### Hour 4-8 — Server & Frontend
- FastAPI + WebSocket streaming server operational
- React frontend: Landing page, DebateStream, VerdictCard components
- Demo fallback mode built FIRST as guaranteed judge-facing experience
- Typewriter animation for debate round rendering

### Hour 8-12 — Integration & DGX Challenges
- End-to-end pipeline: frontend → API → swarm → debate → verdict
- DGX Spark thermal crash #1 during qwen3:32b inference
- Built `safe_crew.py` with cooling intervals between rounds
- DGX Spark thermal crash #2-4 during sustained inference

### Hour 12-16 — Adaptive Engineering
- 7+ DGX power-loss shutdowns documented
- Built 3-tier adaptive execution engine (`adaptive_runner.py`)
  - Tier 1: Multi-model parallel (vLLM) — ideal but unstable on Spark
  - Tier 2: Sequential single-model with 30s cooling pauses
  - Tier 3: Micro mode (8B model, halved context) for degraded hardware
- Hardware monitoring via nvidia-smi polling with thermal gating
- Pre-flight GO/NO-GO check before each analysis

### Hour 16-20 — Video Pipeline & Deployment
- Video ingestion pipeline: ffmpeg frame extraction → GPT-4o Vision analysis
- Screenshot similarity matching against ChromaDB corpus
- Frontend deployed to Vercel: https://frontend-untracked.vercel.app/
- API exposed via ngrok: https://paplike-hillary-beauteously.ngrok-free.dev/docs

### Hour 20-24 — Polish & Traction
- README comprehensive rewrite with accurate project structure
- Test suite: 45+ tests across 5 files
- Live API demo: video ingestion tested end-to-end (10 frames, full journey report)
- Rate limiter added to server.py
- Root wrapper files for master plan alignment
- Multi-model config restored with adaptive fallback framing

## DGX Spark Engineering Story
The most significant engineering challenge was the DGX Spark's thermal instability. After 7+ full power-loss shutdowns during sustained LLM inference, we built a production-grade hardware-adaptive execution system that:
- Monitors GPU temperature in real-time via nvidia-smi
- Automatically selects execution tier based on thermal state
- Unloads models between rounds to prevent cumulative heat buildup
- Trims context windows under thermal pressure
- Falls back gracefully from 32B to 8B models when hardware degrades

This turned a hardware limitation into an architectural feature — the adaptive runner is more sophisticated than a simple "run three models" approach because it handles real-world deployment constraints that production systems actually face.

## Day 2 — Demo Day (March 29, 2026)
- All code dimensions improving across 10 consecutive evaluator scans
- Plan Alignment: 91% | Code Quality: 85% | Documentation: 85%
- Technical Sophistication: 89% | Completeness: 84% | Progress Velocity: 87%
- Frontend live: https://frontend-untracked.vercel.app/
- API live: https://paplike-hillary-beauteously.ngrok-free.dev/docs
- 125+ commits shipped in 24-hour window
