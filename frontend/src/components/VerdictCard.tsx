import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'

interface Round {
  round: number
  agent_name: string
  agent_role: string
  content: string
}

interface VerdictCardProps {
  product: string
  score: number
  decision: string
  fixes: string[]
  rounds: Round[]
  full_report: string
  onBack: () => void
}

type Verdict = 'YES' | 'NO' | 'YES WITH CONDITIONS'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number): string {
  if (score >= 70) return '#22C55E'
  if (score >= 40) return '#F59E0B'
  return '#EF4444'
}

function normalizeVerdict(raw: string): Verdict {
  const upper = raw.toUpperCase()
  if (upper.includes('YES WITH CONDITIONS')) return 'YES WITH CONDITIONS'
  if (upper.includes('YES')) return 'YES'
  return 'NO'
}

function verdictStyle(verdict: Verdict) {
  switch (verdict) {
    case 'YES':
      return { bg: 'rgba(34,197,94,0.08)', color: '#22C55E', border: 'rgba(34,197,94,0.3)' }
    case 'NO':
      return { bg: 'rgba(239,68,68,0.08)', color: '#EF4444', border: 'rgba(239,68,68,0.3)' }
    case 'YES WITH CONDITIONS':
      return { bg: 'rgba(245,158,11,0.08)', color: '#F59E0B', border: 'rgba(245,158,11,0.3)' }
  }
}

function extractFirstSentence(text: string): string {
  const cleaned = text.replace(/^(BUY DECISION|OVERALL SCORE)[^\n]*\n*/gi, '').trim()
  const match = cleaned.match(/^[^.!?\n]+[.!?]/)
  return match ? match[0].trim() : cleaned.slice(0, 140).trim()
}

function extractParagraphs(text: string): string[] {
  return text
    .split(/\n\n+/)
    .map(p => p.trim())
    .filter(p => p.length > 40 && !/^(BUY DECISION|OVERALL SCORE)\s*:/i.test(p))
}

function extractSection(text: string, header: string): string {
  const re = new RegExp(
    `${header}[:\\s]*((?:.|\\n)*?)(?:\\n\\n[A-Z][A-Z\\s]{3,}:|$)`,
    'i',
  )
  const match = text.match(re)
  return match ? match[1].trim() : ''
}

function parseFixParts(fix: string): { title: string; description: string } {
  const emdash = fix.split(/\s+[—–]\s+/)
  if (emdash.length >= 2) {
    return { title: emdash[0].trim(), description: emdash.slice(1).join(' — ').trim() }
  }
  const colon = fix.indexOf(':')
  if (colon > 0 && colon < 60) {
    return { title: fix.slice(0, colon).trim(), description: fix.slice(colon + 1).trim() }
  }
  return { title: fix.split(' ').slice(0, 5).join(' '), description: fix }
}

function parseImpact(fix: string, index: number): 'HIGH' | 'MEDIUM' | 'LOW' {
  const pct = fix.match(/~(\d+)%/)
  if (pct) {
    const n = parseInt(pct[1])
    if (n >= 25) return 'HIGH'
    if (n >= 15) return 'MEDIUM'
    return 'LOW'
  }
  return index === 0 ? 'HIGH' : index === 1 ? 'MEDIUM' : 'LOW'
}

function impactStyle(impact: 'HIGH' | 'MEDIUM' | 'LOW') {
  switch (impact) {
    case 'HIGH':   return { color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.25)' }
    case 'MEDIUM': return { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.25)' }
    case 'LOW':    return { color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.25)' }
  }
}

const ROLE_LABEL: Record<string, string> = {
  first_timer: 'First Timer',
  daily_driver: 'Daily Driver',
  buyer: 'Buyer',
}

