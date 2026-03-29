import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Landing from './components/Landing'
import ContextForm from './components/ContextForm'
import DebateStream from './components/DebateStream'
import VerdictCard from './components/VerdictCard'
import Report from './components/Report'
import { fadeScale, spring } from './animations'
import './index.css'

import { STATIC_DEMO_REPORT_SESSION_ID } from './config'

type View = 'landing' | 'context' | 'debate' | 'verdict' | 'report'

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
  const [reportSessionId, setReportSessionId] = useState<string | null>(null)

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
   * Featured product path: client-only scripted debate in DebateStream (empty sessionId
   * → no WebSocket, no backend). Works on static Vercel deploys with zero API.
   * @param name - Product name from a featured pill click (shown in header; rounds use bundled Notion demo script).
   */
  function handleFeaturedProduct(name: string) {
    setProduct(name)
    setVerdictData(null)
    setSessionId('')
    setView('debate')
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
    const id = sessionId.trim() ? sessionId : STATIC_DEMO_REPORT_SESSION_ID
    setReportSessionId(id)
    setView('report')
  }

  function handleReportReady(sid: string) {
    setReportSessionId(sid)
    setView('report')
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
    setReportSessionId(null)
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
              onFeaturedProduct={handleFeaturedProduct}
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
              onReportReady={handleReportReady}
            />
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
        {view === 'report' && reportSessionId && (
          <motion.div
            key="report"
            initial={fadeScale.initial}
            animate={fadeScale.animate}
            exit={fadeScale.exit}
            transition={spring.gentle}
            style={{ minHeight: '100vh' }}
          >
            <Report sessionId={reportSessionId} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
