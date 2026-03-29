# 🏛️ The War Room

**Three AI models debate your product using 31,668 real user reviews, in 4 minutes, for free.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)](https://react.dev/)
[![CrewAI](https://img.shields.io/badge/CrewAI-orchestration-orange)](https://www.crewai.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

The War Room is a multi-agent AI platform that conducts adversarial product quality analysis by orchestrating structured debate between three distinct open-weight language model architectures, grounded in a pre-curated RAG corpus of real user reviews.

**Live Demo:** [Frontend](https://frontend-untracked.vercel.app/) · [API Docs](https://war-room-production.up.railway.app/docs) · [Health Check](https://war-room-production.up.railway.app/health)

**Production Backend:** Railway (Dockerfile, ffmpeg, Python 3.12, ChromaDB 31,668 chunks)

**Built with:**
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![CrewAI](https://img.shields.io/badge/CrewAI-multi--agent-orange)](https://www.crewai.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-vector--store-green)](https://www.trychroma.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-websocket-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![NVIDIA DGX Spark](https://img.shields.io/badge/NVIDIA-DGX%20Spark-76B900?logo=nvidia&logoColor=white)](https://www.nvidia.com/en-us/products/workstations/dgx-spark/)

> Built at the **2026 yconic New England Inter-Collegiate AI Hackathon** by **Tucker Anglemyer** & **Griffin Kovach**

---

## Features

| Feature | Description |
|---------|-------------|
| **4-round adversarial debate** | Three distinct open-weight LLM families (Llama / Qwen / Mistral) argue over real user evidence, with context chaining R1→R2→R3→R4 |
| **31,668-chunk RAG corpus** | Pre-embedded user reviews, Reddit posts, HN comments, and app metadata across 20 PM tools |
| **Reconnaissance swarm** | 20 parallel ChromaDB scouts query across product dimensions in 1–3 seconds |
| **Live SSE streaming** | Real-time analysis progress via Server-Sent Events at `GET /api/stream/logs/{session_id}` |
| **Dual inference** | Cloud API mode (GPT-4o, sub-60s) and DGX Spark mode (local open-weight, thermal-managed) |
| **Featured product fast-path** | Click any of 20 curated products → debate starts in <5 seconds, no wizard |
| **Two-tier evidence** | Full RAG for 20 curated products, general analysis for freeform entries |
| **6-stage analysis pipeline** | Animated progress feed: frame extraction → vision analysis → competitor matching → evidence curation → specialist deployment → report assembly |
| **Budget guard** | Auto-fallback to demo after 100 daily analyses |
| **Per-IP rate limiting** | 3 analyses per hour per IP |
| **Video ingestion** | ffmpeg frame extraction → GPT-4o Vision → ChromaDB evidence chunks |
| **Hardware-adaptive execution** | 3-tier thermal management on DGX Spark — auto-degrades under GPU pressure |
| **Demo fallback** | Hardcoded typewriter-animated debate activates automatically if WebSocket disconnects |
| **McKinsey-style report** | Structured verdict with score, BUY/PASS/CONDITIONS, sprint-ready findings, evidence citations |

---

## Architecture

```
User Input (product name)
    │
    ▼
┌─────────────────┐
│   Meta-Agent     │ ← Generates product-specific adversarial personas
│  (8-category     │   based on software category taxonomy
│   taxonomy)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Reconnaissance  │ ← 20+ parallel scout agents query ChromaDB
│     Swarm        │   31,668 chunks across 20 product dimensions
│  (6-12 seconds)  │   Sub-50ms cosine similarity retrieval
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4-Round Debate  │ ← CrewAI sequential pipeline
│                  │   R1: First-Timer (Llama 3.3 70B)
│  Context Chain:  │   R2: Daily Driver (Qwen3 32B)
│  R1→R2→R3→R4    │   R3: First-Timer rebuttal
│                  │   R4: Buyer verdict (Mistral Small 24B)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Verdict Card    │ ← Score (1-100), BUY/PASS/CONDITIONS
│                  │   Sprint-ready findings with severity ratings
│  Export: JSON,   │   Evidence citations linking to source reviews
│  Markdown, Jira  │
└─────────────────┘
```

> **Routing note:** Featured products (20 curated) bypass the context wizard and route directly to `POST /analyze` → WebSocket debate stream. Freeform products go through the full context form with optional video upload. Both paths converge on the same 4-round CrewAI pipeline.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Orchestration** | CrewAI | Multi-agent debate pipeline with context chaining |
| **Vector DB** | ChromaDB | 31,668 pre-embedded chunks, cosine similarity search |
| **Embedding** | all-MiniLM-L6-v2 | 384-dim vectors via ChromaDB default |
| **API** | FastAPI | REST (`POST /analyze`) + WebSocket (`WS /ws/{session_id}`) |
| **Inference** | Ollama / vLLM | Local open-weight model serving |
| **Frontend** | React + TypeScript | Live debate stream, verdict cards, Framer Motion animations |
| **Styling** | Tailwind CSS v4 | Utility-first styling with Vite plugin |
| **Deployment** | Vercel | Frontend hosting with analytics |
| **Compute** | NVIDIA DGX Spark | 128GB unified memory for concurrent multi-model serving |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed and running
- ChromaDB data (included in `chroma_db/`)

### Setup

```bash
cd War-Room
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Cloud Mode (recommended for demos)

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-...  # or OPENAI_API_KEY

# Start server in cloud mode
uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

### DGX Spark Mode (on-prem, data sovereign)

```bash
# Run pre-flight check
python -m src.orchestration.hardware_preflight

# Start with adaptive thermal management
uvicorn src.api.server:app --host 0.0.0.0 --port 8000
# AdaptiveRunner auto-selects tier based on GPU telemetry
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Run an Analysis

```bash
# Via API
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"product": "Notion"}'

# Connect to WebSocket for live streaming
wscat -c ws://localhost:8000/ws/{session_id}
```

### Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

Key variables (all optional — defaults target DGX Spark production):

| Variable | Default | Description |
|----------|---------|-------------|
| `FIRST_TIMER_MODEL` | `ollama/llama3.3:70b` | First-Timer agent model (Llama) |
| `DAILY_DRIVER_MODEL` | `ollama/qwen3:32b` | Daily Driver agent model (Qwen) |
| `BUYER_MODEL` | `ollama/mistral-small:24b` | Buyer agent model (Mistral) |
| `LOCAL_MODEL` | `ollama/llama3.1:8b` | Utility model for persona generation + swarm |
| `LOCAL_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `CHROMA_DB_PATH` | `./chroma_db` | Path to ChromaDB persistence |
| `COLLECTION_NAME` | `pm_tools` | ChromaDB collection name |
| `API_PORT` | `8000` | FastAPI server port |
| `MAX_SCOUTS` | `20` | Parallel swarm reconnaissance agents |

> **Local dev tip:** Running all three large models concurrently requires DGX Spark's 128 GB unified memory. On local hardware, override all three model vars to a smaller model (e.g. `ollama/llama3.1:8b`) or use `optimized_crew.py` which routes through `thermal_safe_debate_runner` for single-model-at-a-time sequential loading.

---

## API Reference

### `POST /analyze`

Triggers a full War Room analysis session.

**Request:**

```json
{"product": "Notion - All-in-one workspace for notes, docs, and project management"}
```

**Response:**

```json
{"session_id": "abc-123", "status": "started"}
```

### `WS /ws/{session_id}`

Real-time streaming of debate rounds.

**Events:**

```json
{"type": "round", "round": 1, "agent": "First-Timer", "model": "llama3.3:70b", "content": "..."}
{"type": "round", "round": 2, "agent": "Daily Driver", "model": "qwen3:32b", "content": "..."}
{"type": "round", "round": 3, "agent": "First-Timer", "model": "llama3.3:70b", "content": "..."}
{"type": "verdict", "round": 4, "agent": "Buyer", "score": 72, "decision": "CONDITIONS", "findings": [...]}
```

### `GET /api/stream/logs/{session_id}`

Server-Sent Events endpoint for real-time analysis progress. Replays buffered messages for late-connecting clients, streams live updates, and closes on completion.

**Events** (text/event-stream):

```
data: {"stage": "frame_extraction", "message": "Extracting 10 frames from video..."}
data: {"stage": "vision_analysis", "message": "Analyzing frames with GPT-4o Vision..."}
data: {"stage": "competitor_matching", "message": "Matching against ChromaDB corpus..."}
data: {"stage": "evidence_curation", "message": "Curating evidence for specialists..."}
data: {"stage": "specialist_deployment", "message": "Deploying Round 1: Strategist..."}
data: {"stage": "report_assembly", "message": "Assembling final deliverable..."}
data: [DONE]
```

### `GET /api/preflight`

Hardware pre-flight check. Returns GO/NO-GO verdict with GPU temp, RAM usage, and loaded model status.

```json
{
  "verdict": "GO",
  "tier_recommendation": 2,
  "health": {
    "gpu_temp": 48,
    "gpu_memory": {"used_mib": 12000, "total_mib": 131072, "free_mib": 119072},
    "ram": {"used_gb": 42.1, "total_gb": 128.0, "percent": 33.0},
    "loaded_models": []
  }
}
```

### `POST /api/ingest/video`

Walkthrough video ingestion — extracts key frames via ffmpeg and analyzes with GPT-4o Vision, then stores evidence chunks in ChromaDB. Requires `OPENAI_API_KEY`.

### `GET /health`

Health check for orchestration and demo status.

**Interactive API docs (when server is running):** [Swagger UI `/docs`](http://127.0.0.1:8000/docs) · [ReDoc `/redoc`](http://127.0.0.1:8000/redoc)

---

## Project Structure

```
War-Room/
├── src/                              # Core application package
│   ├── api/
│   │   └── server.py                 # FastAPI REST + WebSocket streaming server
│   ├── inference/
│   │   ├── model_config.py           # Model & runtime configuration (env-driven)
│   │   ├── vllm_multi_model_dispatch.py  # Multi-model dispatch + thermal management
│   │   └── dgx_preflight_check.py    # DGX Spark pre-flight health checker
│   ├── orchestration/
│   │   ├── adversarial_debate_engine.py  # CrewAI 4-round debate pipeline
│   │   ├── persona_generator.py      # Meta-prompt adversarial persona generation
│   │   ├── swarm_reconnaissance.py   # Parallel 20-scout evidence gathering
│   │   ├── thermal_safe_debate_runner.py  # Single-model-at-a-time DGX runner
│   │   └── response_synthesizer.py   # Verdict parsing and synthesis
│   └── rag/
│       └── chroma_retrieval.py       # ChromaDB query wrappers + CrewAI @tool functions
├── ingestion/                        # Data pipeline
│   ├── google_play_scraper.py        # Google Play review scraper
│   ├── reddit_scraper.py             # Reddit post/comment scraper
│   ├── hackernews_scraper.py         # Hacker News comment scraper
│   ├── chunk_preprocessor.py         # Text chunking and normalization
│   ├── chroma_batch_loader.py        # ChromaDB batch ingestion
│   ├── chroma_safe_batch_loader.py   # Safe/resumable batch loader
│   └── screenshot_vision_ingest.py   # Screenshot → ChromaDB via GPT-4o Vision
├── frontend/                         # React + TypeScript frontend
│   ├── src/
│   │   ├── App.tsx                   # Router and WebSocket connection manager
│   │   ├── animations.ts             # Framer Motion animation presets
│   │   ├── preloadedProducts.ts      # Cached product list for instant UI
│   │   └── components/
│   │       ├── Landing.tsx           # Landing page with product search
│   │       ├── DebateStream.tsx      # Live debate round streaming display
│   │       ├── VerdictCard.tsx       # Final verdict with score and findings
│   │       └── ContextForm.tsx       # Product context input form
│   ├── package.json
│   └── vite.config.ts
├── tests/                            # Integration test suite
│   ├── conftest.py                   # Shared fixtures
│   ├── test_adversarial_debate_orchestration.py
│   ├── test_rag_retrieval.py
│   ├── test_response_synthesis.py
│   └── test_vllm_model_dispatch.py
├── optimized_crew.py                 # DGX-optimized CLI: smart evidence + thermal-safe debate
├── test_crew.py                      # Lightweight smoke tests (no CrewAI import)
├── chroma_db/                        # Pre-embedded vector database (31,668 chunks)
├── requirements.txt                  # Python dependencies
├── .env.example                      # Documented environment variable defaults
├── LICENSE                           # MIT
└── README.md
```

---

## Key Design Decisions

- **Multi-model adversarial debate:** Three distinct model families (Llama / Qwen / Mistral) ensure genuinely independent analytical perspectives — different training data → different biases → real disagreement. This is the architectural default, not an aspirational target.

- **Inference strategy — design vs. adaptive fallback:** `config.py` defines three canonical model IDs (`FIRST_TIMER_MODEL`, `DAILY_DRIVER_MODEL`, `BUYER_MODEL`) as the primary configuration. When DGX Spark thermal constraints prevent concurrent multi-model serving, `FALLBACK_MODEL` routes all personas through a single model via `thermal_safe_debate_runner.py`. Multi-model is the design; single-model rotation is the engineering response to real hardware limits.

- **Pre-seeded context injection:** `fetch_context_for_product()` retrieves RAG results at crew build time and injects directly into task descriptions, guaranteeing evidence grounding even if the LLM skips ReAct tool calls

- **Swarm reconnaissance:** 20+ parallel scout threads query ChromaDB across different product dimensions (onboarding, pricing, performance, integrations, etc.) in 1-2 seconds vs ~40 seconds serially

- **Smart evidence curation:** `optimized_crew.py` uses a lightweight 8B model to generate product-specific RAG queries instead of hardcoded templates, then unloads it before the debate starts

- **Thermal-safe debate runner:** Single-model-at-a-time loading with GPU thermal gating prevents cumulative VRAM pressure from crashing the DGX Spark mid-debate. Triggered automatically when GPU exceeds `SAFE_THERMAL_CEILING` (default 75°C); resumes when it drops below `SAFE_THERMAL_RESUME` (default 65°C). Tradeoff: ~30-second cooldown between rounds vs. concurrent serving when thermals permit.

- **Demo fallback:** Hardcoded 4-round debate with typewriter animation activates automatically if WebSocket disconnects within 8 seconds — the system never shows a broken state

- **Circuit-breaker pattern:** WebSocket timeout triggers graceful degradation to demo mode rather than error screens

---

## Inference Configuration

### Default: Three Distinct Models (DGX Spark)

```python
# config.py — Multi-model defaults (DGX Spark target)
FIRST_TIMER_MODEL  = "ollama/llama3.3:70b"      # Llama family — broad, impressionistic
DAILY_DRIVER_MODEL = "ollama/qwen3:32b"          # Qwen family — precise, technical
BUYER_MODEL        = "ollama/mistral-small:24b"  # Mistral family — concise, business

# Adaptive fallback (thermal constraints)
FALLBACK_MODEL     = "ollama/qwen3:32b"          # All personas on single model
```

Three distinct open-weight architectures maximize epistemic divergence: different training data → different priors → genuine disagreement rather than correlated outputs from the same model family.

### Adaptive Fallback: Thermal-Safe Single-Model Rotation

When DGX Spark GPU temperatures exceed the thermal ceiling during sustained debate inference, `thermal_safe_debate_runner.py` automatically degrades to `FALLBACK_MODEL`, loading one model at a time with cooldown intervals. This is not a limitation — it is hardware-aware engineering that keeps the system running under real production constraints.

| Condition | Mode | Behavior |
|-----------|------|----------|
| GPU temp < 75°C | **Multi-model** | Llama / Qwen / Mistral run concurrently |
| GPU temp ≥ 75°C | **Adaptive fallback** | Single model, sequential loading, 30s cooldowns |
| Consumer hardware | **Local dev** | `LOCAL_MODEL` + `DAILY_DRIVER_BUYER_MODEL` (small models) |

All three modes produce a valid 4-round debate with full evidence grounding — only the model diversity varies.

---

## Dual Inference Strategy

The War Room supports two inference paths, selectable per deployment:

**Cloud API Mode (Live Demos & Traction)**
For real-time live analysis during demos and public use, the pipeline routes through cloud LLM APIs (Anthropic/OpenAI). This enables:
- Sub-60-second full 4-round debates on any product
- Reliable live demos without thermal constraints
- Real analysis output (JSON verdicts, evidence citations) for traction measurement
- Tested end-to-end on competitor products during the hackathon

**DGX Spark Mode (On-Prem & Data Sovereignty)**
For enterprises requiring zero data leakage, the pipeline runs entirely on local open-weight models via Ollama/vLLM on DGX Spark's 128GB unified memory. This mode includes:
- Hardware-adaptive execution engine (AdaptiveRunner) with 3-tier thermal management
- Real-time GPU telemetry via nvidia-smi with automatic tier degradation
- Thermal gating: automatic cooldown pauses when GPU exceeds 70°C
- Model lifecycle management: unload/reload between rounds to prevent cumulative heat buildup
- Pre-flight GO/NO-GO check before each analysis

The DGX Spark adaptive runner is production-grade infrastructure that solves a real deployment problem — sustained LLM inference on unified-memory hardware with thermal constraints. Cloud mode doesn't need it; enterprise on-prem mode does. Both paths produce identical verdict JSON output.

---

## DGX Spark Configuration

The War Room is designed for DGX Spark's 128GB unified memory to serve three concurrent models:

| Model | Architecture | INT4 Memory |
|-------|-------------|-------------|
| Llama 3.3 70B | Meta | ~38GB |
| Qwen3 32B | Alibaba | ~18GB |
| Mistral Small 24B | Mistral AI | ~14GB |
| KV Cache overhead | — | ~15-20GB |
| **Total** | | **~85-90GB** |

On consumer hardware (16-64GB RAM), `thermal_safe_debate_runner.py` manages single-model rotation with thermal gating, preserving full debate functionality at the cost of inter-round latency.

### Pre-flight Check

```bash
python -m src.inference.dgx_preflight_check
```

Verifies GPU temperature, free VRAM, Ollama model availability, RAM headroom, and disk space before launching a debate. Prints GO / NO-GO recommendation.

---

## Testing

```bash
# Lightweight smoke tests (no CrewAI import required)
pytest test_crew.py -v

# Full integration suite
pytest tests/ -v
```

---

## Team

- **Tucker Anglemyer** — CrewAI orchestration, FastAPI/WebSocket API, React frontend, Vercel deployment
- **Griffin Kovach** — RAG dataset curation (31,668 chunks), ChromaDB pipeline, tool functions, data quality

---

## License

MIT
