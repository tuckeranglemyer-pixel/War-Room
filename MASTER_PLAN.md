# THE WAR ROOM — Master Plan

## Vision
The War Room is an adversarial AI QA testing engine that replaces $200K consulting engagements with 4 minutes of multi-model debate. A reconnaissance swarm of 20+ parallel scout agents sweeps a knowledge base of 31,668 real user reviews. Then three different LLM architectures assume dynamically generated consumer personas and debate the product's strengths and weaknesses across 4 structured rounds, each grounded in real cited evidence. The output is an actionable product teardown with a scored verdict — designed for product teams, shareable on social media, and structured as sprint-ready tickets.

This is a three-layer orchestration system: a meta-agent generates adversarial personas, a swarm of scouts gathers intelligence, and three expert architectures debate the findings — challenging each other with cited evidence and converging on a verdict no single model could produce alone.

## Problem Definition
**Who experiences this:** Product managers, founders, and development teams evaluating or improving software products. Secondary users: investors conducting due diligence, competitors benchmarking alternatives.

**The specific pain:** Product teams making decisions about their software rely on user research that takes 2-6 weeks and costs $5K-$200K (UserTesting charges $49/response; McKinsey charges $200K+ for a competitive analysis). Individual users evaluating tools have no structured way to stress-test a product before committing their team's workflow to it.

**How many people:** There are 33.2 million small businesses in the US alone, each evaluating an average of 3-5 SaaS tools per year. The product analytics and user research market is $4.2B and growing 18% annually.

**The gap:** Every AI tool today gives you one model's opinion — one brain, one set of blind spots. No existing solution combines multi-model adversarial debate with evidence-grounded RAG analysis to produce a structured, cited, actionable teardown.

## User Impact
- **Time savings:** 4 minutes vs 2-6 weeks of traditional user research
- **Cost savings:** ~$3 per analysis vs $5K-$200K for equivalent consulting output
- **Quality improvement:** Evidence cited from 31,668 real user reviews vs anecdotal feedback
- **Actionability:** Output structured as PM sprint tickets with estimated retention impact percentages
- **Accessibility:** Any founder or PM can run adversarial QA — not just companies that can afford McKinsey

## Technical Architecture

### Layer 1 — Meta-Agent: Dynamic Persona Generation (`meta_prompt.py`)
Takes a product description, sends it to the LLM, and auto-generates 3 adversarial consumer personas as structured JSON. Includes:
- **Conflict requirements:** incompatible priorities between personas — what one considers essential, another considers bloat
- **Specificity requirements:** exact workflows, tools churned from, specific past frustrations
- **Evidence preferences:** each persona trusts different data sources (App Store vs G2 vs HN)
- **Archetype coverage:** First-Timer (onboarding), Daily Driver (depth/reliability), Buyer (team adoption)
- **Graceful degradation:** falls back to static personas if generation fails

### Layer 2 — Reconnaissance Swarm (`swarm.py`)
Before the debate begins, 20+ parallel scout agents sweep the entire knowledge base using Python's ThreadPoolExecutor. Each scout targets a different product dimension:
- Onboarding friction, pricing, mobile experience, integrations, reliability
- Customer support, competitor comparisons, missing features, UI/UX, collaboration
- Data portability, notifications, search, offline access, learning curve
- Security, customization, automation, paywall analysis, version history

The swarm compiles findings into a structured Intelligence Briefing injected into Round 1. Scouts run in parallel (10 workers default, scales to 50+ on DGX). Evidence is pre-gathered so debate agents argue over real patterns — not cold-start searches.

### Layer 3 — Adversarial Debate Engine (`crew.py`)
CrewAI sequential 4-round debate with full context chaining:

