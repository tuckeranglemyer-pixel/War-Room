import { useState, useEffect, useRef, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { fadeUp, spring } from '../animations'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'https://paplike-hillary-beauteously.ngrok-free.dev'

// ── Stage simulation data ───────────────────────────────────────────────────

const FRAME_LABELS = [
  'Dashboard view detected',
  'Navigation menu captured',
  'Settings panel visible',
  'Onboarding flow — step 2',
  'Empty state screen',
  'Data table interaction',
  'Modal dialog captured',
  'Search results view',
  'Profile settings',
  'Mobile layout detected',
]

interface VisionResult {
  frame: number
  friction: number
  strengths: number
}

const VISION_RESULTS: VisionResult[] = [
  { frame: 1, friction: 3, strengths: 2 },
  { frame: 2, friction: 1, strengths: 4 },
  { frame: 3, friction: 2, strengths: 1 },
  { frame: 4, friction: 4, strengths: 2 },
  { frame: 5, friction: 0, strengths: 3 },
  { frame: 6, friction: 2, strengths: 2 },
  { frame: 7, friction: 3, strengths: 1 },
  { frame: 8, friction: 1, strengths: 3 },
  { frame: 9, friction: 2, strengths: 2 },
  { frame: 10, friction: 1, strengths: 4 },
]

interface CompetitorMatch {
  frame: number
  name: string
  score: number
}

const COMPETITOR_MATCHES: CompetitorMatch[] = [
  { frame: 1,  name: 'Notion',     score: 0.82 },
  { frame: 2,  name: 'ClickUp',    score: 0.71 },
  { frame: 3,  name: 'Asana',      score: 0.68 },
  { frame: 4,  name: 'Linear',     score: 0.79 },
  { frame: 5,  name: 'Monday',     score: 0.65 },
  { frame: 6,  name: 'Jira',       score: 0.74 },
  { frame: 7,  name: 'Basecamp',   score: 0.61 },
  { frame: 8,  name: 'Airtable',   score: 0.77 },
  { frame: 9,  name: 'Trello',     score: 0.58 },
  { frame: 10, name: 'Notion',     score: 0.83 },
]

interface EvidenceTopic {
  topic: string
  count: number
}

const EVIDENCE_TOPICS: EvidenceTopic[] = [
  { topic: 'Dashboard patterns',    count: 15 },
  { topic: 'Navigation friction',   count: 12 },
  { topic: 'Onboarding drop-off',   count: 23 },
  { topic: 'Mobile usability',      count: 18 },
  { topic: 'Search reliability',    count: 9  },
  { topic: 'Export limitations',    count: 7  },
]

const CLOUD_SPECIALISTS = [
  { key: 'strategist',        role: 'STRATEGIST',        model: 'GPT-4o',           dotColor: '#3B82F6' },
  { key: 'ux_analyst',        role: 'UX ANALYST',        model: 'GPT-4o',           dotColor: '#E4E4E7' },
  { key: 'market_researcher', role: 'MARKET RESEARCHER', model: 'GPT-4o',           dotColor: '#F59E0B' },
]
const DGX_SPECIALISTS = [
  { key: 'strategist',        role: 'STRATEGIST',        model: 'Llama 3.3-70B',    dotColor: '#3B82F6' },
  { key: 'ux_analyst',        role: 'UX ANALYST',        model: 'Qwen3-32B',        dotColor: '#E4E4E7' },
  { key: 'market_researcher', role: 'MARKET RESEARCHER', model: 'Mistral-Small-24B',dotColor: '#F59E0B' },
]

const TOTAL_REVIEWS = 31_668

// ── Shared sub-components ───────────────────────────────────────────────────

function StageHeader({ label }: { label: string }) {
  return (
    <p style={{
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 11,
      fontWeight: 500,
      letterSpacing: '0.15em',
      color: '#71717A',
      textTransform: 'uppercase',
      marginBottom: 12,
    }}>
      {label}
    </p>
  )
}

function FeedLine({ text, color = '#71717A' }: { text: string; color?: string }) {
  return (
    <motion.p
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={spring.gentle}
      style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
        color,
        lineHeight: 1.6,
        margin: 0,
      }}
    >
      {text}
    </motion.p>
  )
}

