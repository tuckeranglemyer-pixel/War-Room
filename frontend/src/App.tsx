import { useState } from 'react'
import Landing from './components/Landing'
import ContextForm from './components/ContextForm'
import DebateStream from './components/DebateStream'
import VerdictCard from './components/VerdictCard'
import './index.css'

type View = 'landing' | 'context' | 'debate' | 'verdict'

export interface VerdictData {
  score: number
  decision: string
  top_3_fixes: string[]
}

export default function App() {
  const [view, setView] = useState<View>('landing')
  const [product, setProduct] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [verdictData, setVerdictData] = useState<VerdictData | null>(null)

  function handleSelectProduct(name: string) {
    setProduct(name)
    setVerdictData(null)
    setView('context')
  }

  function handleContextComplete(sid: string) {
    setSessionId(sid)
    setView('debate')
  }

  function handleVerdict(data: VerdictData) {
    setVerdictData(data)
    setView('verdict')
  }

  function handleBack() {
    setView('landing')
    setProduct('')
    setSessionId('')
    setVerdictData(null)
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0A0B0F' }}>
      {view === 'landing' && (
        <Landing onSelectProduct={handleSelectProduct} />
      )}
      {view === 'context' && (
        <ContextForm
          productName={product}
          onComplete={handleContextComplete}
          onBack={handleBack}
        />
      )}
      {view === 'debate' && (
        <DebateStream
          product={product}
          sessionId={sessionId}
          onBack={handleBack}
          onVerdict={handleVerdict}
        />
      )}
      {view === 'verdict' && (
        <VerdictCard
          product={product}
          score={verdictData?.score ?? 0}
          decision={verdictData?.decision ?? 'UNKNOWN'}
          fixes={verdictData?.top_3_fixes ?? []}
          onBack={handleBack}
        />
      )}
    </div>
  )
}
