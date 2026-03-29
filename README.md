# 🏛️ The War Room

**Three AI models debate your product using 31,668 real user reviews, in 4 minutes, for free.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)](https://react.dev/)
[![CrewAI](https://img.shields.io/badge/CrewAI-orchestration-orange)](https://www.crewai.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

The War Room is a multi-agent AI platform that conducts adversarial product quality analysis by orchestrating structured debate between three distinct open-weight language model architectures, grounded in a pre-curated RAG corpus of real user reviews.

> Built at the **2026 yconic New England Inter-Collegiate AI Hackathon** by **Tucker Anglemyer** & **Griffin Kovach**

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

### Backend

```bash
cd War-Room
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the API server
uvicorn src.api.server:app --host 0.0.0.0 --port 8000
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

- **Multi-model adversarial debate:** Three distinct model families (Llama / Qwen / Mistral) ensure genuinely independent analytical perspectives — different training data → different biases → real disagreement

- **Pre-seeded context injection:** `fetch_context_for_product()` retrieves RAG results at crew build time and injects directly into task descriptions, guaranteeing evidence grounding even if the LLM skips ReAct tool calls

- **Swarm reconnaissance:** 20+ parallel scout threads query ChromaDB across different product dimensions (onboarding, pricing, performance, integrations, etc.) in 1-2 seconds vs ~40 seconds serially

- **Smart evidence curation:** `optimized_crew.py` uses a lightweight 8B model to generate product-specific RAG queries instead of hardcoded templates, then unloads it before the debate starts

- **Thermal-safe debate runner:** Single-model-at-a-time loading with GPU thermal gating prevents cumulative VRAM pressure from crashing the DGX Spark mid-debate — tradeoff is ~30-second cooldown between rounds

- **Demo fallback:** Hardcoded 4-round debate with typewriter animation activates automatically if WebSocket disconnects within 8 seconds — the system never shows a broken state

- **Circuit-breaker pattern:** WebSocket timeout triggers graceful degradation to demo mode rather than error screens

---

## DGX Spark Configuration

The War Room requires DGX Spark's 128GB unified memory to serve three concurrent models:

| Model | Architecture | INT4 Memory |
|-------|-------------|-------------|
| Llama 3.3 70B | Meta | ~38GB |
| Qwen3 32B | Alibaba | ~18GB |
| Mistral Small 24B | Mistral AI | ~14GB |
| KV Cache overhead | — | ~15-20GB |
| **Total** | | **~85-90GB** |

On consumer hardware (16-64GB RAM), only one 70B model loads at a time — forcing 30-60 second swap delays that destroy the real-time debate experience. The `thermal_safe_debate_runner.py` manages this single-model rotation with thermal gating.

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
