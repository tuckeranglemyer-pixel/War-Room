import { useState } from 'react'
import GlassShard from './components/GlassShard'
import Landing from './components/Landing'
import DebateStream from './components/DebateStream'
import VerdictCard from './components/VerdictCard'
import './index.css'

type View = 'landing' | 'debate' | 'verdict'

export default function App() {
  const [view, setView] = useState<View>('landing')
  const [product, setProduct] = useState('')

  function handleSelectProduct(name: string) {
    setProduct(name)
    setView('debate')
  }

  function handleBack() {
    setView('landing')
    setProduct('')
  }

  return (
    <>
      <GlassShard />
      {view === 'landing' && <Landing onSelectProduct={handleSelectProduct} />}
      {view === 'debate' && <DebateStream product={product} onBack={handleBack} />}
      {view === 'verdict' && <VerdictCard onBack={handleBack} />}
    </>
  )
}
