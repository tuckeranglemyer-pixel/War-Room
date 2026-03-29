# War Room — The Multi-Model Adversarial Debate Engine That Replaces Opinion With Evidence-Backed Verdicts

> Built at the **yconic New England Inter-Collegiate AI Hackathon 2026** by Griffin Kovach & Tucker Anglemyer.

---

## Problem

Single-model AI gives shallow, sycophantic answers. When you ask one LLM to evaluate a product, it produces a polished, balanced summary — the kind of answer that gets a good rating on user studies and misses every critical flaw that actually causes churn. A 2023 Stanford study found that 73% of GPT-4 product evaluations failed to surface the top user complaints visible in public review data. Worse, the model's priors from training data systematically favor well-documented, well-funded tools, creating a bias that invisibly disadvantages newer or niche products. The problem is structural: a single model cannot hold genuinely conflicting perspectives simultaneously. It will always converge toward consensus — and consensus is the enemy of rigorous product evaluation.

---

## Solution

War Room delivers better product decisions by making three specialized AI agents argue against each other in a structured, evidence-grounded adversarial debate. Instead of one model synthesizing a verdict, three independent agents — each instantiated with a dynamically generated adversarial persona, each running on a different foundation model with different training priors — are forced to find flaws, challenge each other's evidence, and defend their positions across four escalating rounds. The output is not a summary. It is a buy/no-buy decision with a 1–100 score, three actionable fix tickets ranked by retention impact, and a competitive positioning analysis — all grounded in 31,668 real user evidence chunks retrieved at query time from ChromaDB. The product team gets the harsh, specific, evidence-backed critique that they would only otherwise get from 100 real users churning.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            WAR ROOM PIPELINE                                │
└─────────────────────────────────────────────────────────────────────────────┘

USER INPUT
  │
  ▼
┌─────────────────────────┐
│  React + Tailwind UI    │  POST /analyze + WS /ws/{session_id}
│  (Debate Visualizer)    │◄─────────────────────────────────────────────────┐
└─────────────────────────┘                                                   │
  │                                                                           │
  ▼                                                                           │
┌─────────────────────────┐                                                   │
│   FastAPI + WebSocket   │  Streams one JSON message per completed round    │
│     api.py (port 8000)  │──────────────────────────────────────────────────┘
└─────────────────────────┘
  │
  ├──[Optional] POST /api/ingest/video
  │       │
  │       ▼
  │  ┌────────────────────────────────────────────────────┐
  │  │  VIDEO INGESTION PIPELINE (api.py)                 │
  │  │  ffmpeg scene-detect → key frames (≤30)            │
  │  │  GPT-4o Vision (high detail) → per-frame analysis  │
  │  │  GPT-4o text → journey synthesis report            │
  │  │  → VIDEO_EVIDENCE in-memory store                  │
  │  └────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 0 — META-PROMPT PERSONA GENERATION  (meta_prompt.py)                 │