const ROLE_COLOR: Record<string, string> = {
  first_timer: '#3B82F6',
  daily_driver: '#A1A1AA',
  buyer: '#F59E0B',
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionLabel({ children }: { children: string }) {
  return (
    <p style={{
      fontFamily: "'Inter', sans-serif",
      fontSize: 13,
      fontWeight: 600,
      letterSpacing: '0.15em',
      textTransform: 'uppercase',
      color: '#3B82F6',
      margin: '0 0 20px',
    }}>
      {children}
    </p>
  )
}

function Card({ children, style }: { children: ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: '#12141A',
      border: '1px solid #1E2028',
      borderRadius: 12,
      padding: 32,
      ...style,
    }}>
      {children}
    </div>
  )
}

function Divider() {
  return <div style={{ height: 1, background: '#1E2028', margin: '24px 0' }} />
}

function ScoreRing({ score }: { score: number }) {
  const [animated, setAnimated] = useState(0)
  const radius = 54
  const stroke = 3
  const circumference = 2 * Math.PI * radius
  const filled = (animated / 100) * circumference
  const size = (radius + stroke) * 2 + 4

  useEffect(() => {
    const start = performance.now()
    const duration = 1200
    function tick(now: number) {
      const progress = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setAnimated(Math.round(score * eased))
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [score])

  const color = scoreColor(score)

  return (
    <div style={{
      position: 'relative',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: 120,
      height: 120,
    }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ position: 'absolute' }}
      >
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#1E2028" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={`${filled} ${circumference - filled}`}
          strokeDashoffset={circumference * 0.25}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 80ms linear' }}
        />
      </svg>
      <div style={{ textAlign: 'center', position: 'relative' }}>
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 48,
          fontWeight: 300,
          color,
          lineHeight: 1,
          display: 'block',
        }}>
          {animated}
        </span>
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 11,
          color: '#3F3F46',
          letterSpacing: '0.05em',
        }}>
          / 100
        </span>
      </div>
    </div>
  )
}

