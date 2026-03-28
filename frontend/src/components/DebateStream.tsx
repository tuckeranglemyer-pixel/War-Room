import { useState, useEffect, useRef, useCallback } from 'react'
import type { VerdictData } from '../App'

interface DebateStreamProps {
  product: string
  sessionId: string
  onBack: () => void
  onVerdict: (data: VerdictData) => void
}

// Simulated scout topics shown during the server-side swarm wait
const SCOUT_RESULTS = [
  { topic: 'Onboarding friction', count: 14 },
  { topic: 'Pricing complaints', count: 8 },
  { topic: 'Mobile app stability', count: 22 },
  { topic: 'Integration gaps', count: 11 },
  { topic: 'Performance under load', count: 6 },
  { topic: 'Collaboration UX', count: 17 },
  { topic: 'Search functionality', count: 9 },
  { topic: 'Template quality', count: 5 },
  { topic: 'Export limitations', count: 7 },
  { topic: 'Notification overload', count: 13 },
  { topic: 'Learning curve', count: 19 },
  { topic: 'Offline capability', count: 4 },
  { topic: 'API reliability', count: 3 },
  { topic: 'Customer support', count: 10 },
  { topic: 'Data migration', count: 6 },
  { topic: 'Permission controls', count: 8 },
  { topic: 'Page load speed', count: 15 },
  { topic: 'Formula complexity', count: 7 },
  { topic: 'Calendar sync issues', count: 12 },
  { topic: 'Version history gaps', count: 5 },
]

const ROLE_DOT: Record<string, string> = {
  first_timer: '#3B82F6',
  daily_driver: '#E4E4E7',
  buyer: '#F59E0B',
}

interface RoundMessage {
  round: number
  agent_name: string
  agent_role: string
  model: string
  content: string
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

// Thin progress bar showing which debate round is active (0-based fill).
function RoundProgress({ current, total }: { current: number; total: number }) {
  return (
    <div style={{ display: 'flex', gap: 4, marginTop: 16 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            height: 4,
            borderRadius: 2,
            background: i < current ? '#3B82F6' : i === current ? '#3B82F6' : '#1E2028',
            animation: i === current ? 'progressPulse 2s ease-in-out infinite' : undefined,
          }}
        />
      ))}
    </div>
  )
}

// Animated UI stand-in for the server-side reconnaissance swarm completing before WS connect.
function SwarmCard({ product, onComplete }: { product: string; onComplete: () => void }) {
  const [scoutsDeployed, setScoutsDeployed] = useState(0)
  const [results, setResults] = useState<typeof SCOUT_RESULTS>([])
  const [flash, setFlash] = useState(false)
  const completedRef = useRef(false)
  // Keep onComplete stable across renders so the effect doesn't re-fire mid-animation
  const onCompleteRef = useRef(onComplete)
  useEffect(() => { onCompleteRef.current = onComplete }, [onComplete])

  useEffect(() => {
    let i = 0
    const interval = setInterval(() => {
      if (i < SCOUT_RESULTS.length) {
        const entry = SCOUT_RESULTS[i]
        if (entry) {
          setScoutsDeployed(i + 1)
          setResults((prev) => [...prev, entry])
        }
        i++
      } else {
        clearInterval(interval)
        setFlash(true)
        setTimeout(() => {
          setFlash(false)
          if (!completedRef.current) {
            completedRef.current = true
            onCompleteRef.current()
          }
        }, 500)
      }
    }, 300)
    return () => clearInterval(interval)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product])

  return (
    <div style={{
      background: '#12141A',
      border: `1px solid ${flash ? '#3B82F6' : '#1E2028'}`,
      borderRadius: 8,
      padding: 20,
      transition: 'border-color 300ms ease',
    }}>
      <p style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: '0.15em',
        color: '#71717A',
        textTransform: 'uppercase',
        marginBottom: 12,
      }}>
        RECONNAISSANCE
      </p>
      <p style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 14,
        color: '#E4E4E7',
        marginBottom: 16,
      }}>
        {scoutsDeployed} / 20 scouts deployed
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {results.filter(Boolean).map((r, i) => (
          <p key={i} style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: '#71717A',
            animation: 'fadeIn 200ms ease',
          }}>
            ✓ {r.topic} — {r.count} reviews found
          </p>
        ))}
      </div>
    </div>
  )
}

