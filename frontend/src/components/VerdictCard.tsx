import { useState, useEffect, useMemo } from 'react'
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
// Core helpers
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
// Feature evidence — types
// ---------------------------------------------------------------------------

type SourceType = 'reddit' | 'hn' | 'playstore' | 'appstore' | 'g2' | 'unknown'

interface ReviewCitation {
  quote: string
  source: string
  sourceType: SourceType
  roundNum: number
  context: string
}

interface FeatureEvidence {
  featureName: string
  aiAnalysis: string
  citations: ReviewCitation[]
  sentiment: 'positive' | 'mixed' | 'negative'
  synthesis: string
}

const SOURCE_BADGES: Record<SourceType, { label: string; bg: string }> = {
  reddit:    { label: 'Reddit',     bg: '#FF4500' },
  hn:        { label: 'HN',         bg: '#FF6600' },
  playstore: { label: 'Play Store', bg: '#34A853' },
  appstore:  { label: 'App Store',  bg: '#0070C9' },
  g2:        { label: 'G2',         bg: '#FF492C' },
  unknown:   { label: 'Review',     bg: '#52525B' },
}

const FEATURE_TOPICS: Array<{ name: string; keywords: string[] }> = [
  { name: 'Search & Findability',  keywords: ['search', 'find', 'findability', 'discover'] },
  { name: 'Mobile Experience',     keywords: ['mobile', 'app', 'crash', 'android', 'ios', 'phone', 'stability'] },
  { name: 'Onboarding',            keywords: ['onboard', 'setup', 'new user', 'tutorial', 'getting started', 'learn', 'setup', 'drag and drop', 'discoverability'] },
  { name: 'Performance & Speed',   keywords: ['slow', 'speed', 'performance', 'load', 'fast', 'lag'] },
  { name: 'Pricing & Value',       keywords: ['pric', 'cost', 'free', 'pay', 'plan', 'tier', 'expensive', 'cheap', 'revenue'] },
  { name: 'Collaboration',         keywords: ['collaborat', 'share', 'team', 'permission', 'workspace'] },
  { name: 'Core Features',         keywords: ['feature', 'block', 'database', 'template', 'workflow', 'command'] },
]

// ---------------------------------------------------------------------------
// Feature evidence — parsing
// ---------------------------------------------------------------------------

function detectSourceType(text: string): SourceType {
  const lower = text.toLowerCase()
  if (/r\/\w+|reddit/i.test(lower)) return 'reddit'
  if (/hacker.?news|news\.yc|hn\./i.test(lower)) return 'hn'
  if (/google.?play|play.?store/i.test(lower)) return 'playstore'
  if (/app.?store|apple/i.test(lower)) return 'appstore'
  if (/g2\.com|g2 review/i.test(lower)) return 'g2'
  return 'unknown'
}

function scoreFeatureTopic(text: string, keywords: string[]): number {
  const lower = text.toLowerCase()
  return keywords.reduce((sum, kw) => sum + (lower.includes(kw) ? 1 : 0), 0)
}

function matchFeatureTopic(text: string): { name: string; keywords: string[] } {
  let best = FEATURE_TOPICS[FEATURE_TOPICS.length - 1]
  let bestScore = 0
  for (const topic of FEATURE_TOPICS) {
    const s = scoreFeatureTopic(text, topic.keywords)
    if (s > bestScore) { bestScore = s; best = topic }
  }
  return best
}

