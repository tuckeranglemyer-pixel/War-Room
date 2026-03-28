# THE WAR ROOM — Master Plan

## Vision
The War Room is an adversarial AI QA testing engine for software products. A reconnaissance swarm of 20+ parallel scout agents first sweeps a knowledge base of 31,668 real user reviews, gathering evidence across every product dimension. Then three different LLM architectures — Llama 3.3-70B, Qwen3-32B, and Mistral-Small-24B — assume dynamically generated consumer personas and debate the product's strengths and weaknesses across 4 structured rounds, grounded in the swarm's evidence and their own independent searches. The output is an actionable product teardown with a scored verdict, designed for product teams and shareable on social media.

This is not a chatbot with personas. It is a three-layer orchestration system: a meta-agent generates adversarial personas, a swarm of scouts gathers intelligence, and three expert architectures debate the findings — challenging each other with cited evidence and converging on a verdict no single model could produce alone.

## Problem Definition
Every AI tool today gives you one model's opinion — one brain, one set of blind spots. Product teams making decisions about their software rely on user research that takes weeks and costs thousands. Individual users evaluating tools have no structured way to stress-test a product before committing. The War Room compresses adversarial product analysis into minutes, grounded in real evidence from thousands of users who already shared their experiences publicly.

The immediate users are product managers and developers evaluating productivity software. The broader application is any domain where decisions benefit from structured multi-perspective debate: healthcare, finance, legal, defense.

## Technical Architecture

### Layer 1 — Meta-Agent: Dynamic Persona Generation (`meta_prompt.py`)
Takes a product description, sends it to the LLM, and auto-generates 3 adversarial consumer personas as structured JSON. Includes conflict requirements (incompatible priorities), specificity requirements (exact workflows, tools churned from), and evidence preferences (each persona trusts different data sources). Falls back to static personas if generation fails.

### Layer 2 — Reconnaissance Swarm (`swarm.py`)
Before the debate begins, 20+ parallel scout agents sweep the entire knowledge base using Python's ThreadPoolExecutor. Each scout targets a different product dimension: onboarding, pricing, mobile experience, integrations, reliability, customer support, competitor comparisons, missing features, UI/UX, collaboration, data portability, notifications, search, offline access, learning curve, security, customization, automation, and paywall analysis.

The swarm compiles its findings into a structured Intelligence Briefing that feeds directly into Round 1 as pre-gathered evidence. This ensures the expert debate agents argue over real patterns found across thousands of reviews — not from cold-start searches.

On DGX Spark, the swarm scales to 50+ scouts with dedicated workers per model. On local dev, 20 scouts run in 10 parallel threads against ChromaDB.

### Layer 3 — Adversarial Debate Engine (`crew.py`)
CrewAI sequential 4-round debate with context chaining:
- **Round 1 — Initial Analysis (First-Timer)**: Evaluates onboarding, finds 3 critical problems backed by swarm evidence + independent tool searches. Severity ratings 1-10, competitor comparisons.
- **Round 2 — Challenge (Daily Driver)**: Mandatory AGREE/DISAGREE on each finding with cited counter-evidence. Exposes 2 hidden long-term problems. Challenges competitor recommendation.
- **Round 3 — Rebuttal (First-Timer)**: Defends or concedes with stubbornness rule — no concession without specific counter-evidence. "You get used to it" is an admission of failure, not a defense. Updated severity ratings.
- **Round 4 — Verdict (Buyer)**: Settles all disagreements. Business-critical assessment (pricing, integrations, data portability, admin). Identifies strategic blind spot. Final score 1-100, YES/NO/YES WITH CONDITIONS, top 3 fixes as actionable product tickets with estimated retention impact.

Each agent has max_iter=10. All agents use `search_pm_knowledge` tool with mandatory tool-use instructions in both backstory and task descriptions.

### RAG Pipeline (`tools.py`)
ChromaDB persistent collection `pm_tools` containing 31,668 pre-embedded chunks with metadata filtering:
- 22,692 Reddit posts/comments (r/productivity, r/notion, r/projectmanagement)
- 6,348 Hacker News stories/comments
- 2,608 Google Play reviews
- 20 app overview metadata documents

7 tool functions with shared `_query_collection` helper: `search_pm_knowledge` (general), `search_app_reviews` (google_play filter), `search_reddit` (reddit filter), `search_g2_reviews`, `search_hn_comments` (hackernews filter), `search_competitor_data` (metadata filter), `search_screenshots`.

### API Layer (`api.py`)
FastAPI server with REST endpoint POST `/analyze` and WebSocket `/ws/{session_id}` streaming debate rounds as structured JSON (agent name, role, model, round number, status, content). Background thread execution with round-by-round emission.

