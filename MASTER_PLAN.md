# The War Room — Hackathon Master Plan

## 1. Vision Clarity

**Vision Statement:** To eliminate the information asymmetry between software product teams and their users by orchestrating adversarial multi-model AI debate grounded in real user evidence, compressing weeks of qualitative research into minutes of structured, cited, actionable analysis.

**North Star Metric (NSM):** Total actionable findings per analysis — defined as the number of evidence-cited, severity-rated, sprint-ready product fixes delivered per War Room session. This NSM directly quantifies value transfer to the end user, serving as the primary leading indicator for sustainable platform adoption and repeat engagement.

**Strategic Direction:** All engineering effort is anchored on maximizing the NSM. The reconnaissance swarm pre-gathers evidence to increase finding density. The adversarial debate protocol forces disagreement to surface non-obvious findings. The structured verdict format ensures every finding is immediately actionable. Each architectural decision traces back to producing more cited, higher-quality findings per session.

## 2. Technical Depth

**System Architecture:** The platform utilizes an event-driven, layered orchestration architecture strictly decoupling persona generation, evidence retrieval, adversarial reasoning, and presentation rendering into independent, composable modules.

**Orchestration Layer:** CrewAI manages a sequential four-round debate pipeline with full context chaining (R1→R2, R1+R2→R3, R1+R2+R3→R4). Each round is assigned to an independent LLM instance with isolated system prompts, enforcing genuine multi-model reasoning divergence. Agent configuration: `max_iter=10`, `verbose=True`, mandatory tool-use instructions embedded in both agent backstory and task description.

**Data Model & Storage:** Evidence is stored in a ChromaDB persistent vector database containing 31,737 pre-embedded document chunks. Cosine similarity search with configurable `n_results` enables sub-50ms retrieval. Metadata schema enforces source-type filtering (`source: reddit | hackernews | google_play | metadata | screenshot`) with secondary fields for `app`, `subreddit`, `url`, and `rating`. A shared `_query_collection(query, n_results, where)` helper abstracts all retrieval operations, enforcing consistent formatting per source type.

**API & System Design:** FastAPI serves a REST endpoint (`POST /analyze`) returning a `session_id`, paired with a WebSocket endpoint (`WS /ws/{session_id}`) for real-time round-by-round streaming. Synchronous CrewAI execution is bridged to asynchronous WebSocket delivery via `asyncio.Queue` within a `ThreadPoolExecutor`, ensuring non-blocking concurrent session support. Automatic verdict parsing extracts score (regex 1-100), decision (YES/NO/CONDITIONS), and fixes from Round 4 raw text. Circuit-breaker pattern: if WebSocket disconnects, the frontend activates a hardcoded demo fallback, guaranteeing graceful degradation of the user experience.

**Inference Layer (NVIDIA DGX Spark):** Three LLM architectures served simultaneously via Ollama on 128GB unified memory — Llama 3.3-70B (42GB, First-Timer agent), Qwen3-32B (20GB, Daily Driver agent), Mistral-Small-24B (14GB, Buyer agent). Total utilization: 76GB/128GB. Zero API dependencies. Zero data egress. Complete computational sovereignty.

## 3. Innovation

**Baseline Paradigm:** Traditional product QA relies on single-model AI analysis (ChatGPT, Claude, Perplexity) that produces one perspective with no structured disagreement, no evidence grounding, and no adversarial challenge. Enterprise alternatives (McKinsey, UserTesting) require weeks and $5K-$200K for equivalent qualitative coverage.

**Novel Architectural Shift:** The War Room introduces a novel recombination of three independent technologies — multi-model adversarial debate (Du et al., 2023), parallel reconnaissance swarm retrieval, and dynamic persona generation — into a first-principles orchestration protocol that bypasses the single-model constraint entirely. Instead of asking one AI for an opinion, the system:
1. Auto-generates product-specific adversarial personas via meta-agent (not static templates — analyzing Notion produces fundamentally different archetypes than analyzing Asana)
2. Deploys 20+ parallel scout agents that sweep 31,737 evidence chunks across 20 product dimensions in 6-12 seconds, pre-gathering intelligence before debate begins
3. Routes each persona to a different LLM architecture (Llama/Qwen/Mistral) with different training data and different reasoning patterns, producing genuinely divergent analysis
4. Enforces structured disagreement via mandatory AGREE/DISAGREE labels, a stubbornness rule preventing premature concession, and a buyer settlement round that resolves disputes with business logic