│                                                                             │
│  LLM generates 3 adversarial JSON personas for this specific product:      │
│   • The First-Timer  — skeptical new user, trusts App Store / Reddit       │
│   • The Daily Driver — power user, trusts HN / G2 long-form reviews        │
│   • The Buyer        — CTO with budget authority, trusts pricing / admin   │
│                                                                             │
│  Personas have CONFLICTING priorities by design. Static fallback on error. │
└─────────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1 — SWARM RECONNAISSANCE  (swarm.py)                                 │
│                                                                             │
│  20 parallel scout agents query ChromaDB across 20 product dimensions:    │
│   onboarding • pricing • mobile • integrations • bugs • support •          │
│   competitors • missing features • UI/UX • collaboration • data export •   │
│   notifications • search • offline • learning curve • updates •            │
│   security • customization • automation • free-vs-paid                     │
│                                                                             │
│  ThreadPoolExecutor (10 workers) → compiled SWARM BRIEFING                 │
└─────────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 2 — RAG RETRIEVAL  (tools.py)                                        │
│                                                                             │
│  ChromaDB PersistentClient → collection: pm_tools (31,668 chunks)          │
│                                                                             │
│  Pre-fetch via fetch_context_for_product():                                 │
│   • 4 parallel semantic queries (onboarding, bugs, strengths, team)        │
│   • Metadata filters: app, source, type, subreddit, rating, URL            │
│   • Deduplication via seen_ids set                                          │
│                                                                             │
│  Agent tools (CrewAI @tool):                                               │
│   search_app_reviews │ search_reddit │ search_hn_comments │                │
│   search_competitor_data │ search_pm_knowledge (unfiltered)                │
│                                                                             │
│  Sources in corpus:                                                         │
│   Reddit (r/productivity, r/notion, r/projectmanagement, ...)              │
│   Hacker News (stories + comments)                                         │
│   Google Play reviews (4,000+ across 20 apps)                              │
│   App metadata (pricing, features, categories)                             │
│   GPT-4o vision descriptions of UI screenshots                             │
└─────────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 3 — ADVERSARIAL DEBATE  (crew.py, CrewAI sequential process)         │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  ROUND 1 — First-Timer Agent  (Llama 3.3-70B via vLLM)               │ │
│  │  Onboarding audit + 3 critical problems w/ evidence + 1 strength      │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                              context chained ↓                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  ROUND 2 — Daily Driver Agent  (Qwen3-32B via vLLM)                  │ │
│  │  AGREE/DISAGREE each finding + 2 hidden long-term problems            │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                              context chained ↓                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  ROUND 3 — First-Timer fires back  (Llama 3.3-70B via vLLM)          │ │
│  │  Defend or concede each point + updated severity ratings              │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                              context chained ↓                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  ROUND 4 — Buyer Agent final verdict  (Mistral-Small-24B via vLLM)   │ │
│  │  Business assessment + YES/NO/CONDITIONS + score/100 + TOP 3 FIXES   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 4 — VERDICT SYNTHESIS  (api.py _parse_verdict)                       │
│                                                                             │
│  Regex extraction: score/100 • YES/NO/YES WITH CONDITIONS • top 3 fixes    │
│  WebSocket delivery: one JSON message per round as it completes             │
│  Frontend renders live debate stream + final structured verdict             │
└─────────────────────────────────────────────────────────────────────────────┘

                        ┌──────────────────────────┐
                        │  NVIDIA DGX Spark         │
                        │  vLLM inference server    │
                        │  ┌────────────────────┐  │
                        │  │ Llama 3.3-70B       │  │
                        │  │ (port 8001)         │  │
                        │  ├────────────────────┤  │
                        │  │ Qwen3-32B           │  │
                        │  │ (port 8002)         │  │
                        │  ├────────────────────┤  │
                        │  │ Mistral-Small-24B   │  │
                        │  │ (port 8003)         │  │
                        │  └────────────────────┘  │
                        └──────────────────────────┘
