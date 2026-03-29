# The War Room — 3-Minute Pitch

This file is written so a **human judge** can follow it live *and* so an **AI summary** (e.g. VC tooling) can extract a clean story: plain-English first, technical precision in the labeled section below.

---

## One-page extract (for judges & AI summaries)

**Non-technical (what it is):** The War Room turns scattered user feedback into a structured product verdict—score, priorities, and cited evidence—in minutes instead of weeks. Teams upload or pick a product, the system gathers real review evidence, and multiple AI perspectives argue with each other so one model cannot silently agree with itself.

**Technical (what it is):** FastAPI + React production app; ChromaDB RAG over **31,668** curated chunks across **20** PM tools; CrewAI-style orchestration with **multi-model** debate design (distinct Llama / Qwen / Mistral roles in the core debate engine); separate **hardware-adaptive** DGX path for local runs (thermal-managed, often **one** Ollama model at a time for stability—see README). Dual inference: **cloud** (APIs, fast demos) and **DGX** (data sovereignty, on-prem).

**Problem:** Manual research and panels are slow ($5K–$200K, weeks) or shallow (single-model chat with no evidence or structured disagreement).

**Traction (hackathon):** **3** real teams ran full video QA on their own builds; **200** commits in **~30** hours; live on **Vercel + Railway**; **10+** page views, **5** GitHub stars; distribution on HN / Discord / Reddit.

**Moat:** Large curated evidence corpus + adversarial protocol + optional full local inference for sensitive data.

**Team:** Tucker Anglemyer (orchestration, API, frontend, deployment) · Griffin Kovach (RAG corpus, ChromaDB, data quality).

---

## OPENING (15 seconds)

"The War Room compresses the research gap between a 3-person startup and a 300-person enterprise to zero. What McKinsey charges $200K and six weeks for, we deliver in minutes—with citations."

---

## THE PROBLEM (30 seconds)

- Product teams spend **40+ hours** and **$5K–$200K** per evaluation cycle
- UserTesting: **$49/response**, **2–5 day** turnaround
- ChatGPT/Claude: instant but single-model, weak evidence grounding, no structured disagreement
- Root cause: **one model cannot reliably challenge its own assumptions**

---

## THE SOLUTION (30 seconds)

- **Three adversarial roles** debate your product using **31,668** real user reviews (not a generic web scrape—curated RAG)
- **Architectural independence:** we route different personas to **different model families** (Llama / Qwen / Mistral) so disagreement is real—not three copies of the same API
- **MIT (Du et al., 2023):** multi-agent debate **91%** factual accuracy vs **82%** same-model—**9** points
- **Industry:** Mitsubishi Electric (Jan 2026) validated multi-agent argumentation for expert QA—same pattern we use for product decisions

*Judge note:* On DGX under thermal stress, we may run **sequentially** or a **single** local model for stability; the *design* is multi-architecture debate; the *deployment* adapts to hardware. Say that in one breath if asked.

---

## LIVE DEMO (60 seconds)

[Live: Griffin drives ngrok / production URL as needed]

- Landing page: **20** curated products (instant path) or upload a **real product video**
- Narrate the pipeline honestly: *"Evidence is being pulled from our review corpus; specialists are producing structured sections; you will see a scored verdict with priorities."*
- If the run is **cloud:** *"API inference—fast, reliable for demo day."*
- If the run is **DGX:** *"Local Ollama on the Spark—data stays on the box; our runner watches thermals and degrades gracefully—we learned that the hard way."*
- End on the **verdict card**: real **score**, **recommendation**, and **actionable** findings (e.g. from `demo_outputs/taskflow_dgx_run.json`: **65/100**, NEEDS_WORK, concrete Monday priority)

*Avoid:* Claiming "three models live right now" unless that specific demo instance is actually running three distinct weights concurrently.

---

## WHAT WE SHIPPED (30 seconds)

- **200** commits in **~30** hours
- **3** real user sessions—teams analyzed **their** products and **implemented** findings
- **DGX Spark**, **128GB** unified memory—built for concurrent large-model serving; **7+** thermal incidents → **adaptive execution engine** (tiered thermal management)
- **Frontend:** Vercel · **Backend:** Railway · **Dual inference:** cloud for speed and reliability, DGX for sovereignty
- **10+** page views (Vercel Analytics), **5** GitHub stars

---

## TRACTION & VALIDATION (15 seconds)

- **3** users ran the **full video QA** pipeline on real hackathon projects **today**
- All **3** got actionable output and **shipped changes** from it
- Posted: **Hacker News**, **Discord**, **Reddit**
- Quote: *"The AGREE/DISAGREE thing is sick, it's like watching AI lawyers"* (Instagram DM)

---

## THE MOAT (15 seconds)

- **31,668** evidence chunks—**40+ hours** to curate; greenfield competitors start at zero
- **Data flywheel:** sessions improve retrieval signals over time
- **Protocol depth:** meta-agent → swarm → debate—not a thin wrapper
- **Local option:** enterprises keep sensitive inputs on-prem; **zero** per-token cloud cost when fully local on DGX

---

## CLOSE (15 seconds)

"This isn't a chatbot wrapper. It's **infrastructure** for **evidence-backed, adversarial** product intelligence. Every product decision could run through this kind of check—fast, cited, and stress-tested. That's The War Room."

---

## If a judge asks one question (cheat sheet)

| Question | Short answer |
|----------|----------------|
| Is it just ChatGPT? | No—structured debate, RAG on **31,668** chunks, multiple model families, verdict schema. |
| Where's the data? | Public reviews + metadata across **20** tools; ChromaDB; optional local inference. |
| What broke in prod? | DGX thermals—solved with adaptive tiers and honest degradation. |
| Who uses it? | **3** real teams this weekend; **6** pre-loaded product runs in docs; live URLs in README. |
