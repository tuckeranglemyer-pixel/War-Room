# War Room — Frontend

React + TypeScript single-page application that renders the adversarial multi-agent product debate in real time. Built with Vite 8, Tailwind CSS 4, and Framer Motion.

## Architecture

The app is a **view state machine** managed in `App.tsx` with three states:

```
landing  →  debate  →  verdict
   ↑___________↓__________|
```

`App` holds shared state (`product`, `sessionId`, `verdictData`) and passes handler callbacks down. View transitions use Framer Motion's `AnimatePresence` with `fadeScale` variants.

## Components

### `App.tsx`
Root layout and view router. Defines shared TypeScript types (`RoundData`, `VerdictData`) exported for child components. Wraps each view in Framer Motion `motion.div` for enter/exit animations.

### `Landing.tsx`
Hero screen with product input, animated conic-gradient border on focus, and suggestion chips from `preloadedProducts.ts`. Handles its own exit animation before signaling the parent to transition.

### `DebateStream.tsx`
Full debate experience. Contains several inner sub-components:

- **RoundProgress** — Segmented progress bar with spring-animated fill and pulse on the active round.
- **SwarmCard** — Simulates the 20-scout reconnaissance swarm with staggered result streaming.
- **AgentInitSequence** — Three agent cards cycling through initialization states before debate begins.
- **RoundCard** — Renders each round's content with optional typewriter effect (demo mode) and regex-parsed AGREE/DISAGREE badges.

Connects to `ws://localhost:8000/ws/{sessionId}` for live debates. When `sessionId` is empty, falls back to a hardcoded demo script with typewriter animation.

### `VerdictCard.tsx`
Post-debate report card. Includes:

- **ScoreRing** — Animated SVG ring that fills to the verdict score.
- **RoundExpander** — Collapsible per-round details.
- **FeatureEvidenceCard** — Parsed feature topics with sentiment tags and source badges.
- Executive summary, metrics grid, top fixes with impact tiers, and competitive positioning section.

Heavy pure-function parsing logic extracts citations, sentiment, and structured sections from raw round text.

### `ContextForm.tsx`
Six-step wizard for video upload and product context fields. Posts to `POST /api/ingest/video` and `POST /analyze`. Currently **not wired into `App.tsx`** — available for integration when the full ingest flow is enabled.

## Shared Modules

| File | Purpose |
|------|---------|
| `animations.ts` | Framer Motion presets: spring configs (`default`, `gentle`, `snappy`), `fade`, `fadeUp`, `fadeScale` variants |
| `preloadedProducts.ts` | Suggestion chip labels for the landing page |
| `index.css` | Tailwind import + global body reset (dark background, Inter font) |

## Design System

### Colors

| Token | Hex | Usage |
|-------|-----|-------|
| Canvas | `#0A0B0F` | Page background |
| Surface | `#12141A`, `#0D0F14` | Cards, panels |
| Border | `#1E2028`, `#1A1C24` | Dividers, card edges |
| Text primary | `#E4E4E7` | Body copy |
| Text secondary | `#A1A1AA` | Labels, meta |
| Text muted | `#71717A`, `#52525B` | Fine print, timestamps |
| Accent | `#3B82F6` | Links, progress, brand |
| Success | `#22C55E` | Positive scores, AGREE |
| Warning | `#F59E0B` | Buyer role, conditional |
| Danger | `#EF4444` | Low scores, DISAGREE |

### Typography

- **Inter** (400–600) — UI copy, headings, buttons
- **JetBrains Mono** — Labels, metadata, code-style elements, round markers

Both loaded from Google Fonts in `index.html`.

### Styling Approach

Primarily **inline styles** (`style={{ ... }}`) with embedded `<style>` blocks for keyframe animations and scoped class names. Tailwind is configured but utility classes are used sparingly — the design system is enforced by convention through consistent hex values across components.

### Animation

Framer Motion handles all view transitions, entrance staggers, and interactive springs. CSS `@keyframes` are used for continuous effects (`borderRotate`, `dotPulse`, `readyFlash`, `finePrintPulse`).

## Development

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173` with Vite HMR. Expects the FastAPI backend at `http://localhost:8000` for live debate mode; works standalone in demo fallback mode.

## Build

```bash
npm run build
```

Output goes to `dist/` — static assets deployable to Vercel or any CDN.