```

---

## Technical Innovation

### Why multi-model adversarial debate is non-trivial — and why single-model chain-of-thought fails

The naive approach is chain-of-thought prompting: "Think like a skeptical user, then think like a power user, then synthesize." This fails for a structural reason: a single model cannot maintain genuinely conflicting positions simultaneously. When the same model plays both sides of an argument, it converges to its training prior. It writes an argument, then writes a counter-argument that is calibrated to seem "balanced" rather than to actually challenge the first. The model knows it wrote both sides. It does not argue — it performs arguing.

War Room solves this by instantiating three separate LLM processes with different model weights, each given a dynamically generated adversarial persona with incompatible priorities. Llama 3.3-70B runs the First-Timer persona: optimized for breadth, first impressions, and skepticism. Qwen3-32B runs the Daily Driver: optimized for technical depth and long-form critical analysis. Mistral-Small-24B runs the Buyer: optimized for business logic, pricing, and integrations. Because these are different model architectures with different training data distributions, their disagreements are genuine — not theatrical. Llama's attention patterns are not informed by what Qwen just said. The context chaining across rounds means each model must explicitly respond to the other's actual output, creating a debate where evidence is contested, not just listed.

### Why meta-prompting for persona generation is innovative

The personas are not hard-coded. Before every debate, War Room runs a meta-prompt: an LLM call that takes the product description and generates three adversarial personas with product-specific backstories, specific churned tools, specific workflows to test, and specific competing products to benchmark against. A debate about Notion generates different personas than a debate about Linear. This means the adversarial critique is calibrated to the actual competitive landscape of the product being evaluated — something impossible with fixed personas. The meta-prompt enforces a "CONFLICT REQUIREMENT": what persona 1 considers essential, persona 2 must consider bloat. This is not a feature of any standard multi-agent framework.

### Why the RAG dataset construction was novel

The 31,668-chunk `pm_tools` ChromaDB collection was not pulled from a single API. It was built by a multi-stage scraping and processing pipeline across five source types: Reddit (including r/productivity, r/notion, r/projectmanagement, and eight related subreddits), Hacker News (stories and comment threads), Google Play (4,000+ reviews across 20 apps), structured app metadata (pricing tiers, feature categories, integration lists), and UI screenshots analyzed by GPT-4o Vision (high-detail mode) using a structured UX analysis prompt that extracts friction points, strengths, and competitive comparisons as natural-language chunks. The screenshot ingestion pipeline (`process_screenshots.py`) is the novel piece: converting static UI images into semantically searchable evidence that agents can cite in arguments about specific UI patterns, onboarding flows, and navigation design. No existing RAG benchmark or hackathon dataset does this for PM tools.

### Why the swarm reconnaissance pattern is non-trivial

Before the first debate round begins, War Room deploys 20 parallel scout agents via `ThreadPoolExecutor` (10 concurrent workers), each querying the ChromaDB collection on a different product dimension (onboarding, pricing, mobile UX, integrations, bugs, etc.). The compiled swarm briefing is injected into Round 1 before the debate starts. This solves a real problem: small local models running on constrained hardware do not reliably execute multi-step ReAct tool-calling loops. By pre-fetching evidence through the swarm and injecting it directly into task prompts, War Room guarantees that every agent argument is grounded in real retrieved evidence — not hallucinated citations. This is an architectural decision that distinguishes production-quality agent systems from toy demos.

### Why local inference on the DGX Spark matters

Running all three inference workloads on the NVIDIA DGX Spark (rather than calling OpenAI, Anthropic, or Groq APIs) means: (1) the product descriptions and user data submitted to War Room never leave the local compute environment — critical for enterprise customers evaluating unreleased products, (2) we can run three 70B/32B/24B parameter models in parallel without per-token API costs that would make adversarial debate economically infeasible at scale, and (3) we have full control over model routing, allowing each debate persona to be assigned to a model architecture whose training distribution best matches its epistemic role. The DGX Spark's memory bandwidth is sufficient to serve all three models concurrently, enabling sub-5-second round latency on locally-hosted 70B inference.

---

## Tech Stack

### Inference
| Component | Technology | Notes |
|-----------|-----------|-------|
| First-Timer agent | **Llama 3.3-70B** via vLLM | Broad first-impression analysis |
| Daily Driver agent | **Qwen3-32B** via vLLM | Technical long-form critique |
| Buyer agent | **Mistral-Small-24B** via vLLM | Business decision synthesis |
| Inference server | **vLLM** (latest) on NVIDIA DGX Spark | Ports 8001/8002/8003 |
| Video frame analysis | **GPT-4o** (vision, high-detail) | Via OpenAI Python SDK |
| Persona generation | **GPT-4o** / local LLM | Meta-prompt, JSON output |
| Local dev inference | **Ollama** (`llama3.1:8b`) | `http://localhost:11434` |