### Frontend (React + TypeScript + Three.js)
- **Three.js Glass Shard**: Refractive IcosahedronGeometry (MeshPhysicalMaterial, transmission 0.95, ior 2.4) with three orbiting point lights (chartreuse, white, electric blue). Mouse-reactive tilt. Full-viewport background.
- **Landing Page**: Massive "THE WAR ROOM" typography (clamp 48-120px, negative leading). 5 pre-loaded product buttons (Canvas, Notion, Google Calendar, Asana, Microsoft To Do). Custom input for any product.
- **Swarm Visualization**: Animated counter showing scouts deploying and evidence accumulating before debate begins.
- **Debate Stream**: Real-time WebSocket. Agent color coding (chartreuse/white/blue). AGREE/DISAGREE labels. Terminal argument aesthetic.
- **Verdict Card**: Hero score, buy decision, top 3 fixes. Instagram story screenshot optimized.
- **Design System**: JetBrains Mono only. Black #000. Chartreuse #E0FB2D. No rounded corners. No gradients. 1px borders. Brutalist terminal energy.

### Infrastructure
- **Local Dev**: Ollama serving llama3.1:8b on M2 Mac. ChromaDB at ./chroma_db.
- **DGX Spark Production**: 128GB unified memory. Three models simultaneously — Llama 3.3-70B, Qwen3-32B, Mistral-Small-24B via Ollama or vLLM on separate ports. Swarm scales to 50+ scouts.
- **Deployment**: Frontend on Vercel. Backend on DGX Spark (FastAPI + uvicorn).

## Innovation
1. **Three-layer orchestration**: Meta-agent → Swarm reconnaissance → Expert debate. Not just multi-agent — it's agents that deploy other agents that feed expert agents. Maps to yconic's "Agents That Hire Agents" thesis.
2. **Multi-model adversarial debate**: Three fundamentally different architectures (Llama, Qwen, Mistral) with different training data. MIT research shows multi-model debate achieves 91% accuracy vs 82% with same-model copies.
3. **Reconnaissance swarm**: 20+ parallel scouts sweep 31,668 documents before debate begins, ensuring expert agents argue over real patterns — not from cold starts.
4. **Dynamic persona generation**: Product-specific personas, not templates. Different products generate different archetypes.
5. **Structured disagreement protocol**: Mandatory AGREE/DISAGREE, stubbornness rules, confidence scoring, buyer settlement.
6. **Evidence-grounded debate**: Every claim backed by searched evidence from real user reviews.

## Scalability Design
- The adversarial debate protocol is product-agnostic. Swap RAG collections to enter any vertical: medical literature → diagnostic debate, legal precedents → opposing counsel, financial reports → investment committee.
- Swarm scales linearly with compute — DGX Spark's 128GB memory supports 50+ concurrent scout processes.
- ChromaDB collections are modular. New industries = new collections, same code.
- Anti-SaaS business model: $50 per War Room engagement. Pay for the outcome, not a seat.

## Market Awareness
- Mitsubishi Electric (January 2026): First manufacturing multi-agent AI argumentation framework for expert-level decision-making — validates the exact adversarial debate pattern for industrial applications.
- No existing product combines multi-model debate + swarm reconnaissance + RAG-grounded evidence for consumer product QA.
- Competitors: UserTesting ($49/response, human-only, days of turnaround), single-model tools (ChatGPT, Perplexity — one perspective, no structured disagreement).

## Team Execution Plan
- **Tucker Anglemyer** (Accounting & Finance, Providence College): CrewAI backend, swarm engine, DGX model serving, FastAPI/WebSocket, React frontend, Three.js hero, pitch delivery
- **Griffin Kovach** (Founder, Clerion AI): RAG dataset curation (31,668 chunks), ChromaDB ingestion, tool wiring, data quality assurance

### Milestones
| Hour | Milestone |
|------|-----------|
| 0-2 | Repo init, local dev env, first CrewAI 4-round test passing |
| 2-4 | RAG pipeline connected, tool calls verified with real data, swarm deployed |
| 4-8 | FastAPI + WebSocket layer, frontend landing page with Three.js shard |
| 8-12 | End-to-end integration, debate streaming to frontend, swarm visualization |
| 12-16 | DGX window — swap to big models, scale swarm to 50, record demo runs |
| 16-20 | Polish, traction push (deploy to Vercel, blast socials, hackathon floor outreach) |
| 20-24 | Demo prep, pitch rehearsal, backup video, final bug fixes |

## Risk Assessment
| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| DGX window too short | Medium | Everything built/tested locally first, DGX only for model swap |
| WiFi kills model pulling | Medium | Cloud API backup keys (Anthropic, OpenAI) ready in .env |
| Small models skip tool calls | Confirmed | Switched to llama3.1:8b, mandatory tool-use instructions in prompts |
| Swarm returns empty results | Low | Debate runs identically without swarm — graceful degradation |
| Live demo fails | Medium | Pre-record best demo run as backup video |
| RAG returns irrelevant results | Low | 31,668 chunks with metadata filtering by source type |

## Differentiation Strategy
Every other team at this hackathon will run one model with one prompt. The War Room deploys a swarm of 20+ scouts to pre-gather intelligence, then runs three different AI architectures that genuinely disagree, challenge each other with cited evidence from 31,668 real reviews, and converge on an answer none of them could reach alone. The DGX Spark enables this — 128GB unified memory serving three large models simultaneously with a scaled reconnaissance swarm, zero API limits, and zero data leakage. This cannot be replicated with cloud APIs at any reasonable cost.
