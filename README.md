# The War Room

Multi-model adversarial QA engine for software products.

## How It Works

1. **Meta-Agent** generates three adversarial consumer personas tailored to the target product
2. **Reconnaissance Swarm** deploys 20 parallel scout agents across 31,668 real user reviews
3. **Three AI Architectures** (Llama 70B · Qwen 32B · Mistral 24B) debate the product across 4 structured rounds
4. **Verdict Engine** delivers a scored assessment with actionable fixes

```
User Input → Meta-Agent → Swarm (20 scouts) → Debate (4 rounds) → Verdict
                ↓                    ↓
ChromaDB (31,668 real reviews)   Context chaining: R1 → R2 → R3 → R4
```

## Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Orchestration | CrewAI | Sequential 4-round debate with context chaining |
| Models | Llama 3.3-70B, Qwen3-32B, Mistral-Small-24B | Different architectures = different reasoning |
| RAG | ChromaDB (31,668 chunks) | Real reviews from Reddit, HN, Google Play |
| Swarm | Python ThreadPoolExecutor | 20 parallel scouts pre-gather evidence |
| API | FastAPI + WebSocket | Real-time debate streaming |
| Frontend | React + TypeScript + Vite | Deployed on Vercel |
| Inference | NVIDIA DGX Spark (128GB) | Three models loaded simultaneously |

## Repository Structure

```
├── crew.py           # CrewAI 4-round debate orchestration
├── meta_prompt.py    # Dynamic persona generation via LLM
├── swarm.py          # 20-agent parallel reconnaissance
├── tools.py          # ChromaDB RAG tools (7 search functions)
├── api.py            # FastAPI + WebSocket streaming server
├── config.py         # Centralized configuration
├── load_db.py        # ChromaDB ingestion script
├── MASTER_PLAN.md    # Hackathon master plan (12 dimensions)
├── frontend/         # React + Vite + TypeScript
│   └── src/
│       └── components/
│           ├── Landing.tsx      # Minimal input interface
│           ├── DebateStream.tsx # Live debate visualization
│           └── VerdictCard.tsx  # Scored verdict display
└── archive/          # Legacy Streamlit prototype
```

## Quick Start
```bash
# Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Data

| Source | Documents |
|--------|----------|
| Reddit (r/productivity, r/notion, r/projectmanagement) | 22,692 |
| Hacker News | 6,348 |
| Google Play | 2,608 |
| App metadata + screenshots | 89 |
| **Total** | **31,737** |

## Team

Built at the 2026 yconic New England Inter-Collegiate AI Hackathon.

- **Tucker Anglemyer** — Providence College, Accounting & Finance
- **Griffin Kovach** — Providence College, Founder of Clerion AI