function StageCard({
  header,
  flash = false,
  children,
}: {
  header: string
  flash?: boolean
  children: React.ReactNode
}) {
  return (
    <motion.div
      initial={fadeUp.initial}
      animate={fadeUp.animate}
      transition={spring.gentle}
      style={{
        background: '#12141A',
        border: `1px solid ${flash ? '#3B82F6' : '#1E2028'}`,
        borderRadius: 8,
        padding: 20,
        transition: 'border-color 300ms ease',
      }}
    >
      <StageHeader label={header} />
      {children}
    </motion.div>
  )
}

/**
 * Monospace terminal showing live log lines for one analyst.
 * Auto-scrolls to the bottom as new lines arrive.
 */
function LogTerminal({ lines }: { lines: string[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])
  return (
    <div style={{
      marginTop: 10,
      background: '#080A0F',
      border: '1px solid #1A1C22',
      borderRadius: 4,
      padding: '8px 10px',
      maxHeight: 80,
      overflowY: 'auto',
      display: 'flex',
      flexDirection: 'column',
      gap: 2,
    }}>
      {lines.map((line, i) => (
        <span key={i} style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          color: line.startsWith('Error') || line.startsWith('FAILED') ? '#EF4444' : '#4ADE80',
          lineHeight: 1.5,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
        }}>
          {'> '}{line}
        </span>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

/**
 * Six-segment progress bar showing which pipeline stage is active.
 */
function PipelineProgress({ stage, total }: { stage: number; total: number }) {
  return (
    <div style={{ display: 'flex', gap: 4, marginBottom: 24 }}>
      {Array.from({ length: total }).map((_, i) => {
        const filled = i < stage
        const active = i === stage
        return (
          <div
            key={i}
            style={{ flex: 1, height: 3, borderRadius: 2, background: '#1E2028', overflow: 'hidden' }}
          >
            <motion.div
              style={{ height: 3, borderRadius: 2, background: '#3B82F6', transformOrigin: 'left center' }}
              initial={{ scaleX: 0 }}
              animate={{
                scaleX: filled ? 1 : active ? 0.55 : 0,
                opacity: active ? [1, 0.45, 1] : 1,
              }}
              transition={{
                scaleX: spring.snappy,
                opacity: active
                  ? { repeat: Infinity, duration: 2, times: [0, 0.5, 1] }
                  : { duration: 0.15 },
              }}
            />
          </div>
        )
      })}
    </div>
  )
}

// ── Main component ──────────────────────────────────────────────────────────

export interface AnalysisPipelineProps {
  /** Product name shown in header. */
  product: string
  /** Session ID from POST /api/ingest/video — empty string until ingest returns. */
  sessionId: string
  /** True once POST /api/analyze returns successfully. */
  analysisComplete: boolean
  /** Error message from the backend — shows an error state when non-empty. */
  error?: string
  /** Current execution mode — controls which model names are shown on specialist cards. */
  execMode?: 'cloud' | 'dgx'
  onBack: () => void
  /** Called with the session ID when the pipeline completes — navigate to report view. */
  onReportReady?: (sessionId: string) => void
}

/**
 * Six-stage animated processing view shown while the backend analyzes a video.
 *
 * Stages run sequentially on simulated timers and hold at Stage 5 (specialist
 * analysis) until ``analysisComplete`` is set, at which point the final assembly
 * stage runs and auto-navigates to ``/report/{sessionId}``.
 *
 * If ``error`` is provided the component renders an error state rather than
 * advancing through the pipeline.
 */
export default function AnalysisPipeline({
  product,
  sessionId,
  analysisComplete,
  error = '',
  execMode = 'cloud',
  onBack,
  onReportReady,
}: AnalysisPipelineProps) {
  const SPECIALISTS = execMode === 'dgx' ? DGX_SPECIALISTS : CLOUD_SPECIALISTS
  // 0=frames 1=vision 2=matching 3=evidence 4=specialists 5=assembly
  const [stageIndex, setStageIndex] = useState(0)
  const [flashStage, setFlashStage] = useState<number | null>(null)

  // Stage 1: frame extraction
  const [framesCaptured, setFramesCaptured] = useState(0)
  const [frameLines, setFrameLines] = useState<string[]>([])

  // Stage 2: vision analysis
  const [visionActive, setVisionActive] = useState(0)
  const [visionResults, setVisionResults] = useState<VisionResult[]>([])

  // Stage 3: competitor matching
  const [matchResults, setMatchResults] = useState<CompetitorMatch[]>([])

  // Stage 4: evidence curation
  const [reviewsSearched, setReviewsSearched] = useState(0)
  const [evidenceLines, setEvidenceLines] = useState<EvidenceTopic[]>([])

  // Stage 5: specialist deployment
  const [visibleSpecialists, setVisibleSpecialists] = useState(0)
  const [specialistStatuses, setSpecialistStatuses] = useState<string[]>(['', '', ''])
  const [specialistInitDone, setSpecialistInitDone] = useState(false)
  const [showPartnerReview, setShowPartnerReview] = useState(false)

  // Stage 6: assembly
  const [showDeliverable, setShowDeliverable] = useState(false)

  // Live SSE logs per analyst key
  const [specialistLogs, setSpecialistLogs] = useState<Record<string, string[]>>({
    strategist: [], ux_analyst: [], market_researcher: [], partner: [], system: [],
  })

  const analysisCompleteRef = useRef(analysisComplete)
  const sessionIdRef = useRef(sessionId)

  useEffect(() => { analysisCompleteRef.current = analysisComplete }, [analysisComplete])
  useEffect(() => { sessionIdRef.current = sessionId }, [sessionId])

  // Subscribe to SSE log stream once we have a sessionId
  const pushLog = useCallback((analyst: string, message: string) => {
    setSpecialistLogs(prev => ({
      ...prev,
      [analyst]: [...(prev[analyst] ?? []), message],
    }))
  }, [])

  useEffect(() => {
    if (!sessionId) return
    const es = new EventSource(`${API_BASE}/api/stream/logs/${sessionId}`)
    es.onmessage = (e) => {
      try {
        const { analyst, message } = JSON.parse(e.data) as { analyst: string; message: string }
        pushLog(analyst, message)
      } catch {/* ignore malformed frames */}
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [sessionId, pushLog])

  /** Flash the card border then advance to the next stage. */
  function flashAndAdvance(from: number) {
    setFlashStage(from)
    setTimeout(() => {
      setFlashStage(null)
      setStageIndex(from + 1)
    }, 500)
  }

  // ── Stage 1: Extracting Frames ────────────────────────────────────────────
  useEffect(() => {
    if (stageIndex !== 0) return
    const FRAME_COUNT = 10
    let i = 0
    const interval = setInterval(() => {
      if (i < FRAME_COUNT) {
        const label = FRAME_LABELS[i] ?? `Frame ${i + 1} captured`
        setFramesCaptured(i + 1)
        setFrameLines(prev => [...prev, `✓ Frame ${i + 1} — ${label}`])
        i++
      } else {
        clearInterval(interval)
        setTimeout(() => flashAndAdvance(0), 400)
      }
    }, 1200)
    return () => clearInterval(interval)
  }, [stageIndex])

  // ── Stage 2: Vision Analysis ──────────────────────────────────────────────
  useEffect(() => {
    if (stageIndex !== 1) return
    let i = 0
    const interval = setInterval(() => {
      if (i < VISION_RESULTS.length) {
        setVisionActive(i + 1)
        const result = VISION_RESULTS[i]
        if (result) setVisionResults(prev => [...prev, result])
        i++
      } else {
        clearInterval(interval)
        setTimeout(() => flashAndAdvance(1), 400)
      }
    }, 1500)
    return () => clearInterval(interval)
  }, [stageIndex])

  // ── Stage 3: Screenshot Matching ──────────────────────────────────────────
  useEffect(() => {
    if (stageIndex !== 2) return
    let i = 0
    const interval = setInterval(() => {
      if (i < COMPETITOR_MATCHES.length) {
        const match = COMPETITOR_MATCHES[i]
        if (match) setMatchResults(prev => [...prev, match])
        i++
      } else {
        clearInterval(interval)
        setTimeout(() => flashAndAdvance(2), 400)
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [stageIndex])

  // ── Stage 4: Evidence Curation ────────────────────────────────────────────
  useEffect(() => {
    if (stageIndex !== 3) return

    // Animate the review counter 0 → TOTAL_REVIEWS over 8 s
    const STEPS = 80
    const INCREMENT = TOTAL_REVIEWS / STEPS
    let step = 0
    const counterInterval = setInterval(() => {
      step++
      setReviewsSearched(Math.min(Math.round(INCREMENT * step), TOTAL_REVIEWS))
      if (step >= STEPS) clearInterval(counterInterval)
    }, 8000 / STEPS)

    // Show topic lines at 2 s each
    let i = 0
    const lineInterval = setInterval(() => {
      if (i < EVIDENCE_TOPICS.length) {
        const topic = EVIDENCE_TOPICS[i]
        if (topic) setEvidenceLines(prev => [...prev, topic])
        i++
      } else {
        clearInterval(lineInterval)
        clearInterval(counterInterval)
        setReviewsSearched(TOTAL_REVIEWS)
        setTimeout(() => flashAndAdvance(3), 400)
      }
    }, 2000)

    return () => {
      clearInterval(counterInterval)
      clearInterval(lineInterval)
    }
  }, [stageIndex])

  // ── Stage 5: Specialist Deployment ───────────────────────────────────────
  useEffect(() => {
    if (stageIndex !== 4) return
    const timers: ReturnType<typeof setTimeout>[] = []

    for (let i = 0; i < 3; i++) {
      const base = i * 800
      timers.push(setTimeout(() => setVisibleSpecialists(v => Math.max(v, i + 1)), base))
      timers.push(setTimeout(() => {
        setSpecialistStatuses(prev => { const n = [...prev]; n[i] = 'initializing'; return n })
      }, base))
      timers.push(setTimeout(() => {
        setSpecialistStatuses(prev => { const n = [...prev]; n[i] = 'analyzing'; return n })
      }, base + 2000))
    }

    // After all 3 are "analyzing", show the partner review hold line
    const holdDelay = 3 * 800 + 2000 + 500
    timers.push(setTimeout(() => {
      setShowPartnerReview(true)
      setSpecialistInitDone(true)
    }, holdDelay))

    return () => timers.forEach(clearTimeout)
  }, [stageIndex])

  // ── Wait for backend, then finish Stage 5 → Stage 6 ─────────────────────
  useEffect(() => {
    if (!specialistInitDone || !analysisComplete) return
    setSpecialistStatuses(['complete', 'complete', 'complete'])
    const t = setTimeout(() => setStageIndex(5), 1500)
    return () => clearTimeout(t)
  }, [specialistInitDone, analysisComplete])

  // ── Stage 6: Assembly ─────────────────────────────────────────────────────
  useEffect(() => {
    if (stageIndex !== 5) return
    const t1 = setTimeout(() => setShowDeliverable(true), 1800)
    const t2 = setTimeout(() => {
      const sid = sessionIdRef.current
      if (sid) {
        if (onReportReady) {
          onReportReady(sid)
        } else {
          window.location.href = `/report/${sid}`
        }
      }
    }, 3200)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [stageIndex, onReportReady])

  const TOTAL_STAGES = 6
  const displayStage = Math.min(stageIndex + 1, TOTAL_STAGES)

  return (
    <div style={{ minHeight: '100vh', background: '#0A0B0F' }}>
      <style>{`
        @keyframes dotPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        @keyframes readyFlash {
          0%   { opacity: 0; filter: brightness(2); }
          50%  { opacity: 1; filter: brightness(1.5); }
          100% { opacity: 1; filter: brightness(1); }
        }
      `}</style>

      <div style={{ maxWidth: 880, margin: '0 auto', padding: '32px 24px 64px' }}>

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div style={{
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', marginBottom: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              type="button"
              aria-label="Back"
              onClick={onBack}
              style={{
                width: 32, height: 32, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: '#71717A',
                fontFamily: "'Inter', sans-serif", fontSize: 18,
                transition: 'color 150ms ease',
                background: 'none', border: 'none', padding: 0,
              }}
              onMouseEnter={e => { e.currentTarget.style.color = '#E4E4E7' }}
              onMouseLeave={e => { e.currentTarget.style.color = '#71717A' }}
            >
              ←
            </button>
            <span style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 16, fontWeight: 600, color: '#E4E4E7',
            }}>
              {product}
            </span>
          </div>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11, color: '#71717A',
          }}>
            {error ? 'ERROR' : `STAGE ${displayStage} OF ${TOTAL_STAGES}`}
          </span>
        </div>

        <PipelineProgress stage={stageIndex} total={TOTAL_STAGES} />

        {/* ── Error state ────────────────────────────────────────────────── */}
        {error ? (
          <motion.div
            initial={fadeUp.initial}
            animate={fadeUp.animate}
            transition={spring.gentle}
            style={{
              background: '#12141A',
              border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 8,
              padding: 20,
              textAlign: 'center',
            }}
          >
            <p style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12, color: '#EF4444', marginBottom: 20,
            }}>
              {error}
            </p>
            <button
              onClick={onBack}
              style={{
                background: 'transparent', border: 'none',
                fontFamily: "'Inter', sans-serif", fontSize: 13,
                color: '#52525B', cursor: 'pointer',
                transition: 'color 150ms ease',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = '#E4E4E7' }}
              onMouseLeave={e => { e.currentTarget.style.color = '#52525B' }}
            >
              ← Try again
            </button>
          </motion.div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

            {/* ── Stage 1: Extracting Frames ────────────────────────────── */}
            <StageCard header="EXTRACTING FRAMES" flash={flashStage === 0}>
              <p style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 14, color: '#E4E4E7', marginBottom: 12,
              }}>
                {framesCaptured} / 10 frames captured
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {frameLines.map((line, i) => <FeedLine key={i} text={line} />)}
              </div>
            </StageCard>

            {/* ── Stage 2: Vision Analysis ──────────────────────────────── */}
            {stageIndex >= 1 && (
              <StageCard header="ANALYZING SCREENS" flash={flashStage === 1}>
                <AnimatePresence mode="wait">
                  {stageIndex === 1 && (
                    <motion.p
                      key={`scan-${visionActive}`}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 13, color: '#3B82F6',
                        marginBottom: 12,
                        display: 'flex', alignItems: 'center', gap: 8,
                      }}
                    >
                      <span style={{
                        width: 6, height: 6, borderRadius: '50%',
                        background: '#3B82F6', display: 'inline-block',
                        animation: 'dotPulse 1s ease-in-out infinite',
                        flexShrink: 0,
                      }} />
                      GPT-4o Vision scanning frame {visionActive}...
                    </motion.p>
                  )}
                </AnimatePresence>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {visionResults.map(r => (
                    <FeedLine
                      key={r.frame}
                      text={`✓ Frame ${r.frame} — ${r.friction} friction point${r.friction !== 1 ? 's' : ''}, ${r.strengths} strength${r.strengths !== 1 ? 's' : ''} identified`}
                    />
                  ))}
                </div>
              </StageCard>
            )}

            {/* ── Stage 3: Screenshot Matching ──────────────────────────── */}
            {stageIndex >= 2 && (
              <StageCard header="MATCHING COMPETITORS" flash={flashStage === 2}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {matchResults.map(m => (
                    <FeedLine
                      key={m.frame}
                      text={`✓ Frame ${m.frame} matched → ${m.name} (${m.score.toFixed(2)} similarity)`}
                    />
                  ))}
                </div>
              </StageCard>
            )}

            {/* ── Stage 4: Evidence Curation ────────────────────────────── */}
            {stageIndex >= 3 && (
              <StageCard header="CURATING EVIDENCE" flash={flashStage === 3}>
                <p style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 13,
                  color: stageIndex === 3 ? '#3B82F6' : '#52525B',
                  marginBottom: 12,
                  transition: 'color 300ms ease',
                }}>
                  Searching {reviewsSearched.toLocaleString()} reviews...
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {evidenceLines.map((e, i) => (
                    <FeedLine key={i} text={`✓ ${e.count} reviews found for ${e.topic}`} />
                  ))}
                </div>
              </StageCard>
            )}

            {/* ── Stage 5: Specialist Deployment ───────────────────────── */}
            {stageIndex >= 4 && (
              <motion.div
                initial={fadeUp.initial}
                animate={fadeUp.animate}
                transition={spring.gentle}
                style={{
                  background: '#12141A',
                  border: '1px solid #1E2028',
                  borderRadius: 8,
                  padding: 20,
                }}
              >
                <StageHeader label="DEPLOYING SPECIALISTS" />

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
                  {SPECIALISTS.map((spec, i) =>
                    visibleSpecialists > i ? (
                      <motion.div
                        key={i}
                        initial={fadeUp.initial}
                        animate={fadeUp.animate}
                        transition={spring.gentle}
                        style={{
                          background: '#0E1016',
                          border: '1px solid #1E2028',
                          borderRadius: 6, padding: '12px 16px',
                        }}
                      >
                        {/* Header row */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                          <div style={{
                            width: 8, height: 8, borderRadius: '50%',
                            background: spec.dotColor,
                            flexShrink: 0,
                            animation: specialistStatuses[i] !== 'complete'
                              ? 'dotPulse 1.5s ease-in-out infinite'
                              : undefined,
                          }} />
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                            <span style={{
                              fontFamily: "'JetBrains Mono', monospace",
                              fontSize: 10, color: '#71717A',
                              letterSpacing: '0.15em', textTransform: 'uppercase',
                            }}>
                              {spec.role}
                            </span>
                            <span style={{
                              fontFamily: "'Inter', sans-serif",
                              fontSize: 13, fontWeight: 600, color: '#E4E4E7',
                            }}>
                              {spec.model}
                            </span>
                          </div>
                          <span style={{
                            marginLeft: 'auto', flexShrink: 0,
                            minHeight: 14, display: 'flex',
                            alignItems: 'center', justifyContent: 'flex-end',
                          }}>
                            <AnimatePresence mode="wait">
                              {specialistStatuses[i] ? (
                                <motion.span
                                  key={specialistStatuses[i]}
                                  initial={{ opacity: 0, y: 8 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  exit={{ opacity: 0, y: -4 }}
                                  transition={spring.gentle}
                                  style={{
                                    fontFamily: "'JetBrains Mono', monospace",
                                    fontSize: 10,
                                    color: specialistStatuses[i] === 'complete'
                                      ? '#22C55E'
                                      : specialistStatuses[i] === 'analyzing'
                                      ? '#3B82F6'
                                      : '#3F3F46',
                                    animation: specialistStatuses[i] === 'complete'
                                      ? 'readyFlash 300ms ease'
                                      : undefined,
                                  }}
                                >
                                  {specialistStatuses[i]}
                                </motion.span>
                              ) : null}
                            </AnimatePresence>
                          </span>
                        </div>
                        {/* Live log terminal */}
                        {(specialistLogs[spec.key]?.length ?? 0) > 0 && (
                          <LogTerminal lines={specialistLogs[spec.key] ?? []} />
                        )}
                      </motion.div>
                    ) : null
                  )}
                </div>

                {showPartnerReview && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={spring.gentle}
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11, color: '#71717A',
                      letterSpacing: '0.08em',
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}
                  >
                    <span style={{
                      width: 5, height: 5, borderRadius: '50%',
                      background: '#71717A', display: 'inline-block',
                      animation: specialistStatuses[0] !== 'complete'
                        ? 'dotPulse 1.5s ease-in-out infinite'
                        : undefined,
                      flexShrink: 0,
                    }} />
                    PARTNER REVIEW — cross-validating findings...
                  </motion.p>
                )}
              </motion.div>
            )}

            {/* ── Stage 6: Assembly ─────────────────────────────────────── */}
            {stageIndex >= 5 && (
              <StageCard header="ASSEMBLING REPORT">
                <AnimatePresence>
                  {showDeliverable && (
                    <FeedLine text="✓ Deliverable ready" color="#22C55E" />
                  )}
                </AnimatePresence>
              </StageCard>
            )}

          </div>
        )}
      </div>
    </div>
  )
}
