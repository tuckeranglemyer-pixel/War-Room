import { useState, useEffect, useRef } from 'react'

interface DebateStreamProps {
  product: string
  onBack: () => void
}

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

const SAMPLE_DEBATE = [
  {
    agent: 'Sprint-Obsessed PM Who Churned From ' ,
    dot: '#3B82F6',
    model: 'Llama 70B',
    round: 'ROUND 1',
    text: `The onboarding experience is fundamentally broken for anyone who doesn't already live in a project management tool. I signed up expecting a simple task tracker and was immediately dropped into a blank page with a "/" command prompt. No tutorial, no templates surfaced, no progressive disclosure. 73% of App Store reviews from the last 6 months mention confusion in the first session.`,
    badges: [] as { text: string; type: 'agree' | 'disagree' }[],
    severity: 8,
    sources: ['App Store', 'r/productivity', 'G2 Review'],
  },
  {
    agent: 'Power User Who Ships With It Daily',
    dot: '#E4E4E7',
    model: 'Qwen 32B',
    round: 'ROUND 1',
    text: `I need to push back on the offline mode complaint. G2 data shows only 12% of power users cite offline capability as a blocker, and the progressive web app caches recently-viewed pages adequately. The real issue is the mobile app — 340 of the last 500 Play Store reviews mention crashes during editing. That's where engineering hours should go.`,
    badges: [
      { text: 'DISAGREE', type: 'disagree' as const },
    ],
    severity: 6,
    sources: ['G2 Review', 'Play Store', 'r/Notion'],
  },
]

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

function SwarmCard({ product, onComplete }: { product: string; onComplete: () => void }) {
  const [scoutsDeployed, setScoutsDeployed] = useState(0)
  const [results, setResults] = useState<typeof SCOUT_RESULTS>([])
  const [flash, setFlash] = useState(false)
  const completedRef = useRef(false)

  useEffect(() => {
    let i = 0
    const interval = setInterval(() => {
      if (i < SCOUT_RESULTS.length) {
        setScoutsDeployed(i + 1)
        setResults((prev) => [...prev, SCOUT_RESULTS[i]])
        i++
      } else {
        clearInterval(interval)
        setFlash(true)
        setTimeout(() => {
          setFlash(false)
          if (!completedRef.current) {
            completedRef.current = true
            onComplete()
          }
        }, 500)
      }
    }, 300)
    return () => clearInterval(interval)
  }, [product, onComplete])

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
        {results.map((r, i) => (
          <p
            key={i}
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              color: '#71717A',
              opacity: 1,
              animation: 'fadeIn 200ms ease',
            }}
          >
            ✓ {r.topic} — {r.count} reviews found
          </p>
        ))}
      </div>
    </div>
  )
}

function DebateCard({ card }: { card: typeof SAMPLE_DEBATE[0] }) {
  function severityColor(s: number): string {
    if (s < 4) return '#22C55E'
    if (s <= 7) return '#F59E0B'
    return '#EF4444'
  }

  return (
    <div style={{
      background: '#12141A',
      border: '1px solid #1E2028',
      borderRadius: 8,
      padding: 24,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <div style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: card.dot,
          flexShrink: 0,
        }} />
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 14,
          fontWeight: 600,
          color: '#E4E4E7',
        }}>
          {card.agent}
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          color: '#71717A',
          background: '#0A0B0F',
          border: '1px solid #1E2028',
          borderRadius: 4,
          padding: '2px 8px',
          flexShrink: 0,
        }}>
          {card.model}
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          color: '#3F3F46',
          marginLeft: 'auto',
          flexShrink: 0,
        }}>
          {card.round}
        </span>
      </div>

      {/* Body */}
      <div style={{ marginTop: 16 }}>
        <p style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 13,
          color: '#A1A1AA',
          lineHeight: 1.8,
        }}>
          {card.badges.map((b, i) => (
            <span key={i} style={{
              display: 'inline-block',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
              fontWeight: 600,
              color: b.type === 'agree' ? '#22C55E' : '#EF4444',
              background: b.type === 'agree' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
              borderRadius: 4,
              padding: '2px 8px',
              marginRight: 8,
              verticalAlign: 'middle',
            }}>
              {b.text}
            </span>
          ))}
          {card.text}
        </p>

        {/* Severity */}
        <p style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          color: severityColor(card.severity),
          marginTop: 12,
        }}>
          SEVERITY: {card.severity}/10
        </p>

        {/* Sources */}
        {card.sources.length > 0 && (
          <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
            {card.sources.map((s) => (
              <span key={s} style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 9,
                color: '#3F3F46',
                background: '#0A0B0F',
                border: '1px solid #1E2028',
                borderRadius: 100,
                padding: '2px 8px',
              }}>
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function DebateStream({ product, onBack }: DebateStreamProps) {
  const [swarmDone, setSwarmDone] = useState(false)

  // Prepend product name to first agent's persona
  const debateCards = SAMPLE_DEBATE.map((card, i) => ({
    ...card,
    agent: i === 0 ? card.agent + product : card.agent,
  }))

  return (
    <div style={{ minHeight: '100vh', background: '#0A0B0F' }}>
      <style>{`
        @keyframes progressPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div style={{
        maxWidth: 880,
        margin: '0 auto',
        padding: '32px 24px 64px',
      }}>
        {/* Top bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span
              onClick={onBack}
              style={{
                width: 32,
                height: 32,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                color: '#71717A',
                fontFamily: "'Inter', sans-serif",
                fontSize: 18,
                transition: 'color 150ms ease',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = '#E4E4E7' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = '#71717A' }}
            >
              ←
            </span>
            <span style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 16,
              fontWeight: 600,
              color: '#E4E4E7',
            }}>
              {product}
            </span>
          </div>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: '#71717A',
          }}>
            ROUND 1 OF 4
          </span>
        </div>

        <RoundProgress current={0} total={4} />

        {/* Swarm card */}
        <div style={{ marginTop: 24 }}>
          <SwarmCard product={product} onComplete={() => setSwarmDone(true)} />
        </div>

        {/* Debate cards — appear after swarm completes */}
        {/* TODO: Wire to WebSocket for live streaming */}
        {swarmDone && (
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {debateCards.map((card, i) => (
              <DebateCard key={i} card={card} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
