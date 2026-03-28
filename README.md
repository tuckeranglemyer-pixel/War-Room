# The War Room

Three AI architectures. Four rounds of adversarial debate. Real evidence. One verdict.

## What It Does
Multi-model adversarial QA testing for software products. A meta-agent analyzes the submitted product and auto-generates three consumer personas — a first-time user, a power user, and a business buyer — each powered by a different LLM architecture, debating across 4 rounds grounded in real user review data from 7,000+ sources.

## Architecture
- **Meta-Agent:** Auto-generates product-specific adversarial personas before debate begins
- **Orchestration:** CrewAI sequential process with context chaining across 4 rounds
- **Models:** Llama 3.3-70B (First-Timer), Qwen3-32B (Daily Driver), Mistral-Small-24B (Buyer) on NVIDIA DGX Spark
- **RAG:** ChromaDB with 7,000+ real user reviews — App Store, Reddit, G2, Hacker News
- **Backend:** FastAPI + WebSocket streaming
- **Frontend:** React + Tailwind

## Debate Structure
1. **Round 1 — Initial Analysis:** First-Timer evaluates onboarding, finds 3 critical problems
2. **Round 2 — Challenge:** Daily Driver agrees/disagrees with evidence, exposes hidden problems
3. **Round 3 — Rebuttal:** First-Timer defends or concedes with counter-evidence
4. **Round 4 — Verdict:** Buyer settles disagreements, scores 1-100, delivers top 3 fixes

## How To Run
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python crew.py
```

Built at the 2026 yconic New England Inter-Collegiate AI Hackathon by Tucker Anglemyer & Griffin Kovach.
