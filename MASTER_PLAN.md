# THE WAR ROOM — Master Plan

## Vision
The War Room is an adversarial AI QA testing engine for software products. Three different LLM architectures — Llama 3.3-70B, Qwen3-32B, and Mistral-Small-24B — assume dynamically generated consumer personas and debate a product's strengths and weaknesses across 4 structured rounds, grounded in 31,668 real user reviews from App Store, Reddit, Hacker News, and Google Play. The output is an actionable product teardown with a scored verdict, designed for product teams and shareable on social media.

This is not a chatbot with personas. It is a multi-model adversarial protocol where different AI architectures with different training data reach different conclusions, challenge each other with cited evidence, and converge on a verdict no single model could produce alone.

## Problem Definition
Every AI tool today gives you one model's opinion — one brain, one set of blind spots. Product teams making decisions about their software rely on user research that takes weeks and costs thousands. Individual users evaluating tools have no structured way to stress-test a product before committing. The War Room compresses adversarial product analysis into minutes, grounded in real evidence from thousands of users who already shared their experiences publicly.

The immediate users are product managers and developers evaluating productivity software. The broader application is any domain where decisions benefit from structured multi-perspective debate: healthcare, finance, legal, defense.

## Technical Architecture

### Backend (Python)
- **Meta-Prompt Engine** (`meta_prompt.py`): Takes a product description, sends it to the LLM, and auto-generates 3 adversarial consumer personas as structured JSON. Includes conflict requirements (incompatible priorities), specificity requirements (exact workflows, tools churned from), and evidence preferences (each persona trusts different data sources). Falls back to static personas if generation fails.
- **CrewAI Orchestration** (`crew.py`): Sequential 4-round debate with context chaining. Round 1 (First-Timer analyzes) → Round 2 (Daily Driver challenges with mandatory AGREE/DISAGREE) → Round 3 (First-Timer rebuts with stubbornness rule) → Round 4 (Buyer delivers scored verdict with top 3 fixes). Each agent has max_iter=10 and verbose=True for streaming.
- **RAG Pipeline** (`tools.py`): ChromaDB persistent collection `pm_tools` containing 31,668 pre-embedded chunks with metadata filtering by source (reddit, hackernews, google_play, metadata). 7 tool functions decorated with @tool: `search_pm_knowledge` (general), `search_app_reviews` (google_play filter), `search_reddit` (reddit filter), `search_g2_reviews`, `search_hn_comments` (hackernews filter), `search_competitor_data` (metadata filter), `search_screenshots`. Shared `_query_collection` helper handles formatting per source type.
- **FastAPI Server** (`api.py`): REST endpoint POST `/analyze` to start sessions. WebSocket endpoint `/ws/{session_id}` streaming debate rounds as structured JSON with agent name, role, model, round number, and content. Background thread execution with round-by-round emission.
- **Data Loader** (`load_chunks.py`): One-time ChromaDB ingestion from `all_chunks.json` — deduplication, metadata sanitization, batch embedding (500/batch).