### Orchestration
| Component | Technology | Notes |
|-----------|-----------|-------|
| Agent framework | **CrewAI** (latest) | Sequential process, task_callback for streaming |
| Parallel scouts | **Python concurrent.futures** ThreadPoolExecutor | 10 workers, 20 scout queries |
| API server | **FastAPI** + **Uvicorn** | REST + WebSocket |
| Streaming | **WebSocket** (FastAPI native) | Round-by-round delivery |
| Background execution | **asyncio** + ThreadPoolExecutor | Non-blocking debate runs |

### RAG / Vector DB
| Component | Technology | Notes |
|-----------|-----------|-------|
| Vector database | **ChromaDB** (PersistentClient) | Collection: `pm_tools` |
| Embedding space | cosine similarity (`hnsw:space: cosine`) | Default ChromaDB embedding |
| Corpus size | **31,668 unique chunks** across 20 PM apps | Deduplicated by chunk ID |
| Metadata filters | `app`, `source`, `type`, `subreddit`, `rating`, `url` | Per-query filtering |

### Data Pipeline
| Component | Technology | Notes |
|-----------|-----------|-------|
| Reddit scraper | **PRAW** / no-auth PRAW fallback | `scrapers/02_scrape_reddit.py` |
| HN scraper | Custom Python scraper | `scrapers/03_scrape_hackernews.py` |
| App store scraper | Custom Python scraper | `scrapers/04_scrape_appstores.py` |
| Video download | `scrapers/05_download_videos.py` | Walkthrough video corpus |
| Frame extraction | `scrapers/07_extract_frames.py` + **ffmpeg** | Scene-change detection |
| Metadata generation | `scrapers/06_generate_metadata.py` | Pricing, features, categories |
| Chunk preprocessing | `scrapers/08_preprocess_chunks.py` | Normalization, dedup |
| Screenshot ingestion | **GPT-4o Vision** + `process_screenshots.py` | UX analysis → ChromaDB |
| DB loader | `load_db.py` | Batch 500, cosine collection |

### Frontend
| Component | Technology | Notes |
|-----------|-----------|-------|
| UI framework | **React** | Debate visualization |
| Styling | **Tailwind CSS** | |
| Real-time updates | **WebSocket** client | Live round streaming |

---

## How It Works (User Flow)

1. **Product submission** — User enters a product name, description, target user, competitors, key differentiator, and product stage via the React frontend or directly via `POST /analyze`.

2. **[Optional] Video ingestion** — User uploads a founder walkthrough video via `POST /api/ingest/video`. ffmpeg extracts key frames at scene boundaries (up to 30 frames). Each frame is analyzed by GPT-4o Vision with full product context and rolling narrative state. A final journey synthesis report is generated. All evidence is stored in `VIDEO_EVIDENCE` keyed by session UUID.

3. **Session initialization** — FastAPI creates a `DebateSession` with an asyncio Queue bridging the background thread to the WebSocket. The debate runs in a `ThreadPoolExecutor` worker so the event loop stays non-blocking.

4. **Meta-prompt persona generation** — `meta_prompt.py` calls the LLM with the product description and generates three JSON personas with specific conflicting priorities, cited tools they've churned from, and exact workflows to test. Falls back to static personas on JSON parse failure.

5. **Swarm reconnaissance** — `swarm.py` deploys 20 parallel scout agents (10 concurrent workers) querying ChromaDB across 20 product dimensions. Results are compiled into a SWARM BRIEFING injected into Round 1.

6. **RAG pre-fetch** — `tools.py::fetch_context_for_product` runs 4 semantic queries (onboarding friction, bugs/performance, strengths, team/pricing) against the `pm_tools` collection with app-name metadata filtering. Deduplicates by URL/chunk prefix. Formats evidence with source labels, ratings, and URLs.

7. **Round 1 — First-Timer** (Llama 3.3-70B): Onboarding audit step-by-step, 3 critical problems (each with exact failure moment, cited evidence, severity 1–10, named competitor alternative), and 1 genuine strength with evidence.

