import { useState } from 'react'
import Landing from './components/Landing'
import DebateStream from './components/DebateStream'
import VerdictCard from './components/VerdictCard'
import './index.css'

type View = 'landing' | 'debate' | 'verdict'

export default function App() {
  const [view, setView] = useState<View>('landing')
  const [product, setProduct] = useState('')

  return (
    <div style={{ minHeight: '100vh', background: '#0A0B0F' }}>
      {view === 'landing' && (
        <Landing onSelectProduct={(name) => { setProduct(name); setView('debate') }} />
      )}
      {view === 'debate' && (
        <DebateStream product={product} onBack={() => { setView('landing'); setProduct('') }} />
      )}
      {view === 'verdict' && (
        <VerdictCard product={product} onBack={() => { setView('landing'); setProduct('') }} />
      )}
    </div>
  )
}