- **Round 1 — Initial Analysis (First-Timer):** Evaluates onboarding, finds 3 critical problems with severity ratings 1-10, competitor comparisons, cited evidence from swarm briefing + independent searches
- **Round 2 — Challenge (Daily Driver):** Mandatory AGREE/DISAGREE on each finding. Must disagree with at least one, agree+escalate at least one. Exposes 2 hidden long-term problems. Challenges competitor recommendation
- **Round 3 — Rebuttal (First-Timer):** Defends or concedes with stubbornness rule — no concession without specific counter-evidence. "You get used to it" is an admission of failure, not a defense. Updated severity ratings
- **Round 4 — Verdict (Buyer):** Settles all disagreements with business logic. Assesses pricing, integrations, data portability, admin controls. Identifies strategic market blind spot. Delivers: YES/NO/YES WITH CONDITIONS, score 1-100, top 3 fixes as sprint tickets with estimated retention impact

Context chaining: R1 feeds R2, R1+R2 feed R3, R1+R2+R3 feed R4. Each round builds on all previous arguments.

### RAG Pipeline (`tools.py`)
ChromaDB persistent collection `pm_tools` with 31,668 pre-embedded chunks and metadata filtering:
- 22,692 Reddit posts/comments from r/productivity, r/notion, r/projectmanagement, r/PKMS, r/selfhosted
- 6,348 Hacker News stories/comments
- 2,608 Google Play reviews with star ratings
- 89 app metadata documents + UI screenshots (chunked and analyzed)

7 tool functions with shared `_query_collection` helper enabling source-specific filtering. Cosine similarity search with configurable result count.

### API Layer (`api.py`)
FastAPI server with:
- `POST /analyze` — accepts product description, returns session_id
- `WS /ws/{session_id}` — streams debate rounds as structured JSON (agent name, role, model, round number, content)
- Background thread execution with `asyncio.Queue` bridge for sync→async streaming
- Automatic verdict parsing with regex extraction of score, decision, and fixes
- Session management for concurrent analyses

