# War Room — Design Decisions

A living record of every non-obvious technical choice in this project, written honestly: what we picked, what we passed on, and what we knowingly gave up.

---

### 1. Local Inference (DGX Spark + vLLM / Ollama) vs. Cloud API Calls

**Choice:** Run all debate LLMs on a local NVIDIA DGX Spark via Ollama (configured in `config.py` with `LOCAL_BASE_URL = "http://localhost:11434"`), with GPT-4o reserved only for the video-analysis pipeline.

**Over:** Routing every inference call to OpenAI, Anthropic, or another managed cloud provider.

**Why:** The adversarial debate format sends the same product context through three to four long-context rounds in rapid succession, which makes per-token cloud costs non-trivial at hackathon scale. Running locally eliminates both cost and rate-limit ceilings, lets us iterate on prompt structure without metering anxiety, and keeps the entire reasoning chain on hardware we control — a genuine privacy advantage when customers describe unreleased products.

**Tradeoff:** We are fully bound to the DGX Spark being up and reachable. Cold-start Ollama latency is higher than a warmed cloud endpoint, and reproducibility across machines requires everyone to pull the same model weights. The `process_screenshots.py` workaround — using GPT-4o for screenshot-to-text extraction because the local models aren't strong enough at vision tasks — reveals the ceiling: local-only is a constraint, not a pure win.

---

### 2. Three Specialized Debate Models (Llama 3.3-70B, Qwen3-32B, Mistral-Small-24B) vs. One Large Model or a Different Combination

**Choice:** Assign distinct LLM personalities to each agent role: Llama 3.3-70B for the First-Timer, Qwen3-32B for the Daily Driver, and Mistral-Small-24B for the Buyer (documented in `config.py` as the intended DGX configuration).

**Over:** Running all agents from one shared model (the current code path in `crew.py` lines 20–26, where all three agents share `local_llm`), or using three instances of the same model with only prompt-level differentiation.

**Why:** Different pre-training corpora and fine-tuning philosophies produce meaningfully different prior biases. Qwen's strong multilingual and enterprise-software training fits a power-user voice; Mistral's efficiency-focused training makes it a credible "cost-sensitive buyer" stand-in; Llama's broad instruction tuning works for naive first impressions. If agents share weights the "disagreement" in round 2 is purely prompt-driven and can collapse into superficial hedging rather than genuine tension.

**Tradeoff:** This is the single largest gap between intent and implementation. The repo's `crew.py` currently assigns all three agents the same `local_llm` object — the multi-model behavior only materializes when the DGX Spark is live and `config.py` is updated to separate the three endpoints. Any evaluation of "debate quality" on a dev machine with a single Ollama instance is not testing the actual architecture. We accepted this deferral to keep the code runnable on a single machine during development.

---

### 3. ChromaDB vs. Other Vector Stores (Pinecone, Weaviate, FAISS)

**Choice:** ChromaDB with a persistent local `PersistentClient` at `./chroma_db`, cosine-similarity HNSW index, per-source metadata filters.

**Over:** Pinecone (managed cloud), Weaviate (self-hosted with REST API), or FAISS (in-memory flat index, no server).

**Why:** ChromaDB is the only option in this list that is simultaneously file-local (no network hop, no account), has a Python-native API that composes naturally with CrewAI tools, and supports structured `where` metadata filters out of the box. The filter capability is load-bearing: `tools.py` queries `where={"app": app_key}` to restrict retrieval to a specific product, which a raw FAISS index cannot do without a custom pre-filter wrapper.

**Tradeoff:** ChromaDB's HNSW implementation is single-process and not horizontally scalable. A concurrent multi-user deployment would hit writer-lock contention. We also own the hardware — there is no SLA, no managed backup, and no dashboard. FAISS would be faster for read-only retrieval at scale but would require us to build the metadata filtering and persistence layers ourselves. Pinecone would solve the scaling concern but adds API cost and a cloud dependency that contradicts the local-inference stance in Decision 1.

---

### 4. CrewAI for Orchestration vs. LangGraph, AutoGen, or Custom Orchestration

**Choice:** CrewAI with `Process.sequential`, explicit `context=[...]` chaining between tasks, and a `task_callback` to stream each completed round over WebSocket.