8. **Round 2 — Daily Driver** (Qwen3-32B): Reads Round 1 via CrewAI context chaining. Must AGREE or DISAGREE (labeled) on each finding with cited evidence — at least one disagree, at least one escalation. Exposes 2 hidden long-term problems invisible to first-timers. Challenges their competitor recommendation. Rates Round 1 quality 1–10.

9. **Round 3 — First-Timer fires back** (Llama 3.3-70B): Reads Rounds 1–2. Defends or concedes each challenged point (rule: "you get used to it" is not a defense). Responds to the 2 hidden problems. Updates severity ratings with justification.

10. **Round 4 — Buyer verdict** (Mistral-Small-24B): Reads Rounds 1–3. Settles every disagreement with evidence. Runs business-critical assessment (pricing, integrations, data portability, admin controls). Identifies the strategic market blind spot both analysts missed. Delivers: BUY DECISION (YES/NO/YES WITH CONDITIONS), OVERALL SCORE 1–100, TOP 3 FIXES (ranked, with sprint description, evidence citation, and estimated retention impact), COMPETITIVE POSITIONING.

11. **Streaming delivery** — Each round completion triggers the `task_callback`, which enqueues a JSON message `{round, agent_name, agent_role, content}` onto the asyncio Queue. The WebSocket coroutine forwards each message to the frontend in real time. The verdict is parsed via regex from the Round 4 output and delivered as a final structured `{type: "verdict", score, decision, top_3_fixes, full_report}` message.

---