function RoundExpander({ round }: { round: Round }) {
  const [open, setOpen] = useState(false)
  const roleColor = ROLE_COLOR[round.agent_role] ?? '#71717A'
  const roleLabel = ROLE_LABEL[round.agent_role] ?? round.agent_role
  const previewLines = round.content.split('\n').filter(l => l.trim()).slice(0, 2).join(' ')
  const paragraphs = round.content.split(/\n\n+/).filter(p => p.trim())

  return (
    <div style={{
      background: '#0D0F14',
      border: '1px solid #1E2028',
      borderRadius: 10,
      overflow: 'hidden',
      transition: 'border-color 150ms ease',
    }}>
      {/* Header row */}
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          padding: '18px 24px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          userSelect: 'none',
        }}
      >
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: roleColor, flexShrink: 0,
        }} />
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 14, fontWeight: 600, color: '#E4E4E7',
        }}>
          {round.agent_name}
        </span>
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 10, fontWeight: 600,
          color: roleColor,
          background: `${roleColor}18`,
          border: `1px solid ${roleColor}35`,
          borderRadius: 100,
          padding: '2px 10px',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>
          {roleLabel}
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10, color: '#3F3F46',
          marginLeft: 'auto',
          flexShrink: 0,
        }}>
          ROUND {round.round}
        </span>
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 13, color: '#3F3F46',
          marginLeft: 8, flexShrink: 0,
          display: 'inline-block',
          transition: 'transform 200ms ease',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        }}>
          ↓
        </span>
      </div>

      {/* Preview (collapsed) */}
      {!open && (
        <div style={{ padding: '0 24px 18px', borderTop: '1px solid #1A1C24' }}>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 13, color: '#3F3F46',
            lineHeight: 1.5, margin: 0,
            overflow: 'hidden',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}>
            {previewLines}
          </p>
        </div>
      )}

      {/* Full content (expanded) */}
      {open && (
        <div style={{ padding: '0 24px 24px', borderTop: '1px solid #1A1C24' }}>
          {paragraphs.map((para, i) => (
            <p key={i} style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 15, color: '#A1A1AA',
              lineHeight: 1.7,
              margin: i === 0 ? '20px 0 0' : '14px 0 0',
            }}>
              {para}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function VerdictCard({
  product, score, decision, fixes, rounds, full_report, onBack,
}: VerdictCardProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50)
    return () => clearTimeout(t)
  }, [])

  const verdict = normalizeVerdict(decision)
  const vs = verdictStyle(verdict)
  const color = scoreColor(score)

  // Parse report sections
  const firstSentence = full_report ? extractFirstSentence(full_report) : ''
  const allParas = extractParagraphs(full_report)

  // Executive summary: skip headers, top-3 lists, and the competitive section
  const execParas = allParas
    .filter(p => !/^(TOP 3|COMPETI|VERDICT PREVIEW|BUY DECISION|OVERALL SCORE|FATAL|^\d+\.)/i.test(p))
    .slice(0, 4)

  // Competitive positioning section
  const competitiveRaw =
    extractSection(full_report, 'COMPETITIVE POSITIONING') ||
    extractSection(full_report, 'COMPETITIVE POSITION') ||
    allParas.find(p => /competi|versus|better than|stealing|differenti/i.test(p)) ||
    ''

  const competitiveParas = competitiveRaw
    ? competitiveRaw.split(/\n+/).filter(l => l.trim()).map(l => l.trim())
    : []

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0A0B0F',
      opacity: mounted ? 1 : 0,
      transition: 'opacity 400ms ease',
      scrollBehavior: 'smooth',
    }}>
      <style>{`
        @media (max-width: 600px) {
          .vc-metrics-grid { grid-template-columns: repeat(2, 1fr) !important; }
        }
      `}</style>

      <div style={{ maxWidth: 800, margin: '0 auto', padding: '64px 24px 96px' }}>

        {/* ── Section 1: Hero ─────────────────────────────────────────── */}
        <Card style={{ textAlign: 'center', marginBottom: 48 }}>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 26, fontWeight: 600,
            color: '#E4E4E7',
            letterSpacing: '-0.02em',
            margin: '0 0 32px',
          }}>
            {product}
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
            <ScoreRing score={score} />
          </div>

          <span style={{
            display: 'inline-block',
            background: vs.bg,
            color: vs.color,
            border: `1px solid ${vs.border}`,
            borderRadius: 100,
            padding: '8px 28px',
            fontFamily: "'Inter', sans-serif",
            fontSize: 11, fontWeight: 700,
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
            marginBottom: firstSentence ? 28 : 0,
          }}>
            {verdict}
          </span>

          {firstSentence && (
            <p style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 16, fontWeight: 400,
              color: '#71717A',
              lineHeight: 1.65,
              maxWidth: 560,
              margin: '0 auto',
            }}>
              {firstSentence}
            </p>
          )}
        </Card>

        {/* ── Section 2: Executive Summary ────────────────────────────── */}
        <Card style={{ marginBottom: 48 }}>
          <SectionLabel>Executive Summary</SectionLabel>

          {execParas.length > 0 ? (
            execParas.map((para, i) => (
              <p key={i} style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 15, fontWeight: 400,
                color: '#A1A1AA', lineHeight: 1.75,
                margin: i === 0 ? 0 : '16px 0 0',
              }}>
                {para}
              </p>
            ))
          ) : full_report ? (
            <p style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 15, color: '#A1A1AA',
              lineHeight: 1.75, margin: 0,
            }}>
              {full_report.slice(0, 600)}
            </p>
          ) : null}

          <Divider />

          {/* Key metrics callout grid */}
          <div className="vc-metrics-grid" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 12,
          }}>
            {[
              { label: 'Overall Score', value: `${score}/100`, color },
              { label: 'Decision', value: verdict, color: vs.color },
              { label: 'Rounds Completed', value: `${rounds.length} of 4`, color: '#52525B' },
              { label: 'Priority Fixes', value: `${fixes.length} identified`, color: '#52525B' },
            ].map(m => (
              <div key={m.label} style={{
                background: '#0A0B0F',
                border: '1px solid #1E2028',
                borderRadius: 8,
                padding: '16px 18px',
              }}>
                <p style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 10, fontWeight: 600,
                  color: '#3F3F46',
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  margin: '0 0 8px',
                }}>
                  {m.label}
                </p>
                <p style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 15, fontWeight: 600,
                  color: m.color, margin: 0,
                }}>
                  {m.value}
                </p>
              </div>
            ))}
          </div>
        </Card>

        {/* ── Section 3: Top 3 Priority Fixes ─────────────────────────── */}
        {fixes.length > 0 && (
          <Card style={{ marginBottom: 48 }}>
            <SectionLabel>Priority Fixes</SectionLabel>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {fixes.slice(0, 3).map((fix, i) => {
                const { title, description } = parseFixParts(fix)
                const impact = parseImpact(fix, i)
                const is = impactStyle(impact)
                return (
                  <div key={i} style={{
                    background: '#0A0B0F',
                    border: '1px solid #1E2028',
                    borderRadius: 10,
                    padding: '22px 24px',
                  }}>
                    {/* Title row */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      gap: 16,
                      marginBottom: 12,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 11, color: '#3F3F46', flexShrink: 0,
                        }}>
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        <p style={{
                          fontFamily: "'Inter', sans-serif",
                          fontSize: 15, fontWeight: 600,
                          color: '#E4E4E7', margin: 0,
                        }}>
                          {title}
                        </p>
                      </div>
                      <span style={{
                        fontFamily: "'Inter', sans-serif",
                        fontSize: 10, fontWeight: 700,
                        color: is.color, background: is.bg,
                        border: `1px solid ${is.border}`,
                        borderRadius: 100, padding: '3px 12px',
                        letterSpacing: '0.08em', flexShrink: 0,
                      }}>
                        {impact}
                      </span>
                    </div>

                    {/* Description */}
                    <p style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 14, color: '#71717A',
                      lineHeight: 1.65, margin: 0,
                    }}>
                      {description}
                    </p>
                  </div>
                )
              })}
            </div>
          </Card>
        )}

        {/* ── Section 4: The Debate ────────────────────────────────────── */}
        {rounds.length > 0 && (
          <Card style={{ marginBottom: 48 }}>
            <SectionLabel>The Debate</SectionLabel>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {rounds.map(round => (
                <RoundExpander key={round.round} round={round} />
              ))}
            </div>
          </Card>
        )}

        {/* ── Section 5: Competitive Position ─────────────────────────── */}
        {competitiveParas.length > 0 && (
          <Card style={{ marginBottom: 48 }}>
            <SectionLabel>Competitive Position</SectionLabel>
            {competitiveParas.map((line, i) => (
              <p key={i} style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 15, color: '#A1A1AA',
                lineHeight: 1.75,
                margin: i === 0 ? 0 : '12px 0 0',
              }}>
                {line}
              </p>
            ))}
          </Card>
        )}

        {/* ── Section 6: Footer ────────────────────────────────────────── */}
        <div style={{ textAlign: 'center', paddingTop: 16 }}>
          <button
            onClick={onBack}
            style={{
              background: '#3B82F6',
              border: 'none',
              borderRadius: 8,
              padding: '14px 36px',
              fontFamily: "'Inter', sans-serif",
              fontSize: 14, fontWeight: 600,
              color: '#fff', cursor: 'pointer',
              transition: 'background 150ms ease',
              display: 'block',
              margin: '0 auto 20px',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#4B8FF7' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#3B82F6' }}
          >
            Start New Analysis
          </button>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 12, color: '#3F3F46',
            letterSpacing: '0.02em',
            margin: 0,
          }}>
            Powered by War Room — 3 AI models, 29,735 real user reviews
          </p>
        </div>

      </div>
    </div>
  )
}
