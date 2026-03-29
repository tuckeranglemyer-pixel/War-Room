# War Room — System Architecture

## System Overview

War Room is a multi-model adversarial debate system that forces three frontier LLMs to critique each other's reasoning before producing a synthesized verdict on any productivity software product. Rather than querying a single model for a balanced opinion, War Room deliberately assigns each model an irreconcilable user perspective — a first-time evaluator, a long-term power user, and a budget-holding buyer — then runs a four-round structured debate in which each model reads and directly attacks the previous model's output before committing to a revised position. The architecture imposes genuine intellectual tension: a model cannot see its own prior output without also seeing a direct challenge to it, forcing position updates grounded in cited evidence rather than hedged agreement. This pipeline is fundamentally impossible on consumer hardware. Running three frontier-scale models concurrently — Llama 3.3 70B, Qwen3 32B, and Mistral-Small 24B — requires hundreds of gigabytes of high-bandwidth, low-latency memory resident simultaneously, with all three models available for inference within the same debate-round window. A single RTX 4090 maxes out at 24 GB of VRAM, enough for one heavily quantized model with no context budget left for RAG injection. War Room requires the NVIDIA DGX Spark's 128 GB unified memory architecture, NVLink-C2C bandwidth, and Grace Blackwell tensor core throughput to operate at the latency budget the debate protocol demands.

---

## Architecture Diagram

```
                              WAR ROOM — FULL DATA FLOW
                              ═══════════════════════════

  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                           CLIENT (Browser / React)                          │
  │                                                                             │
  │   POST /analyze ──────────────────────────────────────────────────────────► │
  │   ◄────────────────────────────────── WS /ws/{session_id} (streaming JSON) │
  └─────────────────────────┬───────────────────────────────────────────────────┘
                            │  HTTP + WebSocket
                            ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                      FastAPI Server  [CPU]                                  │
  │                                                                             │
  │   POST /analyze → spawns DebateSession → ThreadPoolExecutor(_run_debate)   │
  │   POST /api/ingest/video → ffmpeg frame extraction → GPT-4o Vision         │
  │   WS /ws/{session_id} → asyncio Queue → streams round JSON to client       │
  └─────────────────────────┬───────────────────────────────────────────────────┘
                            │
                            ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                   build_crew()  [CPU — orchestration]                       │
  │                                                                             │
  │   Step 0 │ Session context assembly (product, target user, competitors,     │
  │          │ differentiator, stage, optional video evidence)                  │
  │          │                                                                  │
  │   Step 1 │ Meta-Prompt Persona Generation                                   │
  │          │   LLM call → generate_personas() → 3 adversarial JSON personas  │
  │          │   (First-Timer, Daily Driver, Buyer) with specific backstories,  │
  │          │   churn history, and conflicting evaluation priorities            │
  │          │                                                                  │
  │   Step 2 │ Reconnaissance Swarm  [CPU — parallel ChromaDB queries]         │
  │          │   20 scout queries × 10 parallel workers                         │
  │          │   Targets: onboarding, pricing, mobile, integrations, bugs,      │
  │          │   support, competitors, missing features, UI, collaboration,      │
  │          │   data export, notifications, search, offline, learning curve,   │
  │          │   updates, security, customization, automation, paywall          │
  │          │   → Compiled intelligence briefing injected into Round 1         │
  │          │                                                                  │
  │   Step 3 │ ChromaDB RAG Retrieval  [CPU — ChromaDB on local disk]          │
  │          │   Collection: pm_tools | 31,668 chunks | HNSW cosine similarity  │
  │          │   4 targeted queries per product (onboarding, bugs, positives,   │
  │          │   enterprise) with app-key metadata filter                        │
  │          │   → Evidence block injected verbatim into Rounds 2, 3, 4         │
  └─────────────────────────┬───────────────────────────────────────────────────┘
                            │
                            ▼
  ╔═════════════════════════════════════════════════════════════════════════════╗
  ║              vLLM Multi-Model Inference Engine  [DGX SPARK GPU]            ║
  ║              128 GB Unified Memory | NVLink-C2C | Blackwell Tensor Cores   ║
  ║                                                                             ║
  ║   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐   ║
  ║   │  Llama 3.3 70B  │  │   Qwen3 32B     │  │  Mistral-Small 24B      │   ║
  ║   │  (First-Timer)  │  │  (Daily Driver) │  │  (Buyer)                │   ║
  ║   │  Port 8001      │  │  Port 8002      │  │  Port 8003              │   ║
  ║   │  ~70 GB INT8    │  │  ~32 GB INT8    │  │  ~24 GB INT8            │   ║
  ║   └────────┬────────┘  └────────┬────────┘  └────────────┬────────────┘   ║
  ║            │                    │                         │                ║
  ║            └────────────────────┴─────────────────────────┘                ║
  ║                      Total resident footprint: ~126 GB                      ║
  ╚═════════════════════════════════════════════════════════════════════════════╝
                            │
                            ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │               CrewAI Sequential Debate Orchestration  [CPU]                 │
  │                                                                             │
  │  ROUND 1  First-Timer Agent (Llama 70B)                                    │
  │           Inputs: persona, swarm briefing, RAG evidence, product context   │
  │           Output: Onboarding audit + 3 critical problems + 1 strength      │
  │              │                                                              │
  │              ▼  (task output passed as context via CrewAI context=[])      │
  │  ROUND 2  Daily Driver Agent (Qwen3 32B)                                   │
  │           Inputs: Round 1 output + RAG evidence injected directly          │
  │           Output: AGREE/DISAGREE on each R1 finding + 2 hidden problems    │
  │              │                                                              │
  │              ▼  (context=[round1, round2])                                 │
  │  ROUND 3  First-Timer Agent (Llama 70B) — rebuttal                        │
  │           Inputs: R1+R2 outputs + RAG evidence                             │
  │           Output: Defend or concede each challenge + updated severity      │
  │              │                                                              │
  │              ▼  (context=[round1, round2, round3])                         │
  │  ROUND 4  Buyer Agent (Mistral-Small 24B) — synthesis                     │
  │           Inputs: Full R1+R2+R3 transcript + RAG evidence                  │
  │           Output: YES/NO/CONDITIONS + 1-100 score + TOP 3 FIXES            │
  └─────────────────────────┬───────────────────────────────────────────────────┘
                            │
                            ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │             Verdict Parser + WebSocket Delivery  [CPU]                      │
  │                                                                             │
  │   _parse_verdict() → { score, decision, top_3_fixes, full_report }         │
  │   asyncio.Queue → WS /ws/{session_id} → client receives streaming JSON     │
  └─────────────────────────────────────────────────────────────────────────────┘


  COMPONENT PLACEMENT LEGEND
  ══════════════════════════
  [CPU]        Python process, ChromaDB queries, CrewAI task orchestration,
               FastAPI server, WebSocket delivery — runs on Grace CPU cores
  [DGX SPARK]  vLLM inference engine with all three models simultaneously
               resident in 128 GB unified memory, served via OpenAI-compatible
               API on three separate ports
```