## Setup & Run

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) for local dev, or vLLM on NVIDIA DGX Spark for production
- ffmpeg (optional, for video ingestion): [ffmpeg.org](https://ffmpeg.org/download.html)
- OpenAI API key (optional, for video frame analysis and screenshot ingestion)
- ChromaDB data: either run the scraping pipeline or obtain `chroma_db/` from the team

### 1. Clone and install

```bash
git clone https://github.com/<your-org>/War-Room.git
cd War-Room
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install crewai chromadb fastapi uvicorn websockets openai pydantic
```

### 2. Set environment variables

```bash
# Required only for video ingestion and screenshot processing
export OPENAI_API_KEY=sk-...

# Windows PowerShell:
$env:OPENAI_API_KEY = "sk-..."
```

### 3a. Local development (Ollama)

```bash
# Pull the model
ollama pull llama3.1:8b

# Verify Ollama is running at http://localhost:11434
ollama list
```

`config.py` defaults to `LOCAL_MODEL = "ollama/llama3.1:8b"` and `LOCAL_BASE_URL = "http://localhost:11434"`. No changes needed for local dev.

### 3b. DGX Spark production (vLLM)

Uncomment the three model lines in `config.py`:

```python
FIRST_TIMER_MODEL = "ollama/llama3.3:70b"   # or vllm model ID
DAILY_DRIVER_MODEL = "ollama/qwen3:32b"
BUYER_MODEL = "ollama/mistral-small:24b"
```

In `crew.py`, swap from `local_llm` to per-model LLMs:

```python
first_timer_llm  = LLM(model=FIRST_TIMER_MODEL,  base_url="http://localhost:8001/v1")
daily_driver_llm = LLM(model=DAILY_DRIVER_MODEL, base_url="http://localhost:8002/v1")
buyer_llm        = LLM(model=BUYER_MODEL,         base_url="http://localhost:8003/v1")
```

### 4. Load ChromaDB (if building from raw data)

```bash
# First, run scrapers in order (requires Reddit/HN API access or cached data):
python scrapers/02_scrape_reddit.py
python scrapers/03_scrape_hackernews.py
python scrapers/04_scrape_appstores.py
python scrapers/06_generate_metadata.py
python scrapers/08_preprocess_chunks.py

# Load into ChromaDB (pm_tools collection, cosine space):
python load_db.py

# Optional: ingest UI screenshots via GPT-4o Vision
python process_screenshots.py
```

Expected output: `31,668 chunks` in the `pm_tools` collection.

### 5. Start the API server

```bash
python api.py
# Server starts at http://0.0.0.0:8000
# WebSocket at ws://localhost:8000/ws/{session_id}
```

### 6. Run a debate (CLI)

```bash
python crew.py
# Enter: Notion — all-in-one workspace for notes, docs, and databases
```

### 7. Run a debate (API)

```bash
# Start debate, get session_id
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "product_description": "Linear — modern issue tracker for software teams",
    "target_user": "10-person engineering team",
    "competitors": "Jira, GitHub Issues",
    "differentiator": "Speed and keyboard-first UX",
    "product_stage": "Growth"
  }'

# Returns: {"session_id": "uuid-here"}

# Connect WebSocket to stream rounds:
# ws://localhost:8000/ws/{session_id}
```

### 8. Run the swarm standalone

```bash
python swarm.py
# Enter product name to see all 20 scout results before the debate
```

---

## Design Decisions

**Why three different model architectures over three instances of the same model:** Running three Llama-70B instances would produce arguments that differ only in sampling temperature — the same model, the same training priors, the same tendency to hedge. Llama 3.3-70B, Qwen3-32B, and Mistral-Small-24B have genuinely different training data distributions, instruction tuning approaches, and attention patterns. When they disagree, the disagreement reflects real architectural divergence, not stochastic variation. The tradeoff is increased inference infrastructure complexity: three separate vLLM server instances vs one. We accept this cost because the output quality difference is not marginal.

**Why CrewAI sequential process over a custom multi-agent loop:** CrewAI's sequential process with `context=[...]` chaining gives us exact control over which prior outputs are injected into each task. The `task_callback` hook gives us round-level streaming over WebSocket without polling. The tradeoff is that CrewAI's ReAct tool-calling loop is unreliable with sub-10B models. We solved this by pre-injecting all RAG evidence into task prompts via `fetch_context_for_product` and swarm briefings — the models argue from evidence in their context window rather than needing to reliably execute tool calls.

**Why ChromaDB over Pinecone or Weaviate:** ChromaDB runs fully locally with `PersistentClient`, requires zero API keys or cloud infrastructure, and supports metadata filtering that maps directly to our source taxonomy (Reddit, HN, Google Play, metadata, screenshots). The tradeoff is that ChromaDB's default embedding model (all-MiniLM-L6-v2) is weaker than OpenAI ada-002 for semantic retrieval on long reviews. We accept this because the source-filtered queries (`where={"source": "reddit"}`) compensate by narrowing the retrieval space to the correct evidence type per agent persona.

**Why dynamic meta-prompt personas over fixed persona templates:** Fixed personas produce identical debate structure regardless of what is being evaluated. A fixed "CTO persona" applied to a solo productivity app is epistemically incoherent — the CTO would not evaluate Obsidian the same way they evaluate Monday.com. The meta-prompt generates personas whose specific churned-tool history, benchmarked competitors, and test workflows are calibrated to the actual product. The tradeoff is one additional LLM call at debate startup and JSON parse failure risk (mitigated by static fallback).

**Why a swarm pre-seeding pass over relying on ReAct tool calls in-debate:** Local LLMs at the 7B–8B parameter scale (used in dev) do not reliably execute multi-step tool-calling ReAct loops. They frequently skip the tool call, hallucinate a result, or call the tool with a malformed query. The swarm deploys 20 parallel queries before the debate starts and injects the results as pre-loaded context — guaranteeing that every agent has real retrieved evidence in its prompt regardless of whether it successfully executes tool calls during its round. The tradeoff is higher initial latency (the swarm adds ~3–8 seconds pre-debate) and increased total ChromaDB query load.

**Why WebSocket streaming over polling or server-sent events:** Each debate round takes 30–120 seconds on local hardware. Polling a `/status` endpoint would introduce latency and unnecessary load. SSE would work but WebSocket was chosen because the React frontend needs bidirectional capability for potential future user-interruption-of-debate features. The tradeoff is slightly more complex connection management (session cleanup on disconnect, asyncio Queue bridge between the thread pool and the event loop).

**Why ffmpeg scene-change detection over uniform-interval frame sampling for video ingestion:** Founder walkthroughs contain long stretches of typing or explanation with no UI change. Uniform frame sampling at 1 fps would produce 60–180 frames for a 2–3 minute video, most of which are near-identical. Scene-change detection (threshold=0.3) extracts only frames where the UI meaningfully changes, yielding 10–30 semantically distinct frames that cover the full product journey with no redundancy. The fallback to `fps=1/2` triggers only if fewer than 5 frames are detected, ensuring robustness to low-contrast videos.

---

## Alignment with yconic Hackathon Themes

**End-to-End Execution:** War Room is not a demo or a proof-of-concept. It is a complete system: a multi-stage data pipeline that scraped and processed 31,668 chunks from five sources, a vector database with production-grade metadata filtering, a CrewAI orchestration layer with four sequential rounds and context chaining, a FastAPI backend with WebSocket streaming, a React frontend for real-time debate visualization, and a video ingestion pipeline powered by GPT-4o Vision. Every component is implemented and connected. The scraping pipeline (`scrapers/`), the ChromaDB loader (`load_db.py`), the debate engine (`crew.py`), the API server (`api.py`), and the frontend all ship together.

**100x Thinking:** The premise of War Room is that one model asking itself hard questions is qualitatively different from three models with conflicting architectures, conflicting personas, and conflicting evidence preferences being forced to argue against each other's actual outputs. The output of a single LLM product review is a summary. The output of War Room is a contested verdict with a paper trail. This is not 1.1x better than GPT-4 with a good prompt. It is a different category of output because the adversarial structure surfaces information that no single model can surface — the specific claim that a power user would dispute, the hidden 6-month problem that a first-timer can't see, the pricing trap that only a buyer's lens reveals.

**Agents That Hire Agents:** War Room's architecture has two layers of agent spawning. The meta-prompt (an LLM call) generates the three adversarial agents that will run the debate — agents creating agents. The swarm module (`swarm.py`) then deploys 20 parallel scout agents to pre-seed those debate agents with evidence. The debate agents themselves have access to 7 CrewAI tool functions for additional retrieval during their rounds. This is a three-tier agent hierarchy: the meta-agent generates the debaters, the swarm pre-scouts for the debaters, and the debaters use RAG tools during the debate itself.

**Let's Cook OpenClaw:** War Room runs three frontier-class open-weight models — Llama 3.3-70B, Qwen3-32B, and Mistral-Small-24B — on NVIDIA DGX Spark hardware at the hackathon venue. No API calls to closed-source providers for the core inference workload. The product evaluations generated by War Room are produced entirely on open-weight models running on open hardware. The video analysis pipeline optionally uses GPT-4o Vision for frame description, but the adversarial debate itself — the core intellectual work of the system — runs on local open-weight inference.

---

## Demo

> Screenshots and demo video coming. Run `python crew.py` to see a full debate in the terminal, or start `python api.py` and open the React frontend for the streaming visualization.

**Sample output structure (Round 4 verdict):**
```
BUY DECISION: YES WITH CONDITIONS
OVERALL SCORE: 67/100

TOP 3 FIXES:
1. [Onboarding] ...
2. [Mobile performance] ...
3. [Export/data portability] ...

COMPETITIVE POSITIONING: ...
```

---

## Team

| Name | Role |
|------|------|
| **Griffin Kovach** | RAG pipeline architecture, ChromaDB data ingestion (scrapers, load_db.py, process_screenshots.py), tools.py, FastAPI/WebSocket backend (api.py), video ingestion pipeline, config |
| **Tucker Anglemyer** | CrewAI orchestration (crew.py), adversarial debate structure, meta-prompt persona generation (meta_prompt.py), swarm reconnaissance (swarm.py), agent prompt engineering, four-round debate design |

Built in 24 hours at the **yconic New England Inter-Collegiate AI Hackathon 2026**.