This three-layer orchestration (Meta-Agent → Swarm → Debate) implements the "Agents That Hire Agents" paradigm: agents that generate other agents that deploy scout agents that feed expert agents. MIT research demonstrates multi-model debate achieves 91% factual accuracy versus 82% with same-model copies. Mitsubishi Electric independently validated this adversarial debate pattern for manufacturing QA in January 2026.

## 4. Feasibility

**In-Scope MVP (24 hours):**
1. Meta-agent persona generation with JSON parsing and static fallback
2. 20-agent parallel reconnaissance swarm against ChromaDB (31,737 pre-embedded chunks)
3. Four-round sequential CrewAI debate with context chaining across three LLM backends
4. FastAPI REST + WebSocket streaming server with session management
5. React + TypeScript frontend with landing page, live debate stream, and verdict card
6. Demo fallback mode: hardcoded 4-round debate with typewriter animation if backend unavailable
7. Vercel deployment for traction distribution

**Strictly Out-of-Scope:** Custom model training, mobile application, user authentication, payment processing, custom embedding models. All excluded to protect the 24-hour critical path.

**Leveraged Assets:** Pre-trained open-weight models via Ollama (zero training cost). ChromaDB for managed vector storage (zero infrastructure). CrewAI for agent orchestration (off-the-shelf). Vite + React for rapid frontend prototyping. Framer-motion for production-quality animations. 31,737 pre-curated evidence chunks from public platforms (Reddit, HN, Google Play).

**Resource Alignment:** Two-person team with complementary non-overlapping domains — Tucker owns orchestration + frontend + API; Griffin owns RAG data + ChromaDB pipeline + tool functions. API contract (`POST /analyze`, `WS /ws/{session_id}`) established at Hour 0, unblocking fully parallel asynchronous development from Hour 1 forward.

## 5. Scalability Design

**Compute Scaling:** The application layer is entirely stateless. FastAPI serves concurrent sessions via isolated `ThreadPoolExecutor` workers, each maintaining independent `asyncio.Queue` bridges. This architecture allows horizontal scaling via container orchestration — adding capacity requires deploying additional stateless API instances behind a load balancer with zero shared state.

**Data Scaling:** ChromaDB collections are modular and independently embeddable. Current deployment: 31,737 chunks across 20 productivity tools. Scaling to 500K+ chunks across 50 verticals requires only data ingestion — zero code changes to the debate engine. Each vertical (healthcare, legal, finance) is a self-contained collection that plugs into the identical orchestration protocol.

**Inference Scaling:** The DGX Spark's 128GB unified memory currently serves three models simultaneously (76GB utilized). Vertical scaling: larger quantizations or additional models within remaining headroom. Horizontal scaling: vLLM multi-GPU serving with dedicated ports per model enables independent throughput scaling per agent architecture.

**Network Resilience:** WebSocket streaming decouples frontend rendering from backend computation. If inference latency spikes, the frontend displays a progress animation (swarm counter, agent initialization sequence) that absorbs wait time without degrading perceived performance. If backend fails entirely, the demo fallback activates automatically — the system never presents a broken state to the user.

## 6. Ecosystem Thinking

**Interoperability Standards:** All system capabilities are exposed via a fully documented REST + WebSocket interface. `POST /analyze` triggers the complete pipeline programmatically. `WS /ws/{session_id}` streams structured JSON (agent name, role, model, round number, content) enabling any third-party client to consume debate output in real-time.

**Extensibility Protocols:** The architecture implements a plugin model at three layers:
1. **RAG Collections:** Add new industries by adding ChromaDB collections. Healthcare reviews, legal precedents, financial filings — each is a drop-in collection requiring zero code changes to the debate engine
2. **Agent Roles:** New personas (Security Auditor, Accessibility Reviewer, Performance Engineer) can be added as additional debate rounds without modifying existing agents. The meta-agent dynamically generates role-appropriate personas per domain
3. **Model Backends:** `config.py` centralizes all model assignments. Swapping between Ollama local, vLLM distributed, or any OpenAI-compatible API endpoint requires changing 3 configuration variables

**Output Interoperability:** Verdict JSON schema maps directly to Jira/Linear/Asana ticket format — score, severity, description, and estimated retention impact are machine-readable fields. CI/CD pipelines can consume War Room output as automated quality gates.