---

## Compute Requirements & Hardware Justification

### Per-Model Memory Footprint

| Model | Parameters | FP16 | INT8 (vLLM default) | INT4 |
|---|---|---|---|---|
| Llama 3.3 70B | 70B | ~140 GB | ~70 GB | ~35 GB |
| Qwen3 32B | 32B | ~64 GB | ~32 GB | ~16 GB |
| Mistral-Small 24B | 24B | ~48 GB | ~24 GB | ~12 GB |
| **Combined** | **126B** | **~252 GB** | **~126 GB** | **~63 GB** |

The numbers above are weight-only. In live inference, each model additionally requires KV cache for the active context window. War Room's debate rounds inject up to 6,000+ tokens of accumulated context (prior round outputs + RAG evidence block) per model call, adding significant per-request memory pressure on top of static weight storage.

### Why Models Must Be Memory-Resident

vLLM uses PagedAttention for KV cache management: attention keys and values are stored in non-contiguous physical memory pages that are dynamically allocated and freed as requests arrive. This architecture achieves near-zero KV cache waste and high throughput — but it requires the full model weights to be loaded into GPU memory at server startup. There is no swap-to-disk path. A model that is not loaded cannot serve a request. If any of the three War Room models is not resident when its debate round executes, the CrewAI task blocks indefinitely waiting for the inference call to return.

### Concurrent Inference During Debate Rounds

The War Room debate protocol requires all three models to be available within the same session window. A single debate run calls:

- Llama 70B twice (Round 1 and Round 3)
- Qwen3 32B once (Round 2)
- Mistral-Small 24B once (Round 4)

Rounds execute sequentially, but multiple parallel debate sessions (multiple users) will dispatch concurrent requests to all three model endpoints simultaneously. Loading and unloading models between rounds is architecturally incompatible with vLLM's startup-load design and would introduce 30–120 second cold-start penalties per model swap — longer than the entire debate is supposed to take.

### Consumer Hardware Ceiling

An RTX 4090 provides 24 GB of GDDR6X VRAM. At INT4 quantization (the most aggressive quality-degrading compression available), Llama 70B alone requires ~35 GB — exceeding the 4090 by 46%. Running Llama 70B on a consumer GPU requires either:

1. Splitting the model across multiple GPUs over PCIe (severe bandwidth bottleneck — PCIe 5.0 ×16 tops out at 64 GB/s vs. NVLink's 900 GB/s), or
2. CPU offloading via llama.cpp (tokens-per-second drops into single digits, round latency exceeds 5 minutes), or
3. Giving up on 70B and using a 7B–13B model that can generate confident-sounding but analytically shallow output.

None of these options support running three models concurrently. The consumer path collapses War Room's multi-model adversarial premise into a single-model sequential wrapper with no genuine tension.

### Why NOT Cloud APIs

| Concern | Detail |
|---|---|
| **Latency budget** | 3 models × 4 rounds × ~1.5s average cloud API call = 18s of pure network round-trip time, before any token generation. On DGX Spark, the same calls complete locally with no egress latency. |
| **Sampling control** | War Room requires fine-grained control over temperature, top-p, and repetition penalties per agent role. Cloud APIs expose limited or no sampling parameter access. |
| **Data residency** | The RAG corpus (user reviews, Reddit posts, HN comments, app metadata) stays local in ChromaDB. Sending user queries to cloud inference endpoints exposes proprietary product analysis data to third-party infrastructure. |
| **Context injection** | Each round injects up to 6,000 tokens of RAG evidence directly into the prompt. At cloud API pricing, this is non-trivial at scale. |
| **Model availability** | Cloud providers may throttle, version-bump, or deprecate specific model checkpoints mid-hackathon. Local vLLM on DGX Spark pins exact model versions. |

### DGX Spark Grace Blackwell: Requirement-to-Spec Mapping

| War Room Requirement | DGX Spark Specification |
|---|---|
| ~126 GB resident model weights at INT8 | 128 GB LPDDR5X unified memory (CPU + GPU share same physical pool via NVLink-C2C) |
| Low-latency inter-model communication during debate rounds | NVLink-C2C interconnect between Grace CPU and Blackwell GPU; no PCIe bottleneck |
| High-throughput token generation for multi-round, multi-model debate | Blackwell tensor cores with FP8 mixed precision; 5th-gen NVTensor cores |
| Concurrent inference across 3 endpoints (ports 8001–8003) | Single-node architecture — all three vLLM processes share the same physical memory pool without data movement overhead |
| Local ChromaDB vector search over 31,668 chunks | 72-core Grace CPU handles HNSW index traversal while Blackwell handles LLM inference simultaneously without resource contention |

---

## Data Flow

A complete trace of one War Room debate from user input to final verdict:

```
T+0ms     User submits POST /analyze with product_description, target_user,
          competitors, differentiator, product_stage

T+1ms     FastAPI creates DebateSession (UUID), fires _run_debate() into
          ThreadPoolExecutor, returns session_id to client

T+1ms     Client opens WS /ws/{session_id}

T+2ms     _run_debate() begins in background thread

T+2ms     Session context block assembled: product metadata formatted into
          structured prompt prefix injected into all 4 task descriptions

T+5ms     generate_personas() called: LLM generates 3 adversarial JSON personas
          tailored to the specific product under evaluation
          → ~3-8s on DGX Spark (Llama 70B, ~200 token output)

T+8s      deploy_swarm() launches 20 ChromaDB scout queries in parallel
          (ThreadPoolExecutor, 10 workers)
          Each scout targets a different product dimension
          ChromaDB HNSW similarity search per scout: ~5-15ms
          → All 20 scouts complete in ~1-3s (parallel)

T+10s     fetch_context_for_product() runs 4 targeted queries against pm_tools
          collection with app-key metadata filter
          → 4 × ~10ms = ~40ms, returns formatted evidence block

T+10s     All context assembled. CrewAI Crew.kickoff() called.

T+10s     ROUND 1 — First-Timer task dispatched to Llama 3.3 70B (vLLM port 8001)
          Input tokens: ~2,500 (persona + swarm briefing + task instructions)
          Output: ~600-800 tokens (onboarding audit + 3 problems + 1 strength)
          → Inference time on DGX Spark: ~3-6s
          → task_callback fires, round JSON enqueued → WebSocket delivers to client

T+16s     ROUND 2 — Daily Driver task dispatched to Qwen3 32B (vLLM port 8002)
          Input tokens: ~4,000 (R1 output + RAG evidence block + task instructions)
          Output: ~700-900 tokens (AGREE/DISAGREE per finding + hidden problems)
          → Inference time on DGX Spark: ~3-5s
          → task_callback fires, round JSON enqueued → WebSocket delivers to client

T+21s     ROUND 3 — First-Timer rebuttal dispatched to Llama 3.3 70B (port 8001)
          Input tokens: ~6,000 (R1 + R2 outputs + RAG evidence + task instructions)
          Output: ~500-700 tokens (defenses, concessions, updated severity ratings)
          → Inference time on DGX Spark: ~4-7s
          → task_callback fires, round JSON enqueued → WebSocket delivers to client

T+28s     ROUND 4 — Buyer synthesis dispatched to Mistral-Small 24B (port 8003)
          Input tokens: ~8,000 (full R1+R2+R3 transcript + RAG evidence + task)
          Output: ~800-1,000 tokens (YES/NO/CONDITIONS + score + TOP 3 FIXES)
          → Inference time on DGX Spark: ~4-8s
          → task_callback fires, round JSON enqueued → WebSocket delivers to client

T+35s     _parse_verdict() extracts structured fields from Round 4 raw text:
          score (1-100), decision (YES/NO/YES WITH CONDITIONS), top_3_fixes list

T+35s     Verdict dict enqueued → WebSocket delivers final JSON to client
          None sentinel enqueued → WebSocket loop exits, connection closed

Total wall-clock time (DGX Spark): ~30-45s for a full 4-round debate
Total wall-clock time (consumer CPU offload): 8-15 minutes (unacceptable for live use)
```

---

## RAG Pipeline

### Source Breakdown

The `pm_tools` ChromaDB collection contains 31,668 unique chunks derived from:

| Source | Type | Approximate Volume |
|---|---|---|
| Reddit | Posts and comments from r/productivity, r/notion, r/projectmanagement, and related subreddits | ~1,600+ documents |
| Hacker News | Stories and comment threads discussing productivity tools | ~1,000+ comments |
| Google Play | App reviews for top 20 PM tools | ~4,000+ reviews |
| App Store (iOS) | App reviews, supplementing Play Store coverage | ~4,000+ reviews |
| App metadata | Pricing tiers, feature lists, categories, use cases, competitor positioning | Structured records per app |
| Screenshots | GPT-4o Vision UX analysis of product screenshots (processed via `process_screenshots.py`) | Per-app screen descriptions |
| Founder walkthroughs | GPT-4o Vision frame-by-frame analysis of uploaded product demo videos | Session-specific, stored in memory |

### Processing Pipeline

Raw data was chunked into RAG-ready pieces through an offline preprocessing pipeline:

1. **Scrapers** (`scrapers/` directory) collected data from Reddit (via PRAW), Hacker News (Algolia API), Google Play, and app metadata sources
2. **Chunking** (`scrapers/08_preprocess_chunks.py`) split long documents into context-window-sized pieces with metadata preservation
3. **Screenshot vision ingestion** (`process_screenshots.py`) sent each product screenshot to GPT-4o Vision with a structured UX analyst prompt, producing 3–5 paragraph textual descriptions that encode UI layout, friction points, and competitive comparisons
4. **Deduplication** (`load_db.py`'s `deduplicate()`) dropped exact-ID duplicates before ingestion, yielding 31,668 unique chunks
5. **ChromaDB ingestion** (`load_db.py`) batch-loaded chunks in groups of 500, with metadata sanitized to ChromaDB-allowed scalar types

### ChromaDB Collection Configuration

- **Collection name**: `pm_tools`
- **Embedding model**: ChromaDB default (`all-MiniLM-L6-v2` via `chromadb`'s built-in embedding function)
- **Distance metric**: Cosine similarity (`hnsw:space: "cosine"`)
- **Index type**: HNSW (Hierarchical Navigable Small World graph) for approximate nearest-neighbor retrieval
- **Metadata filters**: Every chunk carries `source` (reddit/hackernews/google_play/metadata/screenshot), `app` (normalized product name slug), `type` (post/comment/review/ui_screenshot/video_frame), and source-specific fields (subreddit, rating, URL)
- **Retrieval**: `n_results=5` per query; swarm scouts issue 20 queries in parallel; direct RAG injection issues 4 queries per debate session

### Why This Dataset Matters

Every claim in a War Room debate must be grounded in cited evidence from this corpus — agents are instructed to search before arguing and explicitly flag when no evidence exists for a position. The dataset's value derives from three properties:

1. **Breadth**: 20+ PM tools covered with cross-source corroboration (the same product pain point appearing in Play Store reviews, Reddit threads, and HN comments carries more weight than a single source)
2. **Authenticity**: Real user opinions with real frustration, not documentation, marketing copy, or synthetic data
3. **Adversarial structure**: The source diversity maps directly onto agent roles — first-timer agents are instructed to trust Play Store and Reddit; daily driver agents trust HN and long-form reviews; buyer agents trust metadata and pricing comparisons. Different sources produce genuine disagreement rather than consensus.

---

## Model Selection Rationale

The three-model lineup was chosen to maximize the likelihood that genuine disagreement emerges during debate rounds. Using models from the same architecture family (e.g., three different Llama variants) would produce correlated outputs — similar priors, similar failure modes, similar hallucination patterns — defeating the adversarial premise.

### Llama 3.3 70B (First-Timer and Rebuttal Agent)

Meta's Llama 3.3 training corpus emphasizes English-language web text, academic content, and structured reasoning tasks. Llama 70B tends toward methodical, category-structured responses with strong analytical throughput — well-suited for the First-Timer role, which requires a systematic onboarding audit with numbered findings and severity ratings. Assigned to Rounds 1 and 3, Llama 70B establishes the initial critique framework and then must defend or revise it under challenge — a dual-role that rewards models with consistent internal reasoning across context windows.

### Qwen3 32B (Daily Driver Agent)

Alibaba's Qwen3 training data includes substantial Chinese-language technical content, different web corpora, and distinct RLHF preferences shaped by a different alignment team with different priorities. In practice, Qwen models tend to be more direct in identifying long-term usage friction, more willing to disagree with surface-level assessments, and more attentive to workflow integration concerns — exactly the skeptical power-user perspective the Daily Driver role demands. The different training corpus means Qwen's priors about what constitutes a "serious problem" vs. a "minor annoyance" are genuinely different from Llama's, producing AGREE/DISAGREE positions that reflect distinct reasoning rather than random variation.

### Mistral-Small 24B (Buyer Agent)

Mistral AI's European training perspective, combined with the Mistral architecture's sliding window attention (allowing efficient processing of very long contexts), makes Mistral-Small well-suited for Round 4. The Buyer role requires reading the full prior debate transcript — often 6,000–8,000 tokens of prior round outputs plus RAG evidence — and synthesizing it into a single defensible business decision. Sliding window attention maintains quality on long-context synthesis tasks where models without architectural support for extended context tend to lose coherence. Mistral models are also known for sharp, confident conclusions — appropriate for a role that is explicitly prohibited from hedging.

### The Diversity Is the Point

A single model asked three times will produce three correlated outputs. Agreement emerging from correlated models is noise, not signal. War Room's value proposition is that when Llama 70B identifies an onboarding failure and Qwen3 32B disagrees based on different evidence, the disagreement is architecturally meaningful — it reflects genuinely different priors, different training distributions, and different reasoning patterns encountering the same evidence. When all three models converge on a conclusion despite their different starting points, that convergence is a meaningful signal about the product.

---

## Adversarial Debate Protocol

### Mechanical Round Structure

War Room runs four sequential CrewAI tasks, each building on the outputs of all prior tasks via CrewAI's `context=[]` parameter, which injects prior task outputs directly into the next task's prompt.

**Round 1 — First-Timer Analysis**
- Agent: Llama 3.3 70B, First-Timer persona
- Required outputs: Step-by-step onboarding audit of first 2 minutes; exactly 3 critical problems (each with: the exact failing interaction, a cited user review or Reddit post, a severity rating 1–10, and a named competitor that handles it better); 1 acknowledged strength with evidence
- Receives: swarm reconnaissance briefing, pre-fetched RAG evidence, product context block
- Cannot see: any prior model output (this is the opening argument)

**Round 2 — Daily Driver Challenge**
- Agent: Qwen3 32B, Daily Driver persona
- Required outputs: Clear AGREE or DISAGREE on each of the First-Timer's 3 findings; 2 hidden long-term problems a new user would never discover; challenge to the competitor recommendation; 1–10 quality rating of Round 1 analysis
- Constraint: Must disagree with at least one R1 finding; must agree and escalate at least one. No fence-sitting permitted.
- Receives: Full Round 1 output (via `context=[round1]`) + injected RAG evidence block

**Round 3 — First-Timer Rebuttal**
- Agent: Llama 3.3 70B, same First-Timer persona
- Required outputs: Defense or concession for each point of disagreement (with confidence score 1–10); response to the 2 hidden problems; updated severity ratings; revised stay-or-leave recommendation
- Constraint: Concessions require specific cited evidence. "You get used to it" is explicitly flagged as an admission of failure, not a defense.
- Receives: Full R1 + R2 outputs (via `context=[round1, round2]`) + injected RAG evidence

**Round 4 — Buyer Synthesis and Verdict**
- Agent: Mistral-Small 24B, Buyer persona
- Required outputs: Resolution of every disagreement with evidence; business-critical assessment of pricing, integrations, data portability, and admin; one strategic market blind spot missed by both analysts; final YES/NO/YES WITH CONDITIONS decision; 1–100 score; TOP 3 FIXES as actionable PM tickets with estimated retention impact; competitive positioning summary
- Constraint: No hedging. The Buyer is spending real budget. A non-decision is a disqualifying failure.
- Receives: Full R1 + R2 + R3 transcript (via `context=[round1, round2, round3]`) + injected RAG evidence

### What Constitutes a "Critique"

A valid critique in the War Room protocol must:
1. Take a clear position (AGREE / DISAGREE / ESCALATE)
2. Cite specific evidence from the knowledge base, not general knowledge
3. Name a competitor comparison where relevant
4. Update the severity rating or business impact assessment
5. Address the other model's specific argument, not a strawman version of it

The task descriptions explicitly forbid responses that merely acknowledge uncertainty or suggest "it depends." Every round produces a committed, evidence-backed position.

### How Models Receive Each Other's Outputs

CrewAI's sequential process passes prior task outputs through the `context` parameter. When `context=[round1, round2]` is set on Round 3, CrewAI serializes the raw text output of both completed tasks and prepends them to the Round 3 task description before dispatching the inference call. This means each model receives the full prior transcript, not a summary — preserving specific claims, cited evidence, and severity scores that the rebuttal round is required to address.

The RAG evidence block (real user reviews from ChromaDB) is injected directly into the task `description` string for Rounds 2, 3, and 4, guaranteeing it appears in the prompt regardless of whether the model chooses to invoke the `search_pm_knowledge` tool. This dual-injection strategy (tool available + evidence pre-loaded) compensates for the documented failure mode of smaller local models that do not reliably execute the ReAct tool-calling loop.

### How Consensus and Disagreement Are Identified

Round 4's Buyer agent is explicitly instructed to "settle each disagreement" — for every point where Round 2 and Round 3 produced opposing positions, the Buyer must adjudicate based on the evidence, state which model's argument was stronger, and explain what the disagreement reveals about the product's maturity or the limitation of a single user perspective.

Productive disagreement (two models reaching opposite conclusions from the same evidence) is treated as a signal about edge-case quality: a product that works well for power users but fails first-timers has a real onboarding problem, not a reviewer disagreement. The verdict parser extracts `decision`, `score`, and `top_3_fixes` from Round 4's structured output, surfacing the synthesis as machine-readable fields.

### Why This Produces Better Outputs Than Single-Model or Ensemble Approaches

| Approach | Failure Mode | War Room's Response |
|---|---|---|
| Single model, single prompt | Model averages known priors into a hedged, balanced non-answer | Three models with incompatible personas cannot simultaneously hedge — one must attack the other's position |
| Single model, multiple prompts with different system prompts | Same underlying weights produce correlated outputs despite different instructions | Different model families have genuinely different priors; disagreement is structural, not instructed |
| Simple ensemble (average scores) | Averaging eliminates the signal in outlier positions | War Room preserves disagreements as evidence; the Buyer's job is to adjudicate them, not average them away |
| LLM judge / evaluator | Single evaluator inherits the biases of whoever designed the rubric | Adversarial rebuttal forces each model to defend its position against an actual challenger |

---

## CrewAI Orchestration

### Why CrewAI Over Alternatives

**LangGraph** provides fine-grained control over agent state machines via explicit graph edges, which is powerful for branching decision flows but requires significant boilerplate for linear sequential pipelines. War Room's debate structure is fixed: four rounds, always in order, always with full prior context available. LangGraph's flexibility would add complexity without benefit, and its graph-based state management would require custom nodes to replicate CrewAI's built-in sequential context-chaining behavior.

**AutoGen** excels at multi-agent conversation loops where agents negotiate turn-by-turn. AutoGen's conversational model assumes agents take turns in a shared thread, which does not map cleanly onto War Room's strict round structure (Round 1 must fully complete before Round 2 begins; Round 4 is a synthesis of all three prior outputs, not a continuation of a conversation). AutoGen also provides weaker native support for RAG tool injection per-agent.

**Custom orchestration** (raw API calls with prompt templates) would provide maximum control but would require reimplementing task dependency management, context chaining, tool loop execution, and callback infrastructure that CrewAI provides out of the box. The development cost is not justified for a system with a fixed, well-defined pipeline.

**CrewAI** was selected because:
1. Sequential `Process.sequential` mode matches the debate protocol exactly
2. `context=[]` parameter handles prior-task output injection with no custom code
3. `task_callback` fires after each task completes, enabling WebSocket streaming without polling
4. Per-agent `tools=[]` assignment allows the search tool to be available to all agents while each agent's `backstory` instructs different search priorities
5. Per-agent `llm=` assignment maps directly to the three vLLM endpoints on the DGX Spark
6. `max_iter` limits runaway tool loops that would blow the per-round latency budget

### Agent Definitions and Role Assignment

Each agent is constructed in `build_crew()` with:
- **`role`**: The dynamically generated persona title from `meta_prompt.py` (e.g., "Sprint-Obsessed PM Who Churned From Notion")
- **`goal`**: One sentence defining the agent's evaluation objective and failure condition
- **`backstory`**: 5+ sentences with specific tool churn history, evidence preferences, and what the agent needs to see in this session — appended with an evidence preference directive and a hard rule requiring tool use before any argument
- **`llm`**: A `crewai.LLM` instance pointing at the appropriate vLLM port on the DGX Spark
- **`tools`**: `[search_pm_knowledge]` — the full-corpus ChromaDB search tool available to all agents
- **`max_iter=10`**: Caps the ReAct tool-calling loop at 10 iterations per task to prevent runaway evidence gathering

### Debate Flow Management

`build_crew()` constructs a `Crew` with `process=Process.sequential`, which executes tasks strictly in order: `[round1, round2, round3, round4]`. Each task's `context=[]` parameter declares which prior tasks' outputs should be prepended, and CrewAI handles serialization and injection automatically.

The `task_callback` parameter receives a callable from `DebateSession.build_task_callback()`. After each task completes, CrewAI calls this function with a `TaskOutput` object containing the agent's name and raw output text. The callback maps the task index to the canonical agent role slug, packages a JSON message dict, and enqueues it thread-safely onto `session.queue` via `asyncio.run_coroutine_threadsafe()`. The WebSocket handler dequeues these messages and streams them to the client as each round completes — users see Round 1 results while Round 2 is still running.

The `None` sentinel pattern (`session.queue.put(None)`) signals end-of-stream to the WebSocket loop, which exits cleanly and closes the connection. Errors are caught in the `_run_debate()` try/except block and forwarded as `{"type": "error", "message": ...}` before the sentinel, ensuring the client always receives a terminal message.
