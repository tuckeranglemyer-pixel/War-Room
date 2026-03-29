import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Landing from './components/Landing'
import DebateStream from './components/DebateStream'
import VerdictCard from './components/VerdictCard'
import { fadeScale, spring } from './animations'
import './index.css'

type View = 'landing' | 'debate' | 'verdict'

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
   * From the landing view: go straight to the debate stream in demo mode.
   * Empty sessionId signals DebateStream to skip the backend WebSocket and run
   * the scripted demo (Vercel and external visitors have no API).
   * @param name - Product name from the input or a suggestion chip.
   */
  function handleSelectProduct(name: string) {
    setProduct(name)
    setVerdictData(null)
    setSessionId('')
    setView('debate')
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
            <Landing onSelectProduct={handleSelectProduct} />
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
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