**Forward Compatibility:** Each `@tool` function in `tools.py` maps 1:1 to a Model Context Protocol (MCP) tool definition, ensuring cross-platform agent interoperability as the MCP ecosystem matures. The frontend is a standalone React application deployable as an embeddable iframe widget inside any product dashboard.

## 7. Problem Definition

**Target Persona:** Product managers, founders, and development teams at SaaS companies (10-500 employees) evaluating, improving, or benchmarking software products. Secondary: investors conducting technical due diligence, competitors benchmarking alternatives.

**Friction Point:** Product teams making decisions about their software face a critical workflow bottleneck: synthesizing fragmented user feedback scattered across App Store reviews, Reddit threads, HN discussions, and support tickets into coherent, actionable product strategy. This synthesis currently requires manual qualitative research taking 2-6 weeks and costing $5K-$200K.

**Quantified Cost:** UserTesting charges $49 per individual response with 2-5 day turnaround. McKinsey charges $200K+ for a competitive product analysis over 6-12 weeks. Internal research teams spend an average of 40+ hours per product evaluation cycle. Total addressable market: product analytics and user research ($4.2B, growing 18% YoY). Adjacent market: management consulting ($300B) where AI-powered analysis displaces junior analyst work.

**Root Cause:** Existing AI tools (ChatGPT, Claude, Perplexity) provide single-model, single-perspective analysis with no structured disagreement protocol, no evidence grounding in real user data, and no actionable output format. The root cause is architectural: one model cannot adversarially challenge its own assumptions.

## 8. User Impact

**Beneficiary Scale:** Any product team at the 33.2 million small businesses in the US evaluating 3-5 SaaS tools annually. Immediate hackathon audience: 78 teams + their extended networks (~2,000 college students using Canvas, Notion, and Google Calendar daily).

**Projected Operational Delta:**

| Metric | Current Baseline | With War Room | Improvement |
|--------|-----------------|---------------|-------------|
| Research cycle time | 2-6 weeks | 4 minutes | 2,500x reduction |
| Cost per analysis | $5,000-$200,000 | $0 (local compute) | 100% cost elimination |
| Evidence sources synthesized | 10-50 interviews | 31,737 real reviews | 633x data coverage |
| Analytical perspectives | 1 (single consultant/model) | 3 adversarial architectures | 3x perspective coverage |
| Output actionability | PDF narrative report | Sprint-ready tickets with retention % | Immediate developer handoff |
| Time-to-value | Days to weeks | Under 4 minutes | Same-session actionability |

## 9. Market Awareness

**Direct Competitors:**
- UserTesting ($49/response, human panels, 2-5 day turnaround, no structured analysis)
- Maze/Hotjar (behavioral analytics, no qualitative adversarial analysis)

**Indirect Competitors:**
- ChatGPT/Claude/Perplexity (single-model, no adversarial structure, no evidence grounding)
- G2/Capterra (aggregated ratings, no adversarial analysis, no actionable output)
- McKinsey/BCG (human consulting, $200K+, 6-12 weeks)

**Market Positioning:** While incumbents optimize for either speed (ChatGPT — instant but shallow) or depth (McKinsey — thorough but expensive), The War Room captures the underserved quadrant optimizing for both simultaneously: evidence-dense adversarial analysis delivered in minutes at near-zero marginal cost. This positions the product at the intersection of AI-powered research and consulting automation — a category that does not yet exist.

**Independent Validation:** Mitsubishi Electric (January 2026) announced the manufacturing industry's first multi-agent AI argumentation framework for expert-level decision-making, independently validating the exact adversarial debate pattern for industrial applications. Academic foundation: Du et al. (2023) "Improving Factuality and Reasoning in Language Models through Multiagent Debate."

## 10. Team Execution Plan

**Division of Labor:**
- **Tucker Anglemyer** (Accounting & Finance, Providence College): Owns CrewAI orchestration, swarm engine, meta-agent, FastAPI/WebSocket API, React frontend, Vercel deployment, demo delivery. Prior: built Untracked (60K lines production code, solo, 2 months) — React/TypeScript, Python ML, Postgres/pgvector. PwC internship 2027.
- **Griffin Kovach** (Founder, Clerion AI, Providence College): Owns RAG dataset curation (31,737 chunks across 20 apps), ChromaDB ingestion pipeline, tool function wiring with metadata filtering, data quality assurance. Prior: built Clerion's RAG system for Canvas LMS with domain-specific evidence retrieval.

**Critical Path Milestones:**