// Single round transcript card with role color and AGREE/DISAGREE badges when present.
function DebateCard({ msg }: { msg: RoundMessage }) {
  const dot = ROLE_DOT[msg.agent_role] ?? '#71717A'

  // Detect inline AGREE / DISAGREE markers in the raw content
  const hasAgree = /\bAGREE\b/i.test(msg.content)
  const hasDisagree = /\bDISAGREE\b/i.test(msg.content)

  return (
    <div style={{
      background: '#12141A',
      border: '1px solid #1E2028',
      borderRadius: 8,
      padding: 24,
      animation: 'fadeIn 300ms ease',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: dot, flexShrink: 0,
        }} />
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 14, fontWeight: 600, color: '#E4E4E7',
        }}>
          {msg.agent_name}
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10, color: '#71717A',
          background: '#0A0B0F',
          border: '1px solid #1E2028',
          borderRadius: 4, padding: '2px 8px', flexShrink: 0,
        }}>
          {msg.model}
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          {hasAgree && (
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10, fontWeight: 600,
              color: '#22C55E',
              background: 'rgba(34,197,94,0.1)',
              borderRadius: 4, padding: '2px 8px',
            }}>AGREE</span>
          )}
          {hasDisagree && (
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10, fontWeight: 600,
              color: '#EF4444',
              background: 'rgba(239,68,68,0.1)',
              borderRadius: 4, padding: '2px 8px',
            }}>DISAGREE</span>
          )}
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10, color: '#3F3F46',
          }}>
            ROUND {msg.round}
          </span>
        </div>
      </div>

      {/* Body */}
      <p style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 13, color: '#A1A1AA',
        lineHeight: 1.8, marginTop: 16,
        whiteSpace: 'pre-wrap',
      }}>
        {msg.content}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

// Live debate view: swarm animation, then WebSocket rounds and verdict handoff.
export default function DebateStream({ product, sessionId, onBack, onVerdict }: DebateStreamProps) {
  const [swarmDone, setSwarmDone] = useState(false)
  const [rounds, setRounds] = useState<RoundMessage[]>([])
  const [currentRound, setCurrentRound] = useState(0)
  const [wsError, setWsError] = useState('')
  const wsRef = useRef<WebSocket | null>(null)

  // Open WebSocket once the swarm animation completes
  const connectWS = useCallback(() => {
    // TODO: Wire to WebSocket for live streaming
    const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)

      if (msg.type === 'verdict') {
        onVerdict({
          score: msg.score,
          decision: msg.decision,
          top_3_fixes: msg.top_3_fixes,
        })
        ws.close()
        return
      }

      if (msg.type === 'error') {
        setWsError(msg.message ?? 'Unknown error from server')
        return
      }

      // Round message (no `type` field)
      setRounds((prev) => [...prev, msg as RoundMessage])
      setCurrentRound(msg.round)
    }

    ws.onerror = () => setWsError('WebSocket connection failed')

    return () => ws.close()
  }, [sessionId, onVerdict])

  useEffect(() => {
    if (swarmDone) {
      return connectWS()
    }
  }, [swarmDone, connectWS])

  // Cleanup on unmount
  useEffect(() => {
    return () => { wsRef.current?.close() }
  }, [])

  const handleSwarmComplete = useCallback(() => setSwarmDone(true), [])

  return (
    <div style={{ minHeight: '100vh', background: '#0A0B0F' }}>
      <style>{`
        @keyframes progressPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div style={{ maxWidth: 880, margin: '0 auto', padding: '32px 24px 64px' }}>
        {/* Top bar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span
              onClick={onBack}
              style={{
                width: 32, height: 32,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: '#71717A',
                fontFamily: "'Inter', sans-serif", fontSize: 18,
                transition: 'color 150ms ease',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = '#E4E4E7' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = '#71717A' }}
            >
              ←
            </span>
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
            ROUND {currentRound || 1} OF 4
          </span>
        </div>

        <RoundProgress current={Math.max(currentRound - 1, 0)} total={4} />

        {/* Swarm card */}
        <div style={{ marginTop: 24 }}>
          <SwarmCard product={product} onComplete={handleSwarmComplete} />
        </div>

        {/* WebSocket error */}
        {wsError && (
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11, color: '#EF4444',
            marginTop: 16,
          }}>
            Error: {wsError}
          </p>
        )}

        {/* Live debate cards from WebSocket */}
        {rounds.length > 0 && (
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {rounds.map((msg, i) => (
              <DebateCard key={i} msg={msg} />
            ))}
          </div>
        )}

        {/* Waiting indicator after swarm, before first round arrives */}
        {swarmDone && rounds.length === 0 && !wsError && (
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11, color: '#3F3F46',
            marginTop: 24,
            animation: 'progressPulse 2s ease-in-out infinite',
          }}>
            Waiting for agents...
          </p>
        )}
      </div>
    </div>
  )
}