### Frontend (React + TypeScript + Three.js)
- **Three.js Glass Shard**: Refractive IcosahedronGeometry with MeshPhysicalMaterial (transmission 0.95, ior 2.4, chromatic aberration). Three orbiting point lights (chartreuse, white, electric blue). Mouse-reactive tilt with lerped follow. Subtle float oscillation.
- **Landing Page**: Massive "THE WAR ROOM" typography (clamp 48-120px, negative leading 0.85, chartreuse). 5 pre-loaded product buttons (Canvas, Notion, Google Calendar, Asana, Microsoft To Do). Open text input for custom analysis. Zero friction — one click starts a debate.
- **Debate Stream**: Real-time WebSocket connection. Agent persona name, model badge, round number. AGREE/DISAGREE labels color-coded green/red. Agent color coding: First-Timer (chartreuse), Daily Driver (white), Buyer (electric blue). Terminal argument aesthetic.
- **Verdict Card**: Hero score (1-100), buy decision (YES/NO/YES WITH CONDITIONS), top 3 fixes, "Adversarially tested by 3 AI architectures" tagline. Optimized for Instagram story screenshots.
- **Design System**: JetBrains Mono only. Pure black (#000) background. Chartreuse (#E0FB2D) primary. No rounded corners. No gradients on UI. 1px borders. Wide letter-spacing. Brutalist terminal energy.

### Infrastructure
- **Local Dev**: Ollama serving llama3.1:8b on M2 Mac. ChromaDB persistent storage at ./chroma_db.
- **DGX Spark Production**: 128GB unified memory. Three models loaded simultaneously via Ollama or vLLM (Llama 3.3-70B on port 8001, Qwen3-32B on port 8002, Mistral-Small-24B on port 8003). Each agent routes to a different model endpoint.
- **Deployment**: Frontend on Vercel. Backend on DGX Spark (FastAPI + uvicorn). WebSocket bridge.

### Data
- 22,692 Reddit posts/comments from r/productivity, r/notion, r/projectmanagement
- 6,348 Hacker News stories/comments on productivity tools
- 2,608 Google Play reviews
- 20 app overview metadata documents
- Total: 31,668 embedded chunks in ChromaDB with cosine similarity search

## Innovation
1. **Multi-model adversarial debate**: Not one model with different prompts — three fundamentally different architectures (Llama, Qwen, Mistral) with different training data producing genuinely different reasoning. MIT research shows multi-model debate achieves 91% accuracy vs 82% with same-model copies.
2. **Dynamic persona generation**: The meta-prompt creates product-specific personas, not generic templates. Analyzing Notion generates different personas than analyzing Asana.
3. **Structured disagreement protocol**: Mandatory AGREE/DISAGREE labels, stubbornness rules preventing premature concession, confidence scoring, and a buyer who settles disputes with business logic.
4. **Evidence-grounded debate**: 31,668 real user reviews prevent "ChatGPT in a costume" syndrome. Every claim must be backed by searched evidence.

## Scalability Design
- The adversarial debate protocol is product-agnostic. Swap the RAG collection for medical literature and agents become adversarial diagnostic consultants. Swap for legal precedents and agents become opposing counsel. The protocol IS the product.
- ChromaDB collections are modular — add new industries by adding new collections, not new code.
- Anti-SaaS business model: $50 per War Room engagement. Pay for the outcome, not a seat.

## Market Awareness
- Mitsubishi Electric announced in January 2026 the manufacturing industry's first multi-agent AI argumentation framework for expert-level decision-making — validating the exact pattern for industrial applications.
- No existing product combines multi-model debate with RAG-grounded evidence for consumer product QA.
- Competitors: UserTesting ($49/response, human-only), single-model analysis tools (ChatGPT, Perplexity — one perspective only).

## Team Execution Plan
- **Tucker Anglemyer**: CrewAI backend, DGX model serving, FastAPI/WebSocket, React frontend, Three.js hero, pitch delivery
- **Griffin Kovach**: RAG dataset curation (31,668 chunks), ChromaDB ingestion pipeline, tool wiring, data quality

### Milestones
- Hour 0-2: Repo init, DGX signup, local dev environment, first CrewAI test
- Hour 2-4: RAG pipeline connected, tool calls verified with real data
- Hour 4-8: FastAPI + WebSocket layer, frontend landing page with Three.js
- Hour 8-12: End-to-end integration, debate streaming to frontend
- Hour 12-16: DGX window — swap to big models, record demo runs
- Hour 16-20: Polish, traction push (deploy to Vercel, blast socials)
- Hour 20-24: Demo prep, pitch rehearsal, final bug fixes

## Risk Assessment
| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| DGX window too short | Medium | Build everything locally first, DGX is only for model swap |
| WiFi kills model pulling | Medium | Cloud API backup keys (Anthropic, OpenAI) ready in .env |
| Small models skip tool calls | Confirmed | Switched from mistral:7b to llama3.1:8b, aggressive prompt instructions |
| Live demo fails | Medium | Pre-record best demo run as backup video |
| RAG returns irrelevant results | Low | 31,668 chunks with metadata filtering by source type |

## Differentiation Strategy
Every other team at this hackathon will run one model with one prompt. The War Room runs three different architectures that genuinely disagree, challenge each other with cited evidence from real users, and converge on an answer none of them could reach alone. The DGX Spark enables this — 128GB unified memory serving three large models simultaneously with zero API limits and zero data leakage. This cannot be replicated with cloud APIs at any reasonable cost.