| Hours | Milestone | Owner | Dependency |
|-------|-----------|-------|------------|
| 0-1 | GitHub repo, API contract (`POST /analyze`, `WS /ws/{session_id}`), README | Both | None — unblocks parallel development |
| 1-4 | CrewAI 4-round debate passing end-to-end on local model | Tucker | API contract |
| 1-4 | ChromaDB ingestion of 31,737 chunks with metadata filtering | Griffin | Raw data (pre-curated) |
| 4-8 | FastAPI + WebSocket streaming server, React frontend (3 views) | Tucker | Working crew.py |
| 4-8 | Tool functions wired to ChromaDB, pre-seeded context injection | Griffin | Loaded ChromaDB |
| 8-12 | End-to-end integration: frontend → API → swarm → debate → verdict | Both | Integration gate |
| 12-16 | DGX Spark deployment: 3 models loaded, full demo recorded | Both | DGX access window |
| 16-20 | Vercel deployment, traction push, social distribution | Tucker | Working frontend |
| 20-24 | Demo rehearsal, backup video, final stabilization | Both | Feature freeze at Hour 20 |

## 11. Risk Assessment

| Risk | Probability | Impact | Mitigation Strategy | Contingency Plan |
|------|------------|--------|---------------------|-----------------|
| DGX Spark thermal throttling during sustained inference | Confirmed | Critical | Sequential model loading (one active model per round) with 10-second cooling intervals between rounds. Reduced swarm parallelism (5 workers vs 20) | Automated graceful degradation to local 8B model maintaining core debate functionality for demo |
| Venue WiFi blocking SSH to DGX (port 22 filtered) | Confirmed | High | Direct monitor access with keyboard/mouse. GitHub push/pull for code synchronization | All development completed and tested locally first; DGX window used exclusively for model swap and demo recording |
| Small models (8B) bypassing CrewAI ReAct tool-calling loop | Confirmed | High | Pre-seeded context injection: `fetch_context_for_product()` retrieves 10 RAG results at crew build time and injects directly into task descriptions | Evidence is structurally guaranteed regardless of whether the LLM executes tool calls during inference |
| Live demo failure during Sunday presentation | Medium | Critical | Hardcoded demo fallback with typewriter animation built into frontend — activates automatically if WebSocket disconnects within 8 seconds | Pre-recorded screen capture of best DGX demo run available as instant backup video |
| RAG retrieval returning irrelevant evidence | Low | Medium | Metadata filtering by source type (`reddit`, `hackernews`, `google_play`). Cosine similarity thresholding on 31,737 chunks | Swarm runs 20 parallel queries across different dimensions — irrelevant results in one dimension are diluted by relevant results across 19 others |

## 12. Differentiation Strategy

**Unique Value Proposition (UVP):** The War Room delivers adversarial, evidence-grounded product QA through multi-model debate — structurally incapable of producing single-perspective analysis. Three architectures from three different companies (Meta's Llama, Alibaba's Qwen, Mistral AI's Mistral) trained on different data in different contexts produce genuinely independent reasoning that challenges itself.

**Defensible Moat:** The differentiation is structural, not cosmetic:
1. **Data network effects:** As the RAG corpus grows (currently 31,737 chunks across 20 tools), the quality and specificity of debate findings compound. Each new product vertical added increases the system's analytical coverage, creating a widening knowledge advantage that generic single-model tools cannot replicate without equivalent domain-specific curation
2. **Protocol complexity as barrier to entry:** The three-layer orchestration (meta-agent → swarm → debate) with mandatory disagreement rules, stubbornness constraints, and buyer settlement logic represents significant architectural complexity. Replicating the protocol requires not just running multiple models, but engineering the adversarial interaction structure that produces genuinely divergent, evidence-cited findings
3. **Vertical extensibility as platform moat:** Each new RAG collection (healthcare, legal, finance, security) transforms the same protocol into a new product category without additional engineering. The platform becomes more valuable with each vertical, while competitors must build separate solutions for each domain
4. **Local compute sovereignty:** Running entirely on NVIDIA DGX Spark with zero API dependencies, zero data egress, and zero per-query costs creates a fundamentally different economic model. Enterprises with data sensitivity requirements (healthcare, defense, finance) cannot use cloud-based alternatives — the War Room's on-premise architecture is the only viable option for regulated industries

---

*The War Room — Built at the 2026 yconic New England Inter-Collegiate AI Hackathon by Tucker Anglemyer & Griffin Kovach.*
