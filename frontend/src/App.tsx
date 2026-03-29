import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Landing from './components/Landing'
import ContextForm from './components/ContextForm'
import DebateStream from './components/DebateStream'
import VerdictCard from './components/VerdictCard'
import { fadeScale, spring } from './animations'
import './index.css'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'https://paplike-hillary-beauteously.ngrok-free.dev'

type View = 'landing' | 'context' | 'starting' | 'debate' | 'verdict'

export interface RoundData {
  round: number
  agent_name: string
  agent_role: string
  content: string
}

export interface VerdictData {
  score: number
  decision: string
  top_3_fixes: string[]
  rounds: RoundData[]
  full_report: string
}

/**
 * Root application component managing top-level view state and navigation.
 *
 * Coordinates views — landing → debate → verdict — and passes
 * shared state (product name, session ID, verdict data) down to each view
 * component. All view transitions are animated via Framer Motion AnimatePresence.
 */
export default function App() {
  const [view, setView] = useState<View>('landing')
  const [product, setProduct] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [verdictData, setVerdictData] = useState<VerdictData | null>(null)

  /**
   * Freeform input path: advance to the context wizard to collect product
   * metadata (description, target user, competitors, etc.) before launching.
   * @param name - Product name typed by the user.
   */
  function handleSelectProduct(name: string) {
    setProduct(name)
    setVerdictData(null)
    setSessionId('')
    setView('context')
  }

  /**
   * Featured product path: skip the wizard entirely.
   * POST /analyze with just the product name, then jump straight to the
   * debate stream the moment the backend returns a session_id.
   * @param name - Product name from a featured pill click.
   */
  async function handleFeaturedProduct(name: string) {
    setProduct(name)
    setVerdictData(null)
    setSessionId('')
    setView('starting')
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_name: name }),
      })
      if (!res.ok) throw new Error(`Analyze error ${res.status}`)
      const { session_id } = await res.json()
      setSessionId(session_id)
      setView('debate')
    } catch {
      setView('landing')
    }
  }

  /**
   * Called by ContextForm when the backend returns a session_id.
   * Advances to the live debate stream with the real WebSocket session.
   * @param sid - WebSocket session ID from POST /analyze.
   */
  function handleContextComplete(sid: string) {
    setSessionId(sid)
    setView('debate')
  }

  function handleViewReport() {
    const id = sessionId || 'demo'
    window.location.href = `/report/${id}`
  }

  /**
   * Advance from the debate stream to the verdict summary view.
   * @param data - Structured verdict payload received from the backend.
   */
  function handleVerdict(data: VerdictData) {
    setVerdictData(data)
    setView('verdict')
  }

  /**
   * Reset all state and return to the landing view for a new analysis.
   */
  function handleBack() {
    setView('landing')
    setProduct('')
    setSessionId('')
    setVerdictData(null)
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0A0B0F' }}>
      <AnimatePresence mode="wait">
        {view === 'landing' && (
          <motion.div
            key="landing"
            initial={fadeScale.initial}
            animate={fadeScale.animate}
            exit={fadeScale.exit}
            transition={spring.gentle}
            style={{ minHeight: '100vh' }}
          >
            <Landing
              onSelectProduct={handleSelectProduct}
              onFeaturedProduct={(name) => { void handleFeaturedProduct(name) }}
            />
          </motion.div>
        )}
        {view === 'context' && (
          <motion.div
            key="context"
            initial={fadeScale.initial}
            animate={fadeScale.animate}
            exit={fadeScale.exit}
            transition={spring.gentle}
            style={{ minHeight: '100vh' }}
          >
            <ContextForm
              productName={product}
              onComplete={handleContextComplete}
              onBack={handleBack}
            />
          </motion.div>
        )}
        {view === 'starting' && (
          <motion.div
            key="starting"
            initial={fadeScale.initial}
            animate={fadeScale.animate}
            exit={fadeScale.exit}
            transition={spring.gentle}
            style={{
              minHeight: '100vh',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <p style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 14,
              color: '#3B82F6',
              letterSpacing: '0.02em',
            }}>
              Starting War Room...
            </p>
          </motion.div>
        )}
        {view === 'debate' && (
          <motion.div
            key="debate"
            initial={fadeScale.initial}
            animate={fadeScale.animate}
            exit={fadeScale.exit}
            transition={spring.gentle}
            style={{ minHeight: '100vh' }}
          >
            <DebateStream
              product={product}
              sessionId={sessionId}
              onBack={handleBack}
              onVerdict={handleVerdict}
            />
          </motion.div>
        )}
        {view === 'verdict' && (
          <motion.div
            key="verdict"
            initial={fadeScale.initial}
            animate={fadeScale.animate}
            exit={fadeScale.exit}
            transition={spring.gentle}
            style={{ minHeight: '100vh' }}
          >
            <VerdictCard
              product={product}
              score={verdictData?.score ?? 0}
              decision={verdictData?.decision ?? 'UNKNOWN'}
              fixes={verdictData?.top_3_fixes ?? []}
              rounds={verdictData?.rounds ?? []}
              full_report={verdictData?.full_report ?? ''}
              onBack={handleBack}
            />
            <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 100 }}>
              <button
                onClick={handleViewReport}
                style={{
                  background: 'rgba(15,15,22,0.95)',
                  border: '1px solid rgba(255,255,255,0.12)',
                  borderRadius: 8,
                  padding: '10px 20px',
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 13,
                  fontWeight: 500,
                  color: '#f0f0f5',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  backdropFilter: 'blur(12px)',
                  transition: 'border-color 0.15s ease',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.25)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)' }}
              >
                <span style={{ fontSize: 14 }}>📄</span>
                View Full Report
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