**Over:** LangGraph (DAG-based stateful graph), AutoGen (conversational multi-agent with back-and-forth turns), or a hand-rolled async loop.

**Why:** The debate has a fixed four-round linear structure — there is no conditional branching, no retry DAG, and no need for agents to negotiate turn order. CrewAI's sequential `Process` maps directly to "Round 1 → Round 2 → Round 3 → Round 4" with automatic context threading, which would require explicit state nodes and edges in LangGraph for zero additional expressiveness. CrewAI also integrates cleanly with the `@tool` decorator pattern we already needed for Chroma lookups.

**Tradeoff:** CrewAI's abstraction hides the raw LLM call, making it harder to intercept token streams mid-generation. The `task_callback` only fires when a full round *completes*, which is why the WebSocket sends whole-round JSON blobs rather than streaming tokens — a noticeably worse UX for long rounds. LangGraph would have given us finer-grained streaming control. We also inherit CrewAI's opinionated prompt templating, which occasionally fights with our exact output-format requirements and forces us to embed format instructions redundantly in each task description.

---

### 5. Adversarial Debate Format vs. Ensemble Averaging or Majority Voting

**Choice:** Structured adversarial debate: Round 1 plants claims, Round 2 *must* challenge at least one and escalate at least one (enforced in the prompt at `crew.py` lines 191–194), Round 3 defends or concedes with an explicit stubbornness rule, Round 4 arbitrates and issues a binding verdict.

**Over:** Running N independent analyses in parallel and averaging scores, or having agents vote and taking the majority position.

**Why:** Ensemble averaging smooths away the most interesting signal. When two agents agree that onboarding is broken, that agreement deserves more weight than their averaged score — but when they *disagree*, the nature of the disagreement (severity, user segment, fixability) is the actual product insight. Forcing agents to take adversarial positions and justify them under challenge is a much stronger mechanism for surfacing hidden assumptions. It mirrors how real product reviews work: a Reddit power user and a first-day trialist are not averaging their experience; they are in genuine tension.

**Tradeoff:** The format is prompt-enforced, not structurally guaranteed. If the LLM decides to comply superficially with "disagree with at least one" by disagreeing on an inconsequential point, the debate quality degrades silently — there is no automated check. Ensemble voting would produce more consistent, machine-verifiable outputs. The adversarial format also means round 4 quality is load-bearing: a weak arbitration round can produce a final verdict that ignores valid prior disagreements.

---

### 6. Pre-Built RAG Dataset vs. Real-Time Web Retrieval

**Choice:** A static ~31,737-chunk Chroma collection scraped offline from Reddit, Hacker News, Google Play, the App Store, G2 reviews, and product metadata — loaded once via `load_db.py` and queried at debate time.

**Over:** Live web search or crawling during inference (e.g., calling the Reddit or Google Play API in real time as each debate round runs).

**Why:** Real-time retrieval inside a multi-round debate introduces three failure modes simultaneously: rate limiting (Reddit, Google Play both throttle aggressively), latency (each round would stall on network I/O), and non-determinism (search results change between rounds, so Round 3 might cite different evidence than Round 2 referenced). The pre-built corpus trades freshness for reliability — the swarm's 20 parallel scout queries and the four-template `fetch_context_for_product` call in `tools.py` can all resolve sub-second against a local Chroma file.

**Tradeoff:** The data is a snapshot. Products ship updates; user sentiment shifts. A tool evaluated against a six-month-old corpus can receive outdated criticism (bugs that were fixed) or miss emerging praise. We partially mitigate this by allowing founders to paste in a custom `context` field and upload a screen-recording at `/api/ingest/video`, but those are manual overrides, not automatic freshness. `search_g2_reviews` and `search_screenshots` in `tools.py` also currently return `"[RAG not connected yet]"` stubs — two data sources are documented but not wired.

---

### 7. Round-Robin Critique vs. Free-Form Multi-Agent Discussion

**Choice:** Strict sequential round-robin: First-Timer speaks, Daily Driver responds, First-Timer defends, Buyer arbitrates. Each agent sees only the prior rounds as context, not an open chat thread.

**Over:** A free-form discussion loop where any agent can interject at any point, or an AutoGen-style back-and-forth until a convergence criterion is met.

