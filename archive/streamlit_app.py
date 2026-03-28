"""app.py — War Room Streamlit Frontend
Bloomberg terminal meets McKinsey deliverable.
"""

import queue
import re
import threading
import time
from typing import Any, Optional

import streamlit as st

# ── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="⚔️ War Room",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark-theme CSS ────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Backgrounds ── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
.main { background-color: #0a0a0a !important; }

[data-testid="stSidebar"] {
    background-color: #0f0f0f !important;
    border-right: 1px solid #1e1e1e;
}
section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }

/* ── Base typography ── */
html, body, .stApp { color: #d0d0d0; font-family: 'Inter', 'Segoe UI', sans-serif; }
p, li, label { color: #aaaaaa; }
strong { color: #e0e0e0; }

/* ── Hero ── */
.hero { text-align: center; padding: 3.5rem 1rem 2rem; }
.hero-title {
    font-size: 3.8rem; font-weight: 900; letter-spacing: -3px;
    color: #ffffff; font-family: 'Georgia', 'Times New Roman', serif;
    line-height: 1;
}
.hero-subtitle {
    font-size: 0.72rem; letter-spacing: 5px; text-transform: uppercase;
    color: #555555; margin-top: 0.75rem; font-family: 'Courier New', monospace;
}

/* ── Section headers ── */
.section-header {
    font-size: 0.65rem; letter-spacing: 5px; text-transform: uppercase;
    color: #3a3a3a; border-bottom: 1px solid #1e1e1e;
    padding-bottom: 0.5rem; margin: 2.5rem 0 1.25rem;
    font-family: 'Courier New', monospace;
}
.subsection-header {
    font-size: 0.6rem; letter-spacing: 4px; text-transform: uppercase;
    color: #444444; margin: 2rem 0 0.75rem;
    font-family: 'Courier New', monospace;
}

/* ── Sidebar ── */
.sidebar-title {
    font-size: 0.85rem; font-weight: 700; letter-spacing: 3px;
    text-transform: uppercase; color: #ffffff; padding: 0.25rem 0 1rem;
}
.agent-card {
    background: #141414; border: 1px solid #1e1e1e;
    border-radius: 4px; padding: 0.75rem; margin-bottom: 0.5rem;
}
.agent-desc { color: #666666; font-size: 0.73rem; line-height: 1.5; }

/* ── Status bar ── */
.status-bar {
    background: #141414; border: 1px solid #1e1e1e;
    border-left: 3px solid #ffaa00; border-radius: 4px;
    padding: 0.6rem 1rem; font-size: 0.82rem; color: #cccccc;
    font-family: 'Courier New', monospace; margin-bottom: 0.75rem;
    display: flex; align-items: center; gap: 0.75rem;
}

/* ── Round cards (in-progress / pending) ── */
.round-in-progress {
    background: #141414; border: 1px solid #2a2a2a;
    border-left: 3px solid #ffaa00; border-radius: 4px;
    padding: 0.8rem 1rem; margin-bottom: 0.4rem;
    font-size: 0.88rem; color: #cccccc;
    display: flex; align-items: center; gap: 0.75rem;
}
.round-pending {
    background: #0d0d0d; border: 1px solid #181818;
    border-radius: 4px; padding: 0.8rem 1rem; margin-bottom: 0.4rem;
    font-size: 0.88rem; color: #2e2e2e;
}
.running-label {
    margin-left: auto; font-size: 0.6rem; letter-spacing: 2px;
    color: #ffaa00; font-family: 'Courier New', monospace;
}
.pending-label {
    float: right; font-size: 0.6rem; letter-spacing: 2px;
    color: #2e2e2e; font-family: 'Courier New', monospace;
}
.timeline-connector {
    text-align: center; color: #1e1e1e; margin: 0.15rem 0;
    font-size: 0.75rem; user-select: none;
}

/* ── Pulse animation ── */
@keyframes pulse { 0%,100%{ opacity:1; } 50%{ opacity:0.25; } }
.pulse-dot {
    display: inline-block; width: 8px; height: 8px;
    background: #ffaa00; border-radius: 50%;
    animation: pulse 1.4s ease-in-out infinite; flex-shrink: 0;
}

/* ── Expander overrides ── */
[data-testid="stExpander"] {
    background-color: #141414 !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 6px !important;
    margin-bottom: 0.4rem !important;
}
[data-testid="stExpander"] summary { color: #cccccc !important; }
[data-testid="stExpanderDetails"] { border-top: 1px solid #1e1e1e !important; }

/* ── Verdict badge ── */
.verdict-badge {
    border: 2px solid; border-radius: 8px; padding: 1.5rem 1rem;
    text-align: center; background: #0f0f0f;
}
.verdict-label {
    font-size: 0.58rem; letter-spacing: 3px; text-transform: uppercase;
    color: #555555; font-family: 'Courier New', monospace;
}
.verdict-text {
    font-size: 1.8rem; font-weight: 900;
    font-family: 'Courier New', monospace; margin-top: 0.5rem;
}

/* ── Score ring ── */
.score-ring-container { text-align: center; }
.score-label {
    font-size: 0.58rem; letter-spacing: 3px; text-transform: uppercase;
    color: #555555; font-family: 'Courier New', monospace; margin-bottom: 0.5rem;
}
.score-ring { width: 150px; height: 150px; }

/* ── Findings matrix ── */
.matrix-header {
    font-size: 0.65rem; letter-spacing: 2px; text-transform: uppercase;
    color: #777777; margin-bottom: 0.75rem; font-family: 'Courier New', monospace;
    border-bottom: 1px solid #1e1e1e; padding-bottom: 0.4rem;
}
.issue-item {
    background: #0f0f0f; border: 1px solid #1e1e1e; border-radius: 3px;
    padding: 0.55rem 0.75rem; margin-bottom: 0.35rem;
    font-size: 0.8rem; color: #bbbbbb; line-height: 1.45;
}
.severity-badge {
    font-size: 0.58rem; font-family: 'Courier New', monospace;
    padding: 0.1rem 0.45rem; border-radius: 2px;
    color: #000; font-weight: bold; margin-right: 0.4rem;
}
.positioning-text {
    font-size: 0.84rem; color: #999999; line-height: 1.65;
}

/* ── Priority fix cards ── */
.fix-card {
    background: #0f0f0f; border: 1px solid #1e1e1e;
    border-radius: 6px; padding: 1rem; height: 100%;
    margin-bottom: 0.5rem;
}
.fix-priority {
    display: inline-block; border: 1px solid;
    font-size: 0.65rem; font-family: 'Courier New', monospace;
    font-weight: bold; padding: 0.15rem 0.5rem;
    border-radius: 2px; margin-bottom: 0.75rem; letter-spacing: 1px;
}
.fix-content { font-size: 0.81rem; color: #cccccc; line-height: 1.5; margin-bottom: 0.75rem; }
.fix-impact { font-size: 0.73rem; color: #444444; font-family: 'Courier New', monospace; }
.fix-impact strong { color: #00ff88; }

/* ── Blind spot callout ── */
.blind-spot-callout {
    background: #0d0a00; border: 1px solid #3d2e00;
    border-left: 4px solid #ffaa00; border-radius: 6px;
    padding: 1.25rem 1.25rem 1.25rem 1rem;
    display: flex; gap: 1rem; align-items: flex-start;
}
.blind-spot-icon { font-size: 1.4rem; flex-shrink: 0; line-height: 1.5; }
.blind-spot-text { font-size: 0.85rem; color: #dddddd; line-height: 1.65; }

/* ── Evidence stats ── */
.evidence-stat {
    background: #0f0f0f; border: 1px solid #1e1e1e; border-radius: 4px;
    padding: 0.75rem; text-align: center;
}
.evidence-stat-value {
    font-size: 1.4rem; font-weight: 700; color: #ffffff;
    font-family: 'Courier New', monospace;
}
.evidence-stat-label {
    font-size: 0.62rem; letter-spacing: 2px; text-transform: uppercase;
    color: #444444; margin-top: 0.2rem; font-family: 'Courier New', monospace;
}

/* ── Input / button ── */
[data-testid="stTextInput"] input {
    background-color: #141414 !important; color: #e0e0e0 !important;
    border: 1px solid #2a2a2a !important; border-radius: 4px !important;
    font-size: 0.97rem !important; padding: 0.65rem 0.9rem !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #00ff88 !important;
    box-shadow: 0 0 0 1px #00ff88 !important;
}
[data-testid="stTextInput"] input::placeholder { color: #3a3a3a !important; }

button[kind="primary"] {
    background-color: #00ff88 !important; color: #000000 !important;
    font-weight: 700 !important; border: none !important;
    letter-spacing: 0.5px !important; border-radius: 4px !important;
}
button[kind="primary"]:hover { background-color: #00cc6a !important; }
button[kind="primary"]:disabled {
    background-color: #1a1a1a !important; color: #444444 !important;
}

/* ── Metric overrides ── */
[data-testid="stMetric"] {
    background: #0f0f0f; border: 1px solid #1e1e1e;
    border-radius: 4px; padding: 0.75rem !important;
}
[data-testid="stMetricLabel"] p {
    color: #444444 !important; font-size: 0.65rem !important;
    text-transform: uppercase; letter-spacing: 1.5px;
    font-family: 'Courier New', monospace;
}
[data-testid="stMetricValue"] { color: #ffffff !important; font-family: 'Courier New', monospace !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #1e1e1e; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2e2e2e; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Round metadata ────────────────────────────────────────────────────────────
ROUNDS = [
    {
        "num": 1,
        "agent": "First-Timer",
        "icon": "🟢",
        "color": "#00ff88",
        "subtitle": "Onboarding Audit",
        "model": "mistral:7b",
    },
    {
        "num": 2,
        "agent": "Daily Driver",
        "icon": "🔵",
        "color": "#0088ff",
        "subtitle": "Power User Challenge",
        "model": "mistral:7b",
    },
    {
        "num": 3,
        "agent": "First-Timer",
        "icon": "🟢",
        "color": "#00ff88",
        "subtitle": "Defense & Rebuttal",
        "model": "mistral:7b",
    },
    {
        "num": 4,
        "agent": "Buyer",
        "icon": "🔴",
        "color": "#ff4444",
        "subtitle": "Executive Verdict",
        "model": "mistral:7b",
    },
]

# ── Session-state bootstrap ───────────────────────────────────────────────────
_DEFAULTS: dict = {
    "started": False,
    "running": False,
    "complete": False,
    "error": None,
    "product": "",
    "rounds": [],
    "personas_ready": False,
    "start_time": None,
    "result_queue": None,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Background crew runner ────────────────────────────────────────────────────
def _run_crew(product: str, result_q: queue.Queue) -> None:
    """Runs in a daemon thread. Emits typed tuples onto result_q."""
    try:
        from crew import build_crew  # import here so Streamlit loads fast

        round_counter: list[int] = [0]
        round_start: list[float] = [time.time()]

        def on_task_done(task_output: Any) -> None:
            round_counter[0] += 1
            elapsed = time.time() - round_start[0]
            raw = getattr(task_output, "raw", str(task_output))
            agent_role = getattr(task_output, "agent", "Unknown")
            result_q.put(("round", round_counter[0], raw, agent_role, elapsed))
            round_start[0] = time.time()

        result_q.put(("status", "generating_personas"))
        crew = build_crew(product, task_callback=on_task_done)
        result_q.put(("status", "personas_ready"))
        round_start[0] = time.time()
        crew.kickoff()
        result_q.put(("complete", None))

    except Exception as exc:
        result_q.put(("error", str(exc)))


# ── Parsers ───────────────────────────────────────────────────────────────────
def count_citations(text: str) -> int:
    """Count [APP | source type] RAG citation headers in agent output."""
    return len(re.findall(r"\[[A-Z][A-Z\s]+\| .+?\]", text))


def parse_verdict(text: str) -> str:
    """Extract buy/no-buy verdict from Buyer's Round 4 output."""
    for pattern in [
        r"BUY DECISION\s*[:\-–]+\s*([^\n.]+)",
        r"DECISION\s*[:\-–]+\s*([^\n.]+)",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            v = m.group(1).strip().upper()
            if "WITH CONDITIONS" in v:
                return "YES WITH CONDITIONS"
            if v.startswith("YES"):
                return "YES"
            if v.startswith("NO"):
                return "NO"
    m2 = re.search(r"\b(YES WITH CONDITIONS|YES|NO)\b", text, re.IGNORECASE)
    return m2.group(1).upper() if m2 else "—"


def parse_score(text: str) -> Optional[int]:
    """Extract 1–100 numeric score from Buyer's output."""
    for pattern in [
        r"OVERALL SCORE\s*[:\-–]+\s*(\d+)",
        r"(\d+)\s*/\s*100",
        r"SCORE\s*[:\-–]+\s*(\d+)",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 1 <= val <= 100:
                return val
    return None


def parse_fixes(text: str) -> list[dict]:
    """Extract top 3 priority fixes with estimated retention impact."""
    fixes: list[dict] = []

    # Isolate the TOP 3 FIXES section if it exists
    sec_m = re.search(
        r"TOP\s+3\s+FIXES?\s*[:\-–]*(.*?)(?:\n\s*[A-Z][A-Z ]{4,}\s*[:\-–]|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    section = sec_m.group(1) if sec_m else text

    # Pull numbered items
    items = re.findall(
        r"(?:^|\n)\s*(\d+)[.)]\s*(.+?)(?=\n\s*\d+[.)]|\Z)",
        section,
        re.DOTALL,
    )
    priority_labels = ["P0", "P1", "P2"]
    for i, (_, content) in enumerate(items[:3]):
        content = content.strip()
        impact_m = re.search(r"(\d+)\s*%", content)
        impact = f"{impact_m.group(1)}%" if impact_m else "—"
        fixes.append(
            {
                "priority": priority_labels[i],
                "content": content[:480],
                "impact": impact,
            }
        )
    return fixes


def parse_blind_spot(text: str) -> str:
    """Extract the strategic blind spot from Buyer's output."""
    m = re.search(
        r"(?:THE\s+)?BLIND SPOT\s*[:\-–]*(.*?)(?:\n\s*[A-Z][A-Z ]{4,}\s*[:\-–]|\n\s*\d+\.|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip()[:700] if m else ""


def parse_competitive_positioning(text: str) -> str:
    """Extract competitive positioning paragraph from Buyer's output."""
    m = re.search(
        r"COMPETITIVE POSITIONING\s*[:\-–]*(.*?)(?:\n\s*[A-Z][A-Z ]{4,}\s*[:\-–]|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip()[:900] if m else ""


def parse_issues_with_severity(rounds: list[dict]) -> list[dict]:
    """Scan all rounds for SEVERITY ratings and extract surrounding context."""
    issues: list[dict] = []
    seen: set[str] = set()
    sev_re = re.compile(
        r"(?:SEVERITY|SEV)[:\s]+(\d+)(?:/10)?",
        re.IGNORECASE,
    )
    for r in rounds:
        for m in sev_re.finditer(r["output"]):
            sev = int(m.group(1))
            # Pull up to 200 chars before as context
            start = max(0, m.start() - 200)
            snippet = r["output"][start : m.end()].strip()
            # Deduplicate by first 60 chars
            key = snippet[:60]
            if key not in seen:
                seen.add(key)
                issues.append({"text": snippet[-200:], "severity": sev})
    # Sort by severity descending
    return sorted(issues, key=lambda x: x["severity"], reverse=True)


# ── UI helpers ────────────────────────────────────────────────────────────────
def _verdict_color(verdict: str) -> str:
    if verdict == "YES":
        return "#00ff88"
    if verdict == "NO":
        return "#ff4444"
    if "CONDITIONS" in verdict:
        return "#ffaa00"
    return "#666666"


def _score_color(score: Optional[int]) -> str:
    if score is None:
        return "#555555"
    if score >= 70:
        return "#00ff88"
    if score >= 40:
        return "#ffaa00"
    return "#ff4444"


def _fmt_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    return f"{seconds / 60:.1f}m"


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-title">⚔️ WAR ROOM</div>', unsafe_allow_html=True
        )
        st.caption("Multi-Model Adversarial Product Intelligence")

        with st.expander("About the Methodology", expanded=False):
            st.markdown(
                """
**War Room** runs your product through a structured 4-round adversarial debate
between three distinct AI personas, each grounded in **31,668 real user evidence
chunks** from Reddit, Hacker News, Google Play, and app metadata.

**Round 1 — First-Timer:** Onboarding audit, first impressions, 3 critical problems.

**Round 2 — Daily Driver:** Challenges Round 1, exposes hidden long-term problems.

**Round 3 — First-Timer:** Defends or concedes, updates severity ratings.

**Round 4 — Buyer:** Settles disputes, business-critical assessment, final verdict.
"""
            )

        st.markdown("---")
        st.markdown("**Debate Agents**")
        for r in ROUNDS[:3]:  # only 3 unique agents
            if r["num"] == 3:
                continue  # First-Timer already shown
            desc_map = {
                1: "New user with zero patience. Trusts App Store reviews and Reddit first impressions.",
                2: "Power user who knows every shortcut. Trusts G2 reviews and HN technical threads.",
                4: "Budget holder making a team decision. Trusts pricing data, integrations, business reviews.",
            }
            st.markdown(
                f"""<div class="agent-card">
<span style="font-size:1rem">{r['icon']}</span>
<strong style="color:#e0e0e0"> {r['agent']}</strong><br>
<span class="agent-desc">{desc_map.get(r['num'], '')}</span>
</div>""",
                unsafe_allow_html=True,
            )
        # Buyer
        buyer_cfg = ROUNDS[3]
        st.markdown(
            f"""<div class="agent-card">
<span style="font-size:1rem">{buyer_cfg['icon']}</span>
<strong style="color:#e0e0e0"> {buyer_cfg['agent']}</strong><br>
<span class="agent-desc">Budget holder making a team decision. Trusts pricing data, integrations, business reviews.</span>
</div>""",
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("**Knowledge Base**")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Chunks", "31,668")
            st.metric("Reddit", "22,692")
            st.metric("HN", "6,348")
        with c2:
            st.metric("Apps", "20")
            st.metric("Play Store", "2,608")
            st.metric("Metadata", "20")

        if st.session_state.started and st.session_state.product:
            st.markdown("---")
            st.markdown("**Current Analysis**")
            st.caption(st.session_state.product[:80])
            if st.session_state.start_time:
                elapsed = time.time() - st.session_state.start_time
                st.caption(f"Running for {_fmt_elapsed(elapsed)}")
            if st.session_state.complete:
                if st.button("↩ New Analysis", use_container_width=True):
                    for key in list(_DEFAULTS.keys()):
                        st.session_state[key] = _DEFAULTS[key]
                    st.rerun()


# ── Hero ──────────────────────────────────────────────────────────────────────
def render_hero() -> None:
    st.markdown(
        """
<div class="hero">
  <div class="hero-title">⚔️ THE WAR ROOM</div>
  <div class="hero-subtitle">Multi-Model Adversarial Product Intelligence</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ── Input form ────────────────────────────────────────────────────────────────
def render_input_form() -> None:
    col_in, col_btn = st.columns([6, 1])
    with col_in:
        product_val = st.text_input(
            label="product",
            placeholder="e.g.  Notion — all-in-one workspace for notes, wikis, and project management",
            label_visibility="collapsed",
            disabled=st.session_state.running,
            key="product_input_field",
            value=st.session_state.product if st.session_state.started else "",
        )
    with col_btn:
        deploy = st.button(
            "⚔️ Deploy",
            use_container_width=True,
            disabled=st.session_state.running or not (product_val or "").strip(),
            type="primary",
        )

    if deploy and (product_val or "").strip():
        # Reset all state for a fresh run
        st.session_state.rounds = []
        st.session_state.complete = False
        st.session_state.error = None
        st.session_state.personas_ready = False
        st.session_state.product = product_val.strip()
        st.session_state.start_time = time.time()
        result_q: queue.Queue = queue.Queue()
        st.session_state.result_queue = result_q
        st.session_state.running = True
        st.session_state.started = True
        t = threading.Thread(
            target=_run_crew,
            args=(product_val.strip(), result_q),
            daemon=True,
        )
        t.start()
        st.rerun()


# ── Queue drain ───────────────────────────────────────────────────────────────
def drain_queue() -> None:
    """Consume all pending messages from the background thread's queue."""
    result_q = st.session_state.get("result_queue")
    if result_q is None:
        return
    while not result_q.empty():
        msg = result_q.get_nowait()
        tag = msg[0]
        if tag == "status":
            if msg[1] == "personas_ready":
                st.session_state.personas_ready = True
        elif tag == "round":
            _, num, raw, agent_role, elapsed = msg
            st.session_state.rounds.append(
                {
                    "num": num,
                    "agent": agent_role,
                    "output": raw,
                    "elapsed": elapsed,
                    "citations": count_citations(raw),
                }
            )
        elif tag == "complete":
            st.session_state.running = False
            st.session_state.complete = True
        elif tag == "error":
            st.session_state.running = False
            st.session_state.error = msg[1]


# ── Debate feed ───────────────────────────────────────────────────────────────
def render_debate_feed() -> None:
    completed = {r["num"]: r for r in st.session_state.rounds}
    n_done = len(completed)
    is_running = st.session_state.running

    st.markdown(
        '<div class="section-header">LIVE DEBATE FEED</div>', unsafe_allow_html=True
    )

    for cfg in ROUNDS:
        num = cfg["num"]
        done = completed.get(num)

        if done:
            citations = done.get("citations", 0)
            elapsed = done.get("elapsed", 0.0)
            label = (
                f"{cfg['icon']}  Round {num} — {cfg['agent']}: {cfg['subtitle']}"
                f"   ·   {_fmt_elapsed(elapsed)}"
                f"   ·   {citations} source{'s' if citations != 1 else ''} cited"
            )
            # Expand Round 4 (verdict) and the most recent completed round
            auto_open = num == 4 or num == n_done
            with st.expander(label, expanded=auto_open):
                st.markdown(done["output"])

        elif is_running and n_done == num - 1:
            st.markdown(
                f"""<div class="round-in-progress">
  <span class="pulse-dot"></span>
  {cfg['icon']}  Round {num} — {cfg['agent']}: {cfg['subtitle']}
  <span class="running-label">● RUNNING</span>
</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div class="round-pending">
  ○&nbsp; Round {num} — {cfg['agent']}: {cfg['subtitle']}
  <span class="pending-label">PENDING</span>
</div>""",
                unsafe_allow_html=True,
            )

        # Timeline connector between rounds
        if num < 4:
            if done or (is_running and n_done >= num):
                arrow_color = "#2a2a2a"
            else:
                arrow_color = "#181818"
            st.markdown(
                f'<div class="timeline-connector" style="color:{arrow_color}">▼</div>',
                unsafe_allow_html=True,
            )


# ── Executive summary ─────────────────────────────────────────────────────────
def render_executive_summary() -> None:
    rounds = st.session_state.rounds
    if len(rounds) < 4:
        return

    buyer_output = rounds[3]["output"]
    verdict = parse_verdict(buyer_output)
    score = parse_score(buyer_output)
    fixes = parse_fixes(buyer_output)
    blind_spot = parse_blind_spot(buyer_output)
    competitive = parse_competitive_positioning(buyer_output)
    issues = parse_issues_with_severity(rounds)

    st.markdown("---")
    st.markdown(
        '<div class="section-header">EXECUTIVE SUMMARY</div>', unsafe_allow_html=True
    )

    # ── Verdict + Score ──────────────────────────────────────────────────────
    vc = _verdict_color(verdict)
    sc = _score_color(score)
    ring_pct = score or 0
    circumference = 314  # 2π × r where r=50

    col_verdict, col_score, col_spacer = st.columns([2, 2, 5])

    with col_verdict:
        st.markdown(
            f"""<div class="verdict-badge" style="border-color:{vc}; color:{vc};">
  <div class="verdict-label">BUY DECISION</div>
  <div class="verdict-text">{verdict}</div>
</div>""",
            unsafe_allow_html=True,
        )

    with col_score:
        if score is not None:
            dash = f"{circumference * ring_pct / 100:.1f}"
            st.markdown(
                f"""<div class="score-ring-container">
  <div class="score-label">OVERALL SCORE</div>
  <svg class="score-ring" viewBox="0 0 120 120">
    <circle cx="60" cy="60" r="50" fill="none" stroke="#1e1e1e" stroke-width="10"/>
    <circle cx="60" cy="60" r="50" fill="none" stroke="{sc}" stroke-width="10"
      stroke-dasharray="{dash} {circumference}"
      stroke-linecap="round"
      transform="rotate(-90 60 60)"/>
    <text x="60" y="56" text-anchor="middle" dominant-baseline="central"
      font-size="26" font-weight="bold" fill="{sc}" font-family="monospace">{score}</text>
    <text x="60" y="78" text-anchor="middle"
      font-size="10" fill="#444444" font-family="monospace">/100</text>
  </svg>
</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Score not found in Buyer output.")

    # ── Key Findings Matrix ──────────────────────────────────────────────────
    st.markdown(
        '<div class="subsection-header">KEY FINDINGS</div>', unsafe_allow_html=True
    )
    col_issues, col_comp = st.columns(2)

    with col_issues:
        st.markdown(
            '<div class="matrix-header">⚠ CRITICAL ISSUES</div>',
            unsafe_allow_html=True,
        )
        if issues:
            for issue in issues[:6]:
                sev = issue["severity"]
                if sev >= 8:
                    sev_bg = "#ff4444"
                elif sev >= 5:
                    sev_bg = "#ffaa00"
                else:
                    sev_bg = "#0088ff"
                badge = f'<span class="severity-badge" style="background:{sev_bg}">SEV&nbsp;{sev}</span>'
                txt = re.sub(r"\s+", " ", issue["text"])
                st.markdown(
                    f'<div class="issue-item">{badge}{txt}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No severity ratings parsed — see Buyer output for full breakdown.")

    with col_comp:
        st.markdown(
            '<div class="matrix-header">📊 COMPETITIVE POSITIONING</div>',
            unsafe_allow_html=True,
        )
        if competitive:
            st.markdown(
                f'<div class="positioning-text">{competitive}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption(
                "Competitive positioning not parsed — see Round 4 for Buyer's full analysis."
            )

    # ── Priority Fixes ───────────────────────────────────────────────────────
    if fixes:
        st.markdown(
            '<div class="subsection-header">PRIORITY FIXES</div>',
            unsafe_allow_html=True,
        )
        priority_colors = {"P0": "#ff4444", "P1": "#ffaa00", "P2": "#0088ff"}
        fix_cols = st.columns(len(fixes))
        for i, fix in enumerate(fixes):
            with fix_cols[i]:
                pc = priority_colors.get(fix["priority"], "#666666")
                st.markdown(
                    f"""<div class="fix-card">
  <div class="fix-priority" style="color:{pc}; border-color:{pc};">{fix["priority"]}</div>
  <div class="fix-content">{fix["content"]}</div>
  <div class="fix-impact">Est. retention impact: <strong>{fix["impact"]}</strong></div>
</div>""",
                    unsafe_allow_html=True,
                )

    # ── Strategic Blind Spot ─────────────────────────────────────────────────
    if blind_spot:
        st.markdown(
            '<div class="subsection-header">STRATEGIC BLIND SPOT</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""<div class="blind-spot-callout">
  <div class="blind-spot-icon">⚡</div>
  <div class="blind-spot-text">{blind_spot}</div>
</div>""",
            unsafe_allow_html=True,
        )

    # ── Evidence Base ────────────────────────────────────────────────────────
    st.markdown(
        '<div class="subsection-header">EVIDENCE BASE</div>', unsafe_allow_html=True
    )
    total_citations = sum(r.get("citations", 0) for r in rounds)
    total_elapsed = sum(r.get("elapsed", 0.0) for r in rounds)

    stat_cols = st.columns(5)
    stats = [
        (str(total_citations), "RAG Chunks Cited"),
        ("4 / 4", "Rounds Completed"),
        ("31,668", "KB Total Chunks"),
        (_fmt_elapsed(total_elapsed), "Debate Duration"),
        ("20", "Apps Covered"),
    ]
    for col, (val, label) in zip(stat_cols, stats):
        with col:
            st.markdown(
                f"""<div class="evidence-stat">
  <div class="evidence-stat-value">{val}</div>
  <div class="evidence-stat-label">{label}</div>
</div>""",
                unsafe_allow_html=True,
            )


# ── Main render loop ──────────────────────────────────────────────────────────
render_sidebar()
render_hero()
render_input_form()

# ── Drain queue on each rerun while running ───────────────────────────────────
if st.session_state.running:
    drain_queue()

# ── Status banner ─────────────────────────────────────────────────────────────
if st.session_state.error:
    err = st.session_state.error
    if any(kw in err.lower() for kw in ("ollama", "connection", "refused", "connect")):
        st.error(
            "🔌 **Ollama is not running.**  "
            "Start it and ensure the model is pulled:\n\n"
            "```\nollama serve\nollama pull mistral:7b\n```"
        )
    else:
        st.error(f"**Crew error:** {err}")

elif st.session_state.running:
    n_done = len(st.session_state.rounds)
    if not st.session_state.personas_ready:
        st.markdown(
            '<div class="status-bar"><span class="pulse-dot"></span>'
            "🧠&nbsp; Generating adversarial personas…</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="status-bar"><span class="pulse-dot"></span>'
            f"⚔️&nbsp; Round {n_done + 1} of 4 in progress…</div>",
            unsafe_allow_html=True,
        )

# ── Debate feed + executive summary ──────────────────────────────────────────
if st.session_state.started:
    render_debate_feed()

    if st.session_state.complete:
        render_executive_summary()
    elif st.session_state.running:
        time.sleep(2)
        st.rerun()