function extractCitations(rounds: Round[]): ReviewCitation[] {
  const citations: ReviewCitation[] = []

  for (const round of rounds) {
    const text = round.content
    const lines = text.split('\n')

    for (const line of lines) {
      // ── Pattern A: 'quote' (Source) ──────────────────────────────────────
      // Find source attributions: (r/Notion), (Reddit), (Google Play), etc.
      const srcRe = /\((r\/\w+|Reddit|Google Play|Play Store|Hacker News|HN|App Store|G2)[^)]{0,30}\)/gi
      let sm: RegExpExecArray | null
      while ((sm = srcRe.exec(line)) !== null) {
        const sourceStr = sm[1].trim()
        const beforeSrc = line.slice(0, sm.index)
        // Find bounding single-quotes: use first ' as opener and last ' as closer
        const lastQ = beforeSrc.lastIndexOf("'")
        if (lastQ > 10) {
          const openIdx = beforeSrc.indexOf("'")
          if (openIdx >= 0 && lastQ - openIdx > 14) {
            const quote = beforeSrc.slice(openIdx + 1, lastQ).trim()
            if (quote.length > 14) {
              const lineIdx = text.indexOf(line)
              citations.push({
                quote: quote.slice(0, 200),
                source: sourceStr,
                sourceType: detectSourceType(sourceStr),
                roundNum: round.round,
                context: lineIdx >= 0
                  ? text.slice(Math.max(0, lineIdx - 120), lineIdx + line.length + 60)
                  : line,
              })
            }
          }
        }
      }

      // ── Pattern B: N of M [Source] reviews mention [thing] ───────────────
      const statRe = /(\d+)\s+of\s+(?:the\s+)?(?:last\s+)?\d+\s+(Google Play|Play Store|App Store|Reddit)[^,\n]*reviews?\s+mention([^.!?]{10,100})/i
      const statM = statRe.exec(line)
      if (statM) {
        const lineIdx = text.indexOf(line)
        citations.push({
          quote: `${statM[1]} reviews mention${statM[3]}`.trim().slice(0, 180),
          source: statM[2],
          sourceType: detectSourceType(statM[2]),
          roundNum: round.round,
          context: lineIdx >= 0
            ? text.slice(Math.max(0, lineIdx - 60), lineIdx + line.length + 120)
            : line,
        })
      }
    }

    // ── Pattern C: As one user on [Source] put it: 'quote' ─────────────────
    // Uses full text, not line-by-line, since this often spans a sentence.
    const asRe = /as (?:one )?(?:user|users?) (?:on|at|from) ([^:'"]{2,30}?) put it[:\s]+['']([^'']{15,250})['']/gi
    let am: RegExpExecArray | null
    while ((am = asRe.exec(text)) !== null) {
      citations.push({
        quote: am[2].trim().slice(0, 200),
        source: am[1].trim(),
        sourceType: detectSourceType(am[1]),
        roundNum: round.round,
        context: text.slice(Math.max(0, am.index - 60), am.index + am[0].length + 100),
      })
    }
  }

  // Deduplicate by first 28 chars of quote
  return citations.filter((c, i, arr) =>
    c.quote.length > 14 &&
    arr.findIndex(x => x.quote.slice(0, 28) === c.quote.slice(0, 28)) === i
  )
}

function getBestAIAnalysis(rounds: Round[], keywords: string[]): string {
  let best = { text: '', score: 0 }
  for (const round of rounds) {
    for (const para of round.content.split(/\n\n+/)) {
      const s = scoreFeatureTopic(para, keywords)
      if (s > best.score && para.length > 55) best = { text: para, score: s }
    }
  }
  if (!best.text) return ''
  return best.text.length > 260
    ? best.text.slice(0, 260).trim() + '…'
    : best.text.trim()
}

function detectSentiment(texts: string[]): 'positive' | 'mixed' | 'negative' {
  const blob = texts.join(' ').toLowerCase()
  const neg = ['broke', 'crash', 'broken', 'slow', 'frustrat', 'hate', 'bad', 'terrible',
    'problem', 'fail', 'stuck', 'confus', 'missing', 'annoying', 'useless', 'worse', 'left', 'switch']
  const pos = ['great', 'love', 'perfect', 'excellent', 'amazing', 'fast', 'easy',
    'intuitive', 'best', 'good', 'helpful', 'nice', 'solid', 'useful']
  const n = neg.reduce((s, k) => s + (blob.includes(k) ? 1 : 0), 0)
  const p = pos.reduce((s, k) => s + (blob.includes(k) ? 1 : 0), 0)
  if (n > p + 1) return 'negative'
  if (p > n + 1) return 'positive'
  return 'mixed'
}

function buildFeatureEvidence(rounds: Round[], fixes: string[]): FeatureEvidence[] {
  const allCitations = extractCitations(rounds)
  if (allCitations.length < 2) return []

  // Group citations by feature topic
  const topicMap = new Map<string, { topic: typeof FEATURE_TOPICS[0]; cits: ReviewCitation[] }>()
  for (const cit of allCitations) {
    const topic = matchFeatureTopic(cit.context + ' ' + cit.quote)
    if (!topicMap.has(topic.name)) topicMap.set(topic.name, { topic, cits: [] })
    topicMap.get(topic.name)!.cits.push(cit)
  }

  const results: FeatureEvidence[] = []

  for (const [featureName, { topic, cits }] of topicMap.entries()) {
    const aiAnalysis = getBestAIAnalysis(rounds, topic.keywords)
    if (!aiAnalysis) continue

    const sentiment = detectSentiment(cits.map(c => c.quote + ' ' + c.context))
    const negCount = cits.filter(c => detectSentiment([c.quote]) === 'negative').length

    const relatedFix = fixes.find(f =>
      topic.keywords.some(kw => f.toLowerCase().includes(kw))
    ) ?? ''
    const fixTitle = relatedFix ? parseFixParts(relatedFix).title : ''

    const synthesis = [
      `${cits.length} user citation${cits.length !== 1 ? 's' : ''} reference ${featureName.toLowerCase()} directly.`,
      negCount > 0
        ? `${negCount} highlight${negCount !== 1 ? ' pain points' : 's a pain point'} competitors can exploit.`
        : 'User sentiment in this area is generally favourable.',
      fixTitle ? `Recommended action: ${fixTitle}.` : '',
    ].filter(Boolean).join(' ')

    results.push({ featureName, aiAnalysis, citations: cits.slice(0, 3), sentiment, synthesis })
    if (results.length >= 6) break
  }

  return results
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
        width={size} height={size} viewBox={`0 0 ${size} ${size}`}
        style={{ position: 'absolute' }}
      >
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#1E2028" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke={color} strokeWidth={stroke}
          strokeDasharray={`${filled} ${circumference - filled}`}
          strokeDashoffset={circumference * 0.25} strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 80ms linear' }}
        />
      </svg>
      <div style={{ textAlign: 'center', position: 'relative' }}>
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 48, fontWeight: 300,
          color, lineHeight: 1, display: 'block',
        }}>
          {animated}
        </span>
        <span style={{
          fontFamily: "'Inter', sans-serif", fontSize: 11,
          color: '#3F3F46', letterSpacing: '0.05em',
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
      background: '#0D0F14', border: '1px solid #1E2028',
      borderRadius: 10, overflow: 'hidden',
    }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          padding: '18px 24px', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 12, userSelect: 'none',
        }}
      >
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: roleColor, flexShrink: 0 }} />
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: 14, fontWeight: 600, color: '#E4E4E7' }}>
          {round.agent_name}
        </span>
        <span style={{
          fontFamily: "'Inter', sans-serif", fontSize: 10, fontWeight: 600,
          color: roleColor, background: `${roleColor}18`, border: `1px solid ${roleColor}35`,
          borderRadius: 100, padding: '2px 10px', letterSpacing: '0.06em', textTransform: 'uppercase',
        }}>
          {roleLabel}
        </span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: '#3F3F46', marginLeft: 'auto', flexShrink: 0 }}>
          ROUND {round.round}
        </span>
        <span style={{
          fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#3F3F46',
          marginLeft: 8, flexShrink: 0, display: 'inline-block',
          transition: 'transform 200ms ease',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        }}>
          ↓
        </span>
      </div>

      {!open && (
        <div style={{ padding: '0 24px 18px', borderTop: '1px solid #1A1C24' }}>
          <p style={{
            fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#3F3F46',
            lineHeight: 1.5, margin: 0,
            overflow: 'hidden', display: '-webkit-box',
            WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
          }}>
            {previewLines}
          </p>
        </div>
      )}

      {open && (
        <div style={{ padding: '0 24px 24px', borderTop: '1px solid #1A1C24' }}>
          {paragraphs.map((para, i) => (
            <p key={i} style={{
              fontFamily: "'Inter', sans-serif", fontSize: 15, color: '#A1A1AA',
              lineHeight: 1.7, margin: i === 0 ? '20px 0 0' : '14px 0 0',
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
// Feature evidence sub-components
// ---------------------------------------------------------------------------

function SourceBadge({ type }: { type: SourceType }) {
  const { label, bg } = SOURCE_BADGES[type]
  return (
    <span style={{
      fontFamily: "'Inter', sans-serif",
      fontSize: 9, fontWeight: 700,
      color: '#fff', background: bg,
      borderRadius: 100, padding: '2px 8px',
      letterSpacing: '0.07em', textTransform: 'uppercase', flexShrink: 0,
    }}>
      {label}
    </span>
  )
}

function SentimentTag({ sentiment }: { sentiment: 'positive' | 'mixed' | 'negative' }) {
  const map = {
    positive: { color: '#22C55E', bg: 'rgba(34,197,94,0.08)',  border: 'rgba(34,197,94,0.25)',  label: 'Mostly Positive' },
    mixed:    { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.25)', label: 'Mixed' },
    negative: { color: '#EF4444', bg: 'rgba(239,68,68,0.08)',  border: 'rgba(239,68,68,0.25)',  label: 'Mostly Negative' },
  }[sentiment]
  return (
    <span style={{
      fontFamily: "'Inter', sans-serif",
      fontSize: 10, fontWeight: 600,
      color: map.color, background: map.bg, border: `1px solid ${map.border}`,
      borderRadius: 100, padding: '2px 10px', letterSpacing: '0.07em',
    }}>
      {map.label}
    </span>
  )
}

function FeatureEvidenceCard({ evidence }: { evidence: FeatureEvidence }) {
  // Build observation bullets from the AI analysis sentences (skip quoted passages)
  const bullets = evidence.aiAnalysis
    .split(/[.!?]\s+/)
    .map(s => s.replace(/^['"]|['"]$/g, '').trim())
    .filter(s => s.length > 20 && !/^['"]/.test(s) && !/^\d+$/.test(s))
    .slice(0, 3)

  return (
    <div style={{
      background: '#12141A',
      border: '1px solid #1E2028',
      borderRadius: 12,
      padding: 28,
      overflow: 'hidden',
    }}>
      {/* ── Two-column body ──────────────────────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '45% 1px 1fr',
        gap: 0,
        marginBottom: 20,
      }}>

        {/* Left — AI Analysis */}
        <div style={{ paddingRight: 24 }}>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 10, fontWeight: 600, color: '#3F3F46',
            letterSpacing: '0.12em', textTransform: 'uppercase',
            margin: '0 0 14px',
          }}>
            ANALYSIS — {evidence.featureName}
          </p>

          {/* Quote block */}
          <div style={{
            borderLeft: '2px solid #1E2028',
            paddingLeft: 14,
            marginBottom: 18,
          }}>
            <p style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 12, color: '#52525B',
              lineHeight: 1.65, margin: 0, fontStyle: 'italic',
            }}>
              "{evidence.aiAnalysis.slice(0, 220)}{evidence.aiAnalysis.length > 220 ? '…' : ''}"
            </p>
          </div>

          {/* Observation bullets */}
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 9, fontWeight: 600, color: '#3F3F46',
            letterSpacing: '0.1em', textTransform: 'uppercase',
            margin: '0 0 10px',
          }}>
            What our AI observed:
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {bullets.map((b, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <span style={{ color: '#3B82F6', fontSize: 9, paddingTop: 3, flexShrink: 0 }}>▸</span>
                <p style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 12, color: '#52525B',
                  lineHeight: 1.5, margin: 0,
                }}>
                  {b}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Vertical divider */}
        <div style={{ background: '#1E2028', width: 1 }} />

        {/* Right — Real User Reviews */}
        <div style={{ paddingLeft: 24 }}>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 10, fontWeight: 600, color: '#3F3F46',
            letterSpacing: '0.12em', textTransform: 'uppercase',
            margin: '0 0 14px',
          }}>
            WHAT REAL USERS SAY
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
            {evidence.citations.map((cit, i) => (
              <div key={i} style={{
                background: '#0D0F14',
                border: '1px solid #1A1C24',
                borderRadius: 8,
                padding: '10px 14px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <SourceBadge type={cit.sourceType} />
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 9, color: '#3F3F46',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {cit.source}
                  </span>
                </div>
                <p style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 12, color: '#71717A',
                  lineHeight: 1.6, margin: 0, fontStyle: 'italic',
                }}>
                  "{cit.quote.slice(0, 160)}{cit.quote.length > 160 ? '…' : ''}"
                </p>
              </div>
            ))}
          </div>

          {/* Sentiment row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 9, fontWeight: 600, color: '#3F3F46',
              letterSpacing: '0.1em', textTransform: 'uppercase',
            }}>
              Sentiment:
            </span>
            <SentimentTag sentiment={evidence.sentiment} />
          </div>
        </div>
      </div>

      {/* ── Synthesis — full width ────────────────────────────────────────── */}
      <div style={{ borderTop: '1px solid #1E2028', paddingTop: 16 }}>
        <span style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 9, fontWeight: 700, color: '#3B82F6',
          letterSpacing: '0.14em', textTransform: 'uppercase',
          display: 'block', marginBottom: 8,
        }}>
          SYNTHESIS
        </span>
        <p style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 13, color: '#A1A1AA',
          lineHeight: 1.65, margin: 0,
        }}>
          {evidence.synthesis}
        </p>
      </div>
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

  const firstSentence = full_report ? extractFirstSentence(full_report) : ''
  const allParas = extractParagraphs(full_report)

  const execParas = allParas
    .filter(p => !/^(TOP 3|COMPETI|VERDICT PREVIEW|BUY DECISION|OVERALL SCORE|FATAL|^\d+\.)/i.test(p))
    .slice(0, 4)

  const competitiveRaw =
    extractSection(full_report, 'COMPETITIVE POSITIONING') ||
    extractSection(full_report, 'COMPETITIVE POSITION') ||
    allParas.find(p => /competi|versus|better than|stealing|differenti/i.test(p)) ||
    ''

  const competitiveParas = competitiveRaw
    ? competitiveRaw.split(/\n+/).filter(l => l.trim()).map(l => l.trim())
    : []

  // Feature evidence: only rendered when citations found in rounds
  const featureEvidence = useMemo(() => buildFeatureEvidence(rounds, fixes), [rounds, fixes])
  const hasFeatureEvidence = featureEvidence.length > 0

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
          .vc-evidence-grid { grid-template-columns: 1fr !important; }
          .vc-evidence-divider { display: none !important; }
        }
      `}</style>

      <div style={{ maxWidth: 800, margin: '0 auto', padding: '64px 24px 96px' }}>

        {/* ── Section 1: Hero ─────────────────────────────────────────── */}
        <Card style={{ textAlign: 'center', marginBottom: 48 }}>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 26, fontWeight: 600, color: '#E4E4E7',
            letterSpacing: '-0.02em', margin: '0 0 32px',
          }}>
            {product}
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
            <ScoreRing score={score} />
          </div>

          <span style={{
            display: 'inline-block',
            background: vs.bg, color: vs.color, border: `1px solid ${vs.border}`,
            borderRadius: 100, padding: '8px 28px',
            fontFamily: "'Inter', sans-serif",
            fontSize: 11, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase',
            marginBottom: firstSentence ? 28 : 0,
          }}>
            {verdict}
          </span>

          {firstSentence && (
            <p style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 16, fontWeight: 400, color: '#71717A',
              lineHeight: 1.65, maxWidth: 560, margin: '0 auto',
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
                fontSize: 15, fontWeight: 400, color: '#A1A1AA',
                lineHeight: 1.75, margin: i === 0 ? 0 : '16px 0 0',
              }}>
                {para}
              </p>
            ))
          ) : full_report ? (
            <p style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 15, color: '#A1A1AA', lineHeight: 1.75, margin: 0,
            }}>
              {full_report.slice(0, 600)}
            </p>
          ) : null}

          <Divider />

          <div className="vc-metrics-grid" style={{
            display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12,
          }}>
            {[
              { label: 'Overall Score',      value: `${score}/100`,            color },
              { label: 'Decision',           value: verdict,                   color: vs.color },
              { label: 'Rounds Completed',   value: `${rounds.length} of 4`,   color: '#52525B' },
              { label: 'Priority Fixes',     value: `${fixes.length} identified`, color: '#52525B' },
            ].map(m => (
              <div key={m.label} style={{
                background: '#0A0B0F', border: '1px solid #1E2028', borderRadius: 8, padding: '16px 18px',
              }}>
                <p style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 10, fontWeight: 600, color: '#3F3F46',
                  letterSpacing: '0.1em', textTransform: 'uppercase', margin: '0 0 8px',
                }}>
                  {m.label}
                </p>
                <p style={{
                  fontFamily: "'Inter', sans-serif", fontSize: 15, fontWeight: 600,
                  color: m.color, margin: 0,
                }}>
                  {m.value}
                </p>
              </div>
            ))}
          </div>
        </Card>

        {/* ── Section 3: Feature-Level Evidence ───────────────────────── */}
        {hasFeatureEvidence && (
          <Card style={{ marginBottom: 48 }}>
            <SectionLabel>Feature Analysis</SectionLabel>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              {featureEvidence.map((ev, i) => (
                <FeatureEvidenceCard key={i} evidence={ev} />
              ))}
            </div>
          </Card>
        )}

        {/* ── Section 4: Top 3 Priority Fixes ─────────────────────────── */}
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
                    background: '#0A0B0F', border: '1px solid #1E2028',
                    borderRadius: 10, padding: '22px 24px',
                  }}>
                    <div style={{
                      display: 'flex', alignItems: 'flex-start',
                      justifyContent: 'space-between', gap: 16, marginBottom: 12,
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
                          fontSize: 15, fontWeight: 600, color: '#E4E4E7', margin: 0,
                        }}>
                          {title}
                        </p>
                      </div>
                      <span style={{
                        fontFamily: "'Inter', sans-serif",
                        fontSize: 10, fontWeight: 700,
                        color: is.color, background: is.bg, border: `1px solid ${is.border}`,
                        borderRadius: 100, padding: '3px 12px',
                        letterSpacing: '0.08em', flexShrink: 0,
                      }}>
                        {impact}
                      </span>
                    </div>
                    <p style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 14, color: '#71717A', lineHeight: 1.65, margin: 0,
                    }}>
                      {description}
                    </p>
                  </div>
                )
              })}
            </div>
          </Card>
        )}

        {/* ── Section 5: The Debate ────────────────────────────────────── */}
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

        {/* ── Section 6: Competitive Position ─────────────────────────── */}
        {competitiveParas.length > 0 && (
          <Card style={{ marginBottom: 48 }}>
            <SectionLabel>Competitive Position</SectionLabel>
            {competitiveParas.map((line, i) => (
              <p key={i} style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 15, color: '#A1A1AA',
                lineHeight: 1.75, margin: i === 0 ? 0 : '12px 0 0',
              }}>
                {line}
              </p>
            ))}
          </Card>
        )}

        {/* ── Section 7: Footer ────────────────────────────────────────── */}
        <div style={{ textAlign: 'center', paddingTop: 16 }}>
          <button
            onClick={onBack}
            style={{
              background: '#3B82F6', border: 'none', borderRadius: 8,
              padding: '14px 36px',
              fontFamily: "'Inter', sans-serif",
              fontSize: 14, fontWeight: 600, color: '#fff', cursor: 'pointer',
              transition: 'background 150ms ease',
              display: 'block', margin: '0 auto 20px',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#4B8FF7' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#3B82F6' }}
          >
            Start New Analysis
          </button>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 12, color: '#3F3F46', letterSpacing: '0.02em', margin: 0,
          }}>
            Powered by War Room — 3 AI models, 29,735 real user reviews
          </p>
        </div>

      </div>
    </div>
  )
}