**Why:** Free-form discussion is difficult to terminate predictably — agents in an unconstrained loop tend to either converge immediately (collapsing to yes-man dynamics) or oscillate indefinitely. The round-robin structure gives us a deterministic four-message output every time, which is essential for the WebSocket streaming contract in `api.py` (the `ROUND_ROLES` mapping at lines 39–40 is how each completed task gets a label for the frontend). It also mirrors the structure of formal product review panels, where each stakeholder gets a defined speaking turn rather than fighting for the floor.

**Tradeoff:** The Buyer (Round 4) sees all prior rounds as `context` chains but cannot ask the First-Timer or Daily Driver a follow-up question. Interesting threads that emerge in Round 3 cannot be re-opened — the arbitration in Round 4 must work with whatever was said. In practice this means some genuine disagreements go unresolved rather than being chased to a conclusion. A free-form loop with a maximum-turns cap and a consensus detector would produce more thorough closure, at the cost of unpredictable output length and a much harder parsing job for the verdict-extraction regex in `api.py` lines 361–407.

---

### 8. Sequential CrewAI Process vs. Hierarchical / Parallel Crew

**Choice:** `Process.sequential` in `crew.py` line 269, with no manager agent.

**Over:** `Process.hierarchical` (CrewAI's built-in manager-agent pattern) or a parallel crew where multiple agents run simultaneously.

**Why:** A hierarchical process introduces a manager LLM that decides task delegation — adding a fourth inference-heavy layer that has no natural role in a debate where the turn structure is already fully specified. Parallel execution would allow Round 2 and Round 3 to fire simultaneously, but Round 3 must *read* Round 2 before responding — parallelizing them would break the debate's argumentative dependency chain entirely.

**Tradeoff:** Sequential execution means total wall-clock time is the sum of all four round latencies. On a loaded DGX Spark with 70B weights, that can be several minutes. We pre-fetch evidence via the swarm in parallel *before* the crew starts (`swarm.py` `ThreadPoolExecutor`, `config.MAX_WORKERS = 10`) specifically to hide the biggest latency cost, but the rounds themselves remain serial and there is no easy way to speed them up without restructuring the debate logic.

---

### 9. In-Memory Session Store vs. Persistent Session Database

**Choice:** A module-level `SESSIONS` dict in `api.py` (line 42) keyed by UUID, holding debate output in RAM.

**Over:** Writing sessions to SQLite, Redis, or any durable store.

**Why:** This is a hackathon project with a single-server deployment. Persisting sessions adds a database dependency, a migration story, and a cleanup policy — none of which deliver user-facing value when the expected concurrency is low and sessions are consumed immediately over WebSocket. UUIDs prevent accidental cross-session reads without any auth layer.

**Tradeoff:** A server restart drops all in-flight debates. Memory grows unboundedly if sessions are never cleared (there is no TTL or eviction today). Multi-instance horizontal scaling is impossible because sessions live in one process's heap. This is a known and accepted limitation for the current scale.

---

### 10. GPT-4o for Video / Screenshot Analysis vs. Local Vision Model

**Choice:** Route all vision tasks — per-frame scene analysis in `api.py` (lines 498–516) and bulk screenshot descriptions in `process_screenshots.py` — through `gpt-4o` via the OpenAI API.

**Over:** Running a local multimodal model (LLaVA, Qwen-VL, Pixtral) on the DGX Spark.

**Why:** Video frame analysis requires reliable spatial reasoning, OCR-quality text extraction from UI screenshots, and consistent JSON output format — tasks where GPT-4o has a demonstrated quality ceiling that local 7B-class vision models do not yet match. The video pipeline is an offline enrichment step (`/api/ingest/video`), not a hot path in the debate, so the network latency and API cost are acceptable.

**Tradeoff:** The `OPENAI_API_KEY` environment variable becomes a hard dependency for anyone using the video feature, directly contradicting the "local inference, no cloud cost" principle in Decision 1. If the key is absent the video ingest silently fails or errors (the key is fetched with a default empty string at `api.py` line 52, which will produce a 401 at call time rather than a clear startup warning). This is the architecture's most visible philosophical inconsistency and the first thing to resolve if the project moves toward full air-gap operation.

---

*Last updated: March 2026. For context on the intended DGX multi-model configuration versus the current single-model dev path, see `config.py` lines 10–13 and `.cursorrules` lines 79–85.*
