import { useEffect, useState } from 'react'

interface VerdictCardProps {
  product: string
  onBack: () => void
}

type Verdict = 'YES' | 'NO' | 'YES WITH CONDITIONS'

function scoreColor(score: number): string {
  if (score > 70) return '#22C55E'
  if (score >= 40) return '#F59E0B'
  return '#EF4444'
}

function verdictStyle(verdict: Verdict) {
  switch (verdict) {
    case 'YES':
      return { bg: 'rgba(34,197,94,0.1)', color: '#22C55E', border: 'rgba(34,197,94,0.15)' }
    case 'NO':
      return { bg: 'rgba(239,68,68,0.1)', color: '#EF4444', border: 'rgba(239,68,68,0.15)' }
    case 'YES WITH CONDITIONS':
      return { bg: 'rgba(245,158,11,0.1)', color: '#F59E0B', border: 'rgba(245,158,11,0.15)' }
  }
}

function ScoreRing({ score }: { score: number }) {
  const [animatedScore, setAnimatedScore] = useState(0)
  const radius = 56
  const stroke = 4
  const circumference = 2 * Math.PI * radius
  const filled = (animatedScore / 100) * circumference
  const size = (radius + stroke) * 2

  useEffect(() => {
    const start = performance.now()
    const duration = 1000
    function tick(now: number) {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setAnimatedScore(Math.round(score * eased))
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [score])

  return (
    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={radius + stroke}
          cy={radius + stroke}
          r={radius}
          fill="none"
          stroke="#1E2028"
          strokeWidth={stroke}
        />
        <circle
          cx={radius + stroke}
          cy={radius + stroke}
          r={radius}
          fill="none"
          stroke={scoreColor(score)}
          strokeWidth={stroke}
          strokeDasharray={`${filled} ${circumference - filled}`}
          strokeDashoffset={circumference * 0.25}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 100ms linear' }}
        />
      </svg>
      <div style={{ position: 'absolute', textAlign: 'center' }}>
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 48,
          fontWeight: 600,
          color: '#E4E4E7',
          lineHeight: 1,
          display: 'block',
        }}>
          {animatedScore}
        </span>
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 14,
          fontWeight: 400,
          color: '#3F3F46',
        }}>
          / 100
        </span>
      </div>
    </div>
  )
}

const SCORE = 68
const VERDICT: Verdict = 'YES WITH CONDITIONS'
const FIXES = [
  {
    priority: '01',
    desc: 'Redesign first-run onboarding — current flow assumes prior knowledge of databases and loses 73% of new users in the first session.',
    impact: '~25% retention impact',
  },
  {
    priority: '02',
    desc: 'Rebuild mobile editing experience — 340 of last 500 Play Store reviews cite crashes during document editing.',
    impact: '~20% retention impact',
  },
  {
    priority: '03',
    desc: 'Rework notification system — users across all review platforms report alert fatigue leading to missed deadlines.',
    impact: '~12% satisfaction impact',
  },
]

export default function VerdictCard({ product, onBack }: VerdictCardProps) {
  const vs = verdictStyle(VERDICT)

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '64px 24px',
    }}>
      {/* Main card */}
      <div style={{
        maxWidth: 480,
        width: '100%',
        background: '#12141A',
        border: '1px solid #1E2028',
        borderRadius: 8,
        padding: '48px 40px',
        textAlign: 'center',
      }}>
        {/* Product name */}
        <p style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          color: '#71717A',
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
        }}>
          {product}
        </p>

        {/* Score ring */}
        <div style={{ marginTop: 24 }}>
          <ScoreRing score={SCORE} />
        </div>

        {/* Verdict badge */}
        <div style={{ marginTop: 24 }}>
          <span style={{
            display: 'inline-block',
            background: vs.bg,
            color: vs.color,
            border: `1px solid ${vs.border}`,
            borderRadius: 100,
            padding: '6px 20px',
            fontFamily: "'Inter', sans-serif",
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
          }}>
            {VERDICT}
          </span>
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: '#1E2028', margin: '32px 0' }} />

        {/* Fixes */}
        <div style={{ textAlign: 'left' }}>
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            color: '#3F3F46',
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            marginBottom: 16,
          }}>
            PRIORITY FIXES
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {FIXES.map((fix) => (
              <div key={fix.priority} style={{ display: 'flex', gap: 12 }}>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                  color: '#3F3F46',
                  flexShrink: 0,
                  paddingTop: 2,
                }}>
                  {fix.priority}
                </span>
                <div>
                  <p style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: 13,
                    color: '#A1A1AA',
                    lineHeight: 1.6,
                    margin: 0,
                  }}>
                    {fix.desc}
                  </p>
                  <p style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10,
                    color: '#F59E0B',
                    marginTop: 4,
                  }}>
                    {fix.impact}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: '#1E2028', margin: '32px 0' }} />

        {/* Footer */}
        <p style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9,
          color: '#3F3F46',
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
        }}>
          ADVERSARIALLY TESTED BY 3 AI ARCHITECTURES
        </p>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 32 }}>
          <button
            onClick={onBack}
            style={{
              background: 'transparent',
              border: '1px solid #1E2028',
              borderRadius: 6,
              padding: '10px 20px',
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              fontWeight: 500,
              color: '#71717A',
              cursor: 'pointer',
              transition: 'all 150ms ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#2A2D38'
              e.currentTarget.style.color = '#E4E4E7'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = '#1E2028'
              e.currentTarget.style.color = '#71717A'
            }}
          >
            Run Another
          </button>
          <button
            style={{
              background: '#3B82F6',
              border: 'none',
              borderRadius: 6,
              padding: '10px 20px',
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              fontWeight: 500,
              color: '#fff',
              cursor: 'pointer',
              transition: 'background 150ms ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = '#4B8FF7' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '#3B82F6' }}
          >
            Share Report
          </button>
        </div>
      </div>

      {/* Back link outside card */}
      <span
        onClick={onBack}
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 12,
          color: '#3F3F46',
          marginTop: 24,
          cursor: 'pointer',
          transition: 'color 150ms ease',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.color = '#71717A' }}
        onMouseLeave={(e) => { e.currentTarget.style.color = '#3F3F46' }}
      >
        Back to War Room
      </span>
    </div>
  )
}
