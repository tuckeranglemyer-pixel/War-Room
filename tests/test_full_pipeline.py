"""
WAR ROOM — Full End-to-End Pipeline Test
=========================================
Runs every pipeline stage in sequence, prints results at each step, and
saves the exact prompt text each debate agent would receive to
tests/pipeline_output/.

Usage:
    python tests/test_full_pipeline.py                        # synthetic mode
    python tests/test_full_pipeline.py path/to/demo.mp4       # real video

Requirements:
    - OPENAI_API_KEY in environment
    - ./chroma_db with a pm_tools collection
    - screenshot_chunks.json at repo root
    - ffmpeg on PATH (only needed when passing a real video)
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _banner(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _step(msg: str) -> None:
    print(f"  {msg}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:  # noqa: PLR0912, PLR0915  (pipeline is inherently long)
    video_path: str | None = sys.argv[1] if len(sys.argv) > 1 else None

    _banner("WAR ROOM — FULL PIPELINE TEST")

    # ======================================================================
    # STAGE 0: Verify dependencies
    # ======================================================================
    print("\n[STAGE 0] Verifying dependencies...")

    api_key = os.environ.get("OPENAI_API_KEY", "")
    assert api_key, "Set OPENAI_API_KEY environment variable before running."

    import chromadb  # noqa: PLC0415

    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_collection("pm_tools")
    _step(f"ChromaDB: {collection.count()} chunks in pm_tools")

    suite_path = Path("screenshot_chunks.json")
    assert suite_path.exists(), (
        f"Missing {suite_path}. Expected at repo root (screenshot_chunks.json)."
    )
    with open(suite_path, encoding="utf-8") as fh:
        suite = json.load(fh)
    _step(f"Screenshot suite: {len(suite)} analyses loaded from {suite_path}")

    _step("Dependencies OK")

    # ======================================================================
    # STAGE 1: Simulate user onboarding answers
    # ======================================================================
    print("\n[STAGE 1] User onboarding context")

    user_context: dict[str, str] = {
        "product_name": "TaskFlow",
        "productDescription": (
            "A project management tool for small marketing teams that combines"
            " kanban boards with automated client reporting."
        ),
        "target_user": "Non-technical marketing managers at agencies with 5-20 employees",
        "competitors": "Asana, Monday.com, Trello, ClickUp",
        "differentiator": (
            "Built-in client reporting that auto-generates from task completion"
            " data — no manual report building"
        ),
        "product_stage": "MVP with 12 beta users",
    }

    for key, val in user_context.items():
        _step(f"{key}: {val}")

    # ======================================================================
    # STAGE 2: Frame extraction
    # ======================================================================
    print("\n[STAGE 2] Frame extraction")

    frames: list[str] = []
    tmp_dir: str | None = None

    if video_path and Path(video_path).exists():
        _step(f"Video: {video_path}")
        from src.api.server import extract_key_frames  # noqa: PLC0415

        tmp_dir = tempfile.mkdtemp(prefix="warroom_test_")
        raw_frames = extract_key_frames(video_path, tmp_dir)
        frames = [str(p) for p in raw_frames]
        _step(f"Extracted {len(frames)} frames via ffmpeg")
    else:
        _step("No video provided — scanning screenshot_suite/data/ for test images")
        data_dir = Path("screenshot_suite/data")

        if data_dir.exists():
            for app_dir in sorted(data_dir.iterdir()):
                ss_dir = app_dir / "screenshots"
                if ss_dir.exists():
                    for img in sorted(ss_dir.iterdir()):
                        if img.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                            frames.append(str(img))
                            if len(frames) >= 3:
                                break
                if len(frames) >= 3:
                    break

        if frames:
            _step(f"Using {len(frames)} images from screenshot_suite/data/: "
                  f"{[Path(f).name for f in frames]}")
        else:
            _step("No test images found — switching to synthetic frame mode (no API calls)")

    # ======================================================================
    # STAGE 3: GPT-4o Vision analysis (dual-format)
    # ======================================================================
    print("\n[STAGE 3] GPT-4o Vision analysis (dual-format)")

    from openai import OpenAI  # noqa: PLC0415

    oai = OpenAI(api_key=api_key)

    video_frame_prompt = (
        f"You are analyzing a walkthrough frame of a product called"
        f" {user_context['product_name']}.\n"
        f"Product: {user_context['productDescription']}\n"
        f"Target user: {user_context['target_user']}\n\n"
        "Analyze this frame for:\n"
        "1. Screen identification — what view/page is this?\n"
        "2. Journey moment — where in the user journey is this? "
        "(onboarding, core workflow, settings, etc.)\n"
        "3. Friction points from the target user's perspective\n"
        "4. Rate this screen 1-10 from: First-Timer, Daily Driver, and Buyer perspectives\n"
        "5. What competitor screens does this remind you of?\n\n"
        "Write 3-4 detailed paragraphs."
    )

    ux_match_prompt = (
        "You are a senior UX analyst. Analyze this screenshot with EXTREME specificity.\n"
        "Cover: 1) Screen ID (app, exact view), 2) Layout & visual hierarchy, "
        "3) Every interactive element, 4) UX friction points (be brutal), "
        "5) UX strengths, 6) Onboarding impact (cognitive load 1-10), "
        "7) Competitor comparison. Write 4-6 detailed paragraphs. "
        "Be specific enough to reconstruct the screen."
    )

    frame_analyses: list[dict] = []

    if frames:
        for i, frame_path in enumerate(frames):
            _step(f"Frame {i + 1}/{len(frames)}: {Path(frame_path).name}")

            with open(frame_path, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode()

            ext = Path(frame_path).suffix.lower().lstrip(".")
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(
                ext, "image/png"
            )
            data_url = f"data:{mime};base64,{b64}"

            # Call 1: debate analysis
            print(f"    GPT-4o call 1 (debate format)...", end=" ", flush=True)
            r1 = oai.chat.completions.create(
                model="gpt-4o",
                max_tokens=1200,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": video_frame_prompt},
                            {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                        ],
                    }
                ],
            )
            debate_analysis = r1.choices[0].message.content or ""
            print(f"OK ({len(debate_analysis)} chars)")

            # Call 2: UX match analysis
            print(f"    GPT-4o call 2 (UX match format)...", end=" ", flush=True)
            r2 = oai.chat.completions.create(
                model="gpt-4o",
                max_tokens=1500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"This is a screenshot of a product.\n\n{ux_match_prompt}",
                            },
                            {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                        ],
                    }
                ],
            )
            ux_analysis = r2.choices[0].message.content or ""
            print(f"OK ({len(ux_analysis)} chars)")

            frame_analyses.append(
                {
                    "frame_number": i,
                    "frame_path": frame_path,
                    "debate_analysis": debate_analysis,
                    "ux_analysis": ux_analysis,
                }
            )
            time.sleep(0.5)
    else:
        # Fully synthetic fallback — no API calls, just structured test data
        _step("Using synthetic frame analyses (no GPT-4o calls)")
        frame_analyses = [
            {
                "frame_number": 0,
                "frame_path": "synthetic",
                "debate_analysis": (
                    "This appears to be a kanban-style project dashboard with columns for "
                    "To Do, In Progress, Review, and Done. The sidebar shows team members "
                    "and project filters. The main CTA is a blue 'Add Task' button in the "
                    "top right. First-Timer: 5/10 — moderate learning curve. "
                    "Daily Driver: 7/10 — efficient once learned. Buyer: 6/10 — clear value prop. "
                    "Reminds of Trello and Monday.com dashboards."
                ),
                "ux_analysis": (
                    "This screen shows a kanban board view with four columns: To Do, In Progress, "
                    "Review, Done. The left sidebar contains 8 navigation items without grouping. "
                    "A prominent blue 'Add Task' button sits top-right. The board uses drag-and-drop "
                    "cards with assignee avatars and due date labels. Cognitive load: 6/10. "
                    "The layout is clean but the sidebar lacks visual hierarchy, making it hard "
                    "to distinguish primary from secondary navigation. No onboarding tooltips visible."
                ),
            },
            {
                "frame_number": 1,
                "frame_path": "synthetic",
                "debate_analysis": (
                    "This is a reporting dashboard showing client metrics. Bar charts display "
                    "task completion rates over time. A dropdown lets users select different "
                    "clients. Export options include PDF and CSV. First-Timer: 6/10. "
                    "Daily Driver: 8/10 — power feature for agencies. Buyer: 9/10 — key differentiator. "
                    "Reminds of Asana's workload view and Monday.com's reporting module."
                ),
                "ux_analysis": (
                    "The reporting view features a central bar chart with time-series task completion "
                    "data. Client selection is via a dropdown in the top-left. Three tabs separate "
                    "Overview, Detailed, and Export views. The chart lacks data labels and axis "
                    "titles. Export is buried in a secondary dropdown menu rather than a primary CTA. "
                    "Cognitive load: 5/10. Strengths: clean data visualisation, client segmentation. "
                    "Weakness: export discoverability is poor — new users will miss it."
                ),
            },
            {
                "frame_number": 2,
                "frame_path": "synthetic",
                "debate_analysis": (
                    "Settings page showing integrations. Slack, Google Drive, and Zapier tiles "
                    "are visible. Each has a toggle and a 'Configure' link. The page feels sparse "
                    "with lots of whitespace. First-Timer: 8/10 — easy to parse. "
                    "Daily Driver: 6/10 — no bulk actions. Buyer: 7/10 — popular integrations present. "
                    "Reminds of ClickUp and Asana integrations pages."
                ),
                "ux_analysis": (
                    "An integrations settings page with a grid of 6 service tiles (Slack, Google "
                    "Drive, Zapier, Notion, HubSpot, Calendly). Each tile shows a logo, service name, "
                    "toggle switch, and 'Configure' link. Connected integrations are highlighted with "
                    "a green border. Grid has generous whitespace — easy to scan. No search or filter "
                    "for integrations. No indication of plan restrictions. Cognitive load: 3/10. "
                    "Very approachable but scales poorly if more integrations are added."
                ),
            },
        ]
        for fa in frame_analyses:
            _step(f"Synthetic frame {fa['frame_number']}: {fa['debate_analysis'][:80]}...")

    _step(f"Total frames analyzed: {len(frame_analyses)}")

    # ======================================================================
    # STAGE 4: Screenshot suite matching
    # ======================================================================
    print("\n[STAGE 4] Screenshot suite matching")

    from screenshot_suite.matcher import find_similar_screens  # noqa: PLC0415

    # Build in the format synthesize_evidence expects: matched_competitors key
    screenshot_matches: list[dict] = []
    for fa in frame_analyses:
        raw_matches = find_similar_screens(fa["ux_analysis"], top_k=3)
        screenshot_matches.append(
            {
                "frame_number": fa["frame_number"],
                "user_analysis": fa["ux_analysis"],
                "matched_competitors": raw_matches,  # key name matches synthesis.py
            }
        )
        _step(f"Frame {fa['frame_number']} top matches:")
        for match in raw_matches:
            _step(
                f"    {match['app']}/{match['filename']}"
                f" — similarity: {match['similarity_score']:.3f}"
            )

    # ======================================================================
    # STAGE 5: Evidence curation (themed RAG + GPT-4o-mini)
    # ======================================================================
    print("\n[STAGE 5] Evidence curation (themed RAG queries)")

    from screenshot_suite.evidence_curator import curate_evidence  # noqa: PLC0415

    # curated_evidence_by_frame[frame_number] = list of theme dicts from curate_evidence
    curated_evidence_by_frame: dict[int, list[dict]] = {}

    for sm in screenshot_matches:
        frame_num = sm["frame_number"]
        top_match = sm["matched_competitors"][0] if sm["matched_competitors"] else None
        if top_match is None:
            curated_evidence_by_frame[frame_num] = []
            continue

        _step(
            f"Curating evidence for Frame {frame_num} vs "
            f"{top_match['app']}/{top_match['filename']}..."
        )
        themes = curate_evidence(
            user_context=user_context,
            user_frame_analysis=sm["user_analysis"],
            matched_screenshot=top_match,
        )
        curated_evidence_by_frame[frame_num] = themes
        _step(f"  → {len(themes)} themes extracted, "
              f"{sum(len(t.get('supporting_reviews', [])) for t in themes)} supporting reviews")

    _step(
        f"Total curated evidence packages: "
        f"{sum(len(v) for v in curated_evidence_by_frame.values())} themes across "
        f"{len(curated_evidence_by_frame)} frames"
    )

    # ======================================================================
    # STAGE 6: Build comparison cards
    # ======================================================================
    print("\n[STAGE 6] Comparison cards")

    from screenshot_suite.comparison_builder import build_comparison_card  # noqa: PLC0415

    comparison_cards: list[dict] = []
    card_index = 0

    for sm in screenshot_matches:
        frame_num = sm["frame_number"]
        top_match = sm["matched_competitors"][0] if sm["matched_competitors"] else None
        if top_match is None:
            continue

        curated_themes = curated_evidence_by_frame.get(frame_num, [])
        card = build_comparison_card(
            frame_number=frame_num,
            user_analysis=sm["user_analysis"],
            competitor_match=top_match,
            curated_themes=curated_themes,
            user_context=user_context,
            card_index=card_index,
        )
        comparison_cards.append(card)
        card_index += 1

        _step(
            f"Card {card['card_id']}: "
            f"Frame {frame_num} vs {top_match['app']}/{top_match['filename']}"
            f" (sim: {top_match['similarity_score']:.3f})"
        )

    _step(f"Built {len(comparison_cards)} comparison cards")

    # ======================================================================
    # STAGE 7: Synthesize agent brief
    # ======================================================================
    print("\n[STAGE 7] Synthesize agent brief")

    from screenshot_suite.synthesis import synthesize_evidence  # noqa: PLC0415

    # synthesize_evidence reads screenshot_matches with matched_competitors key
    video_evidence_payload = {"screenshot_matches": screenshot_matches}

    synthesis = synthesize_evidence(
        session_id="pipeline_test",
        video_evidence=video_evidence_payload,
        user_context=user_context,
    )

    agent_brief: str = synthesis.get("agent_brief", "")
    _step(f"Agent brief: {len(agent_brief)} chars")
    _step(f"Apps compared: {', '.join(synthesis.get('apps_compared', []))}")
    _step(f"Dominant themes: {synthesis.get('dominant_themes', [])}")

    # Use synthesis cards if available; fall back to manually built ones
    final_cards: list[dict] = synthesis.get("comparison_cards") or comparison_cards

    # ======================================================================
    # STAGE 8: Build EXACT agent prompts
    # ======================================================================
    print("\n[STAGE 8] Building exact agent prompts")
    print("=" * 60)

    # Journey summary — mirroring generate_journey_summary output format
    journey_summary = "\n\n".join(
        f"Frame {fa['frame_number']}: {fa['debate_analysis']}"
        for fa in frame_analyses
    )

    # Shared context block assembled the same way adversarial_debate_engine.py does
    product_section = (
        f"PRODUCT UNDER REVIEW: {user_context['product_name']}\n"
        f"DESCRIPTION: {user_context['productDescription']}\n"
        f"TARGET USER: {user_context['target_user']}\n"
        f"COMPETITORS: {user_context['competitors']}\n"
        f"DIFFERENTIATOR: {user_context['differentiator']}\n"
        f"PRODUCT STAGE: {user_context['product_stage']}\n"
    )

    frame_snippets = "\n\n".join(
        f"--- Frame {fa['frame_number']} ---\n{fa['debate_analysis'][:500]}"
        for fa in frame_analyses[:10]
    )

    video_section = (
        "\nVIDEO EVIDENCE FROM FOUNDER'S PRODUCT WALKTHROUGH:\n"
        "JOURNEY SUMMARY:\n"
        f"{journey_summary[:3000]}\n\n"
        "KEY FRAME ANALYSES (up to 10 frames):\n"
        f"{frame_snippets}\n\n"
        "CRITICAL: The above is PRIMARY evidence from the founder's live walkthrough. "
        "Reference specific frames when making arguments.\n"
    )

    match_section = "\n\nSCREENSHOT COMPARISON EVIDENCE:\n"
    for sm in screenshot_matches[:10]:
        for comp in sm["matched_competitors"][:2]:
            match_section += (
                f"\nUser Frame {sm['frame_number']} matches "
                f"{comp['app']}/{comp['filename']}"
                f" (similarity: {comp['similarity_score']:.2f}):\n"
                f"Competitor analysis: {comp.get('document', 'N/A')[:500]}...\n"
            )

    context_block = product_section + video_section + match_section

    if agent_brief:
        context_block += f"\n\n{agent_brief}"

    tools_section = (
        "\nAVAILABLE TOOLS:\n"
        "1. search_pm_knowledge(query: str) — search full RAG corpus\n"
        "2. search_app_reviews(query: str) — search app store reviews\n"
        "3. search_reddit(query: str) — search Reddit discussions\n"
        "4. search_hn_comments(query: str) — search Hacker News threads\n"
        "5. search_competitor_data(query: str) — search competitor metadata\n"
        "6. search_screenshots(query: str) — search 69-app screenshot analysis suite\n"
    )

    personas: dict[str, dict[str, str]] = {
        "first_timer": {
            "role": "First-Time User Advocate",
            "backstory": (
                f"You are a brand-new user encountering {user_context['product_name']}"
                f" for the very first time.\n"
                f"You represent {user_context['target_user']}.\n"
                "You have ZERO familiarity with the product. You judge based on:\n"
                "- How intuitive is the onboarding?\n"
                "- Can you accomplish a basic task within 5 minutes?\n"
                "- Is the UI self-explanatory or do you need a tutorial?\n"
                "- How does first-run experience compare to competitors?\n\n"
                "You are HARSH on complexity and GENEROUS toward simplicity.\n"
                "You MUST use the search_screenshots tool at least once per round "
                "to find competitor evidence."
            ),
            "task": (
                f"ROUND 1 — OPENING ARGUMENT (First-Timer perspective)\n\n"
                f"{context_block}\n\n"
                f"Deliver your opening argument about {user_context['product_name']} from the "
                "perspective of a first-time user.\n"
                "Focus on: onboarding friction, initial impressions, learnability, and how the "
                "first-run experience compares to competitors.\n"
                "Reference specific frames from the video evidence and screenshot comparisons.\n"
                "Support every claim with evidence from the RAG tools — search for real user "
                "reviews about competitors' onboarding."
                f"\n{tools_section}"
            ),
        },
        "daily_driver": {
            "role": "Power User / Daily Driver",
            "backstory": (
                "You use project management tools 8 hours a day, 5 days a week.\n"
                f"You represent experienced {user_context['target_user']} who will use "
                f"{user_context['product_name']} as their primary tool.\n"
                "You judge based on:\n"
                "- Workflow efficiency — how many clicks for common actions?\n"
                "- Feature depth — can it handle edge cases?\n"
                "- Keyboard shortcuts, bulk actions, integrations\n"
                "- How does daily-use ergonomics compare to competitors?\n\n"
                "You are HARSH on missing power features and GENEROUS toward depth.\n"
                "You MUST use the search_screenshots tool at least once per round "
                "to find competitor evidence."
            ),
            "task": (
                f"ROUND 1 — OPENING ARGUMENT (Daily Driver perspective)\n\n"
                f"{context_block}\n\n"
                f"Deliver your opening argument about {user_context['product_name']} from the "
                "perspective of a daily power user.\n"
                "Focus on: workflow efficiency, feature depth, ergonomics, and how the core "
                "workflows compare to competitors.\n"
                "Reference specific frames from the video evidence and screenshot comparisons.\n"
                "Support every claim with evidence from the RAG tools — search for real user "
                "reviews about competitors' daily-use experience."
                f"\n{tools_section}"
            ),
        },
        "buyer": {
            "role": "Budget-Conscious Buyer / Decision Maker",
            "backstory": (
                "You are the person who signs the check. You evaluate tools for ROI, "
                "pricing, vendor reliability, and team adoption risk.\n"
                f"You represent the decision maker for {user_context['target_user']}.\n"
                "You judge based on:\n"
                "- Pricing vs. value delivered\n"
                "- Team adoption risk — will the team actually use this?\n"
                "- Vendor maturity — is this company stable?\n"
                "- Migration cost from current tools\n"
                "- What competitors offer at the same price point?\n\n"
                "You are HARSH on unclear value props and GENEROUS toward clear ROI.\n"
                "You MUST use the search_screenshots tool at least once per round "
                "to find competitor evidence."
            ),
            "task": (
                f"ROUND 1 — OPENING ARGUMENT (Buyer perspective)\n\n"
                f"{context_block}\n\n"
                f"Deliver your opening argument about {user_context['product_name']} from the "
                "perspective of a budget-conscious buyer/decision maker.\n"
                "Focus on: value proposition clarity, pricing competitiveness, adoption risk, "
                "and how the product compares to what competitors offer at similar price points.\n"
                "Reference specific frames from the video evidence and screenshot comparisons.\n"
                "Support every claim with evidence from the RAG tools — search for real user "
                "reviews about competitors' pricing and ROI."
                f"\n{tools_section}"
            ),
        },
    }

    # ======================================================================
    # SAVE ALL OUTPUT
    # ======================================================================
    output_dir = Path("tests/pipeline_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    for persona_key, persona in personas.items():
        filepath = output_dir / f"agent_{persona_key}_prompt.txt"
        full_prompt = (
            f"ROLE: {persona['role']}\n\n"
            f"BACKSTORY:\n{persona['backstory']}\n\n"
            f"TASK:\n{persona['task']}\n"
        )
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(full_prompt)

        print(f"\n{'=' * 60}")
        print(f"AGENT: {persona['role']}")
        print(f"{'=' * 60}")
        print(f"  Backstory preview: {persona['backstory'][:160]}...")
        print(f"  Task length:       {len(persona['task']):,} chars")
        print(f"  Context block:     {len(context_block):,} chars")
        print(f"  Saved to:          {filepath}")

    # Serialisable frame_analyses (drop frame_path for portability)
    serialisable_analyses = [
        {k: v for k, v in fa.items() if k != "frame_path"} for fa in frame_analyses
    ]
    with open(output_dir / "frame_analyses.json", "w", encoding="utf-8") as fh:
        json.dump(serialisable_analyses, fh, indent=2)

    with open(output_dir / "screenshot_matches.json", "w", encoding="utf-8") as fh:
        json.dump(screenshot_matches, fh, indent=2)

    flat_curated = [
        {"frame_number": fn, "themes": themes}
        for fn, themes in curated_evidence_by_frame.items()
    ]
    with open(output_dir / "curated_evidence.json", "w", encoding="utf-8") as fh:
        json.dump(flat_curated, fh, indent=2, default=str)

    with open(output_dir / "comparison_cards.json", "w", encoding="utf-8") as fh:
        json.dump(final_cards, fh, indent=2, default=str)

    with open(output_dir / "agent_brief.txt", "w", encoding="utf-8") as fh:
        fh.write(agent_brief)

    with open(output_dir / "full_context_block.txt", "w", encoding="utf-8") as fh:
        fh.write(context_block)

    # ======================================================================
    # Final summary
    # ======================================================================
    _banner("PIPELINE COMPLETE")

    total_matches = sum(len(sm["matched_competitors"]) for sm in screenshot_matches)
    total_reviews = sum(
        len(t.get("supporting_reviews", []))
        for themes in curated_evidence_by_frame.values()
        for t in themes
    )

    print(f"\n  Frames analyzed:       {len(frame_analyses)}")
    print(f"  Screenshot matches:    {total_matches}")
    print(f"  Supporting reviews:    {total_reviews}")
    print(f"  Comparison cards:      {len(final_cards)}")
    print(f"  Context block:         {len(context_block):,} chars")

    print(f"\n  Output saved to: {output_dir.resolve()}")
    print(f"\n  Files:")
    for output_path in sorted(output_dir.iterdir()):
        print(f"    {output_path.name:45s} ({output_path.stat().st_size:>8,} bytes)")

    print(
        "\n  Open tests/pipeline_output/agent_*_prompt.txt to see exactly"
        " what each model receives.\n"
    )

    if tmp_dir and Path(tmp_dir).exists():
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    main()