### Frontend (`frontend/` — React + TypeScript + Vite)
- **Landing:** Minimal input-centered design. Single text field with animated gradient border on focus. Product suggestions (Canvas, Notion, Google Calendar, Asana, Microsoft To Do). Spring-physics animations via framer-motion
- **Debate Stream:** Real-time WebSocket rendering. Swarm reconnaissance counter → Agent initialization sequence (three engines powering up) → Round cards with typewriter effect → AGREE/DISAGREE badges → Source citation pills → Progress bar tracking rounds
- **Verdict Card:** Animated score ring (SVG), verdict badge (color-coded), priority fixes with retention impact estimates, share functionality
- **Demo Fallback:** Hardcoded 4-round debate with typewriter animation activates if backend is unavailable — demo always works
- **Design System:** Inter + JetBrains Mono. Near-black (#0A0B0F) background. Blue (#3B82F6) accent used sparingly. 8px spacing scale. Restrained, data-dense, professional

### Infrastructure
- **Local Dev:** Ollama serving llama3.1:8b on M2 Mac. ChromaDB persistent storage
- **Production:** Hybrid cloud + edge architecture. Cloud LLMs (Claude Sonnet, GPT-4o) for reliable high-quality inference. NVIDIA DGX Spark (128GB unified memory) for local-only deployments requiring zero data leakage
- **Deployment:** Frontend on Vercel (CDN). Backend deployable on any server with Python 3.12+
- **Model-agnostic:** config.py centralizes all model assignments — swap between local Ollama, cloud APIs, or vLLM endpoints by changing 3 lines

## Innovation
1. **Three-layer orchestration:** Meta-agent → Swarm reconnaissance → Expert debate. Agents that deploy other agents that feed expert agents. Maps to yconic's "Agents That Hire Agents" thesis
2. **Multi-model adversarial debate:** Different architectures with different training data produce genuinely different reasoning. MIT research shows multi-model debate achieves 91% accuracy vs 82% with same-model copies
3. **Reconnaissance swarm:** 20+ parallel scouts pre-gather evidence across 20 product dimensions before debate begins. Eliminates cold-start problem
4. **Dynamic persona generation:** Product-specific personas generated per analysis — not static templates. Analyzing Notion creates different archetypes than analyzing Asana
5. **Structured disagreement protocol:** Mandatory AGREE/DISAGREE labels, stubbornness rules preventing premature concession, confidence scoring, buyer settlement with business logic
6. **Evidence-grounded debate:** Every claim backed by cited evidence from 31,668 real user reviews. No hallucinated opinions

## Ecosystem Thinking
- **API-first design:** Every capability exposed via REST + WebSocket. Third-party integrations can trigger analyses programmatically
- **Plugin architecture for RAG collections:** Add new industries by dropping a new ChromaDB collection — healthcare reviews, legal precedents, financial filings. Zero code changes to the debate engine
- **Model-agnostic orchestration:** The debate protocol works with any LLM backend — Ollama, vLLM, OpenAI, Anthropic, Gemini. `config.py` makes swapping a 3-line change
- **Output interoperability:** Verdict JSON exports directly to Jira, Linear, Asana via structured ticket format. Score + fixes are machine-readable for CI/CD integration
- **Embeddable widget:** The frontend is a standalone React app deployable as an iframe widget inside any product dashboard
- **MCP-ready:** Architecture is designed for Model Context Protocol integration — each tool function maps 1:1 to an MCP tool definition for cross-platform agent interoperability

## Scalability Design
- **Vertical scaling:** The adversarial debate protocol is product-agnostic. Swap RAG collections to enter any vertical:
  - Medical literature → diagnostic debate between specialist AI personas
  - Legal precedents → opposing counsel simulation
  - Financial reports → investment committee deliberation
  - Security audits → red team vs blue team analysis
- **Horizontal scaling:** Swarm scales linearly with compute. FastAPI handles concurrent sessions via background threads
- **Data scaling:** ChromaDB collections are modular and independently embeddable. Current: 31,668 chunks across 20 productivity tools. Target: 500K+ chunks across 50 verticals
- **Business model:** Anti-SaaS. $50 per War Room engagement. Pay for the outcome, not a seat. Zero recurring cost for users who don't need ongoing analysis

## Market Awareness
- **Validation:** Mitsubishi Electric (January 2026) announced the manufacturing industry's first multi-agent AI argumentation framework for expert-level decision-making — independently validating the adversarial debate pattern
- **Competitive landscape:**
  - UserTesting: $49/response, human-only, 2-5 day turnaround. War Room: ~$3, AI-powered, 4 minutes
  - ChatGPT/Claude/Perplexity: single-model, no structured disagreement, no evidence grounding, no persistence
  - G2/Capterra: Aggregated reviews with no adversarial analysis or actionable output
- **Market size:** Product analytics and user research: $4.2B growing 18% YoY. Adjacent: management consulting ($300B) where AI-powered analysis displaces junior analyst work
- **Positioning:** The War Room sits at the intersection of AI-powered research and consulting automation — a category that doesn't exist yet

## Team Execution Plan
- **Tucker Anglemyer** (Accounting & Finance, Providence College): CrewAI backend, swarm engine, model configuration, FastAPI/WebSocket, React frontend, demo delivery. Built Untracked (60K lines, solo, 2 months). PwC internship 2027
- **Griffin Kovach** (Founder, Clerion AI, Providence College): RAG dataset curation (31,668 chunks across 20 apps), ChromaDB ingestion pipeline, tool wiring with metadata filtering, data quality assurance. Built Clerion's RAG system for Canvas LMS

### Milestones
| Hour | Milestone | Status |
|------|-----------|--------|
| 0-2 | Repo init, local dev env, first CrewAI 4-round test | ✅ Complete |
| 2-4 | RAG pipeline connected, tool calls verified with real data | ✅ Complete |
| 4-8 | FastAPI + WebSocket layer, frontend landing page | ✅ Complete |
| 8-12 | End-to-end integration, swarm visualization, debate streaming | ✅ Complete |
| 12-16 | DGX deployment, cloud API integration, scale testing | 🔄 In Progress |
| 16-20 | Polish, traction push, deploy to Vercel, social distribution | ⬜ Planned |
| 20-24 | Demo prep, pitch rehearsal, backup video, final fixes | ⬜ Planned |

## Risk Assessment
| Risk | Likelihood | Mitigation | Status |
|------|-----------|------------|--------|
| DGX thermal throttling | Confirmed | Cloud API fallback (Claude + GPT-4o) provides equivalent output quality | ✅ Mitigated |
| WiFi blocks SSH to DGX | Confirmed | Direct monitor access + GitHub push/pull workflow | ✅ Mitigated |
| Small models skip tool calls | Confirmed | Pre-seeded context injection guarantees real evidence regardless of model | ✅ Mitigated |
| Live demo fails | Medium | Hardcoded demo fallback with typewriter animation built into frontend | ✅ Mitigated |
| RAG returns irrelevant results | Low | 31,668 chunks with metadata filtering by source type | ✅ Mitigated |
| Swarm returns empty | Low | Debate runs identically without swarm — graceful degradation | ✅ Mitigated |

## Responsible AI & Ethics
- **No hallucinated evidence:** Every claim in the debate must be backed by cited evidence from the RAG knowledge base. Agents are prompted with "ONLY cite evidence from the knowledge base — do not invent usernames or URLs"
- **Transparent disagreement:** AGREE/DISAGREE labels make model reasoning visible and auditable. Users see exactly where models diverge and why
- **No vendor manipulation:** The system evaluates products adversarially — it cannot be paid to produce favorable results. The buyer persona is structurally incentivized to find flaws
- **Data provenance:** All 31,668 review chunks are sourced from public platforms (Reddit, HN, Google Play) with URLs preserved. No scraped private data
- **Model transparency:** Each agent's underlying model architecture is displayed in the UI. Users know which AI produced which argument
- **Bias mitigation through adversarial structure:** Single-model analysis inherits that model's training biases. Multi-model debate forces models to challenge each other's assumptions, surfacing blind spots that any individual model would miss

## Traction Strategy
- **Hackathon floor (Saturday):** Offer every competing team a free War Room analysis of their product. Each run = a tracked user. Target: 15+ teams
- **Social distribution (Saturday night):** Deploy frontend to Vercel. Run War Room on Canvas (every college student's most-hated app). Screenshot the sharpest finding. Post to Instagram story with link. Target: 200+ link clicks from PC student network
- **Group chat seeding:** Drop the Vercel link in 5+ group chats with the hook: "We built something that tells you everything wrong with [Notion/Canvas/Asana] in 4 minutes"
- **Reddit distribution:** Post to r/productivity, r/notion, r/SaaS with genuine value — "We analyzed Notion with 3 AI models debating 31,668 real reviews. Here's what they found"
- **Metrics to show judges:** Total sessions run, unique users, most-analyzed product, average session duration, screenshots of social engagement
- **Retention hook:** "The first time you use it, you learn what's wrong with the app you use today. You come back when you're evaluating a NEW tool — you run it through the War Room before you commit"

## Technical Performance Metrics
- **RAG retrieval:** Cosine similarity search returns top-5 results per query in <50ms on ChromaDB with 31,668 chunks
- **Swarm execution:** 20 parallel scouts complete in 6-12 seconds (ThreadPoolExecutor with 10 workers)
- **Debate generation:** Full 4-round debate completes in 8-15 minutes on DGX Spark with three 70B-class models, or 3-5 minutes per round on cloud inference
- **Memory allocation on DGX:** Llama 3.3-70B (42GB) + Qwen3-32B (20GB) + Mistral-Small-24B (14GB) = 76GB of 128GB unified memory utilized
- **Frontend streaming:** WebSocket delivers round output in <100ms from completion to browser render
- **Pre-seeded context:** Each agent receives 10 RAG results (fetched at crew build time) injected directly into task descriptions — guarantees evidence usage regardless of model tool-calling reliability

## Differentiation Strategy
Every other team at this hackathon will run one model with one prompt. The War Room deploys a reconnaissance swarm of 20+ scouts to pre-gather intelligence from 31,668 real user reviews, then runs three different AI architectures that genuinely disagree, challenge each other with cited evidence, and converge on a scored verdict with actionable fixes. The output is structured as sprint-ready tickets — not a chatbot response. The architecture is model-agnostic and vertical-agnostic: swap the RAG collection, and the same adversarial protocol analyzes healthcare, finance, legal, or defense decisions. We didn't build an app. We built the peer review layer for artificial intelligence.
