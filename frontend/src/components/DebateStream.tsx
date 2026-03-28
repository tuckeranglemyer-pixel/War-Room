import { useState, useEffect, useRef, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import type { VerdictData } from '../App'
import { fadeUp, spring } from '../animations'

interface DebateStreamProps {
  product: string
  sessionId: string
  onBack: () => void
  onVerdict: (data: VerdictData) => void
}

interface RoundMessage {
  round: number
  agent_name: string
  agent_role: string
  model: string
  content: string
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

const ROLE_DOT: Record<string, string> = {
  first_timer: '#3B82F6',
  daily_driver: '#E4E4E7',
  buyer: '#F59E0B',
}

const INIT_AGENTS = [
  { role: 'FIRST-TIMER', model: 'Llama 70B', dotColor: '#3B82F6' },
  { role: 'DAILY DRIVER', model: 'Qwen 32B', dotColor: '#E4E4E7' },
  { role: 'BUYER', model: 'Mistral 24B', dotColor: '#F59E0B' },
]

const DEMO_ROUNDS: RoundMessage[] = [
  {
    round: 1,
    agent_name: 'First-Timer',
    agent_role: 'first_timer',
    model: 'Llama 70B',
    content: "The onboarding experience is broken for anyone who doesn't already live in a project management tool. I signed up expecting a simple task tracker and was dropped into a blank page with a '/' command prompt. No tutorial, no templates surfaced, no progressive disclosure.\n\nAs one user on r/Notion put it: 'Search is exactly why I left Notion too. Once your docs grow, it feels unusable unless you remember the exact wording.'\n\nSEVERITY: 8/10\n\nThe competitor that handles this better: Obsidian. Zero onboarding friction \u2014 you open it, you start typing. No databases, no blocks, no learning curve.",
  },
  {
    round: 2,
    agent_name: 'Daily Driver',
    agent_role: 'daily_driver',
    model: 'Qwen 32B',
    content: "DISAGREE on the onboarding criticism. The '/' command system IS Notion \u2014 removing it would gut the product. Power users chose Notion specifically because of blocks and databases. The learning curve is the moat.\n\nBut I AGREE the search is catastrophically bad. 'Been using Notion for years, and though it's not perfect I do love it. But man it is soooo slow, and I swear it's only gotten slower.' (r/Notion)\n\nHidden problem the First-Timer missed: mobile editing. 340 of the last 500 Google Play reviews mention crashes during editing. This is worse than search because it's data loss, not just friction.\n\nSEVERITY: 9/10",
  },
  {
    round: 3,
    agent_name: 'First-Timer',
    agent_role: 'first_timer',
    model: 'Llama 70B',
    content: "I'll concede on the '/' commands \u2014 the Daily Driver is right that power users depend on them. But the product team should STILL fix discoverability. 'I really hate to setup things in this tool. There is no drag and drop... it really goes on my nerves.' (Reddit)\n\nThe hidden mobile problem changes my assessment. If I can't trust the app with my data on mobile, that's not friction \u2014 that's a dealbreaker.\n\nUpdated severity \u2014 Onboarding: 6/10 (down from 8). Search: 9/10 (unchanged). Mobile stability: 9/10 (new).\n\nRevised verdict: LEAVE unless mobile is fixed within 90 days.",
  },
  {
    round: 4,
    agent_name: 'Buyer',
    agent_role: 'buyer',
    model: 'Mistral 24B',
    content: "BUY DECISION: YES WITH CONDITIONS\n\nOVERALL SCORE: 64/100\n\nThe First-Timer is right about discoverability, the Daily Driver is right about search being the real killer. Both missed that Notion's pricing at $10/user/month is fair but the free tier is generous enough that most teams never upgrade \u2014 that's a revenue problem, not a user problem.\n\nTOP 3 FIXES:\n1. Rebuild search with semantic indexing \u2014 73% of churn mentions cite findability. ~30% retention impact.\n2. Fix mobile editing crashes \u2014 340 of 500 recent Play Store reviews. ~20% retention impact.\n3. Add progressive onboarding for new users \u2014 current approach loses 60%+ of first-time users. ~15% retention impact.\n\nCOMPETITIVE POSITIONING: Notion's block system is unmatched. But Obsidian is stealing individuals, Linear is stealing engineering teams, and Capacities is stealing note-takers. Fatal gap: Notion is trying to be everything and becoming excellent at nothing.",
  },
]

const DEMO_VERDICT: VerdictData = {
  score: 64,
  decision: 'YES WITH CONDITIONS',
  top_3_fixes: [
    'Rebuild search with semantic indexing \u2014 73% of churn mentions cite findability. ~30% retention impact.',
    'Fix mobile editing crashes \u2014 340 of 500 recent Play Store reviews. ~20% retention impact.',
    'Add progressive onboarding for new users \u2014 current approach loses 60%+ of first-time users. ~15% retention impact.',
  ],
}

const headerChild = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: spring.gentle },
}

const staggerShow = (stagger: number) => ({
  hidden: {},
  show: { transition: { staggerChildren: stagger } },
})

function RoundProgress({ completed, active, total }: { completed: number; active: number; total: number }) {
  return (
    <div style={{ display: 'flex', gap: 4, marginTop: 16 }}>
      {Array.from({ length: total }).map((_, i) => {
        const isFilled = i < completed
        const isActive = i === active - 1 && !isFilled
        const showBlue = isFilled || isActive
        return (
          <div
            key={i}
            style={{
              flex: 1,
              height: 4,
              borderRadius: 2,
              background: '#1E2028',
              overflow: 'hidden',
            }}
          >
            <motion.div
              style={{
                height: 4,
                borderRadius: 2,
                background: '#3B82F6',
                transformOrigin: 'left center',
              }}
              initial={{ scaleX: 0 }}
              animate={{
                scaleX: showBlue ? 1 : 0,
                opacity: isActive ? [1, 0.55, 1] : 1,
              }}
              transition={{
                scaleX: spring.snappy,
                opacity: isActive
                  ? { repeat: Infinity, duration: 2, times: [0, 0.5, 1] }
                  : { duration: 0.15 },
              }}
            />
          </div>
        )
      })}
    </div>
  )
}

function SwarmCard({ product, onComplete }: { product: string; onComplete: () => void }) {
  const [scoutsDeployed, setScoutsDeployed] = useState(0)
  const [results, setResults] = useState<typeof SCOUT_RESULTS>([])
  const [flash, setFlash] = useState(false)
  const completedRef = useRef(false)
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
  }, [product])

  return (
    <motion.div
      initial={fadeUp.initial}
      animate={fadeUp.animate}
      transition={spring.gentle}
      style={{
        background: '#12141A',
        border: `1px solid ${flash ? '#3B82F6' : '#1E2028'}`,
        borderRadius: 8,
        padding: 20,
      }}
    >
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
      <motion.div
        variants={staggerShow(0.05)}
        initial="hidden"
        animate="show"
        style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
      >
        {results.filter(Boolean).map((r, i) => (
          <motion.p
            key={`${r.topic}-${i}`}
            variants={{
              hidden: { opacity: 0, y: 8 },
              show: { opacity: 1, y: 0, transition: spring.gentle },
            }}
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              color: '#71717A',
            }}
          >
            ✓ {r.topic} — {r.count} reviews found
          </motion.p>
        ))}
      </motion.div>
    </motion.div>
  )
}

function AgentInitSequence({ onComplete }: { onComplete: () => void }) {
  const [visibleCards, setVisibleCards] = useState(0)
  const [statuses, setStatuses] = useState<string[]>(['', '', ''])
  const [showLine, setShowLine] = useState(false)
  const [showCommencing, setShowCommencing] = useState(false)
  const onCompleteRef = useRef(onComplete)
  useEffect(() => { onCompleteRef.current = onComplete }, [onComplete])

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = []

    for (let i = 0; i < 3; i++) {
      const base = i * 600
      timers.push(setTimeout(() => setVisibleCards(v => Math.max(v, i + 1)), base))
      timers.push(setTimeout(() => {
        setStatuses(prev => { const n = [...prev]; n[i] = 'initializing'; return n })
      }, base))
      timers.push(setTimeout(() => {
        setStatuses(prev => { const n = [...prev]; n[i] = 'loading context'; return n })
      }, base + 1500))
      timers.push(setTimeout(() => {
        setStatuses(prev => { const n = [...prev]; n[i] = 'ready'; return n })
      }, base + 3000))
    }

    timers.push(setTimeout(() => setShowLine(true), 4800))
    timers.push(setTimeout(() => setShowCommencing(true), 5100))
    timers.push(setTimeout(() => onCompleteRef.current(), 6100))

    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {INIT_AGENTS.map((agent, i) => (
        visibleCards > i && (
          <motion.div
            key={i}
            initial={fadeUp.initial}
            animate={fadeUp.animate}
            transition={spring.gentle}
            style={{
              background: '#12141A',
              border: '1px solid #1E2028',
              borderRadius: 8,
              padding: 20,
              display: 'flex',
              alignItems: 'center',
              gap: 16,
            }}
          >
            <div style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: agent.dotColor,
              animation: 'dotPulse 1.5s ease-in-out infinite',
              flexShrink: 0,
            }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10,
                color: '#71717A',
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
              }}>
                {agent.role}
              </span>
              <span style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 14,
                fontWeight: 600,
                color: '#E4E4E7',
              }}>
                {agent.model}
              </span>
            </div>
            <span style={{ marginLeft: 'auto', flexShrink: 0, minHeight: 14, display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
              <AnimatePresence mode="wait">
                {statuses[i] ? (
                  <motion.span
                    key={statuses[i]}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={spring.gentle}
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10,
                      color: statuses[i] === 'ready' ? '#22C55E' : statuses[i] === 'loading context' ? '#71717A' : '#3F3F46',
                      animation: statuses[i] === 'ready' ? 'readyFlash 300ms ease' : undefined,
                    }}
                  >
                    {statuses[i]}
                  </motion.span>
                ) : null}
              </AnimatePresence>
            </span>
          </motion.div>
        )
      ))}

      {showLine && (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 16 }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: '60%' }}
            transition={spring.snappy}
            style={{ height: 1, background: '#3B82F6' }}
          />
        </div>
      )}

      {showCommencing && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={spring.gentle}
          style={{
            textAlign: 'center',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: '#3B82F6',
            letterSpacing: '0.1em',
            marginTop: 8,
          }}
        >
          Commencing adversarial debate...
        </motion.p>
      )}
    </div>
  )
}

function RoundCard({ msg, typewriter, onTypingComplete }: {
  msg: RoundMessage
  typewriter?: boolean
  onTypingComplete?: () => void
}) {
  const [displayedText, setDisplayedText] = useState(typewriter ? '' : msg.content)
  const [isDone, setIsDone] = useState(!typewriter)
  const dot = ROLE_DOT[msg.agent_role] ?? '#71717A'
  const completedRef = useRef(false)
  const onCompleteRef = useRef(onTypingComplete)
  useEffect(() => { onCompleteRef.current = onTypingComplete }, [onTypingComplete])

  useEffect(() => {
    if (!typewriter) return
    let i = 0
    const interval = setInterval(() => {
      if (i < msg.content.length) {
        i++
        setDisplayedText(msg.content.substring(0, i))
      } else {
        clearInterval(interval)
        setIsDone(true)
        if (!completedRef.current) {
          completedRef.current = true
          onCompleteRef.current?.()
        }
      }
    }, 15)
    return () => clearInterval(interval)
  }, [msg.content, typewriter])

  const hasAgree = /\bAGREE\b/.test(displayedText)
  const hasDisagree = /\bDISAGREE\b/.test(displayedText)

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      transition={spring.default}
      style={{ overflow: 'hidden', borderRadius: 8 }}
    >
      <div style={{
        background: '#12141A',
        border: '1px solid #1E2028',
        borderRadius: 8,
        padding: 24,
      }}>
        <motion.div
          variants={staggerShow(0.03)}
          initial="hidden"
          animate="show"
          style={{ display: 'flex', alignItems: 'center', gap: 12 }}
        >
          <motion.div
            variants={headerChild}
            style={{
              width: 8, height: 8, borderRadius: '50%',
              background: dot, flexShrink: 0,
            }}
          />
          <motion.span
            variants={headerChild}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 14, fontWeight: 600, color: '#E4E4E7',
            }}
          >
            {msg.agent_name}
          </motion.span>
          <motion.span
            variants={headerChild}
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10, color: '#71717A',
              background: '#0A0B0F',
              border: '1px solid #1E2028',
              borderRadius: 4, padding: '2px 8px', flexShrink: 0,
            }}
          >
            {msg.model}
          </motion.span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
            <AnimatePresence>
              {hasAgree && (
                <motion.span
                  key="agree"
                  initial={{ opacity: 0, scale: 0.92 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={spring.snappy}
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10, fontWeight: 600,
                    color: '#22C55E',
                    background: 'rgba(34,197,94,0.1)',
                    borderRadius: 4, padding: '2px 8px',
                  }}
                >
                  AGREE
                </motion.span>
              )}
            </AnimatePresence>
            <AnimatePresence>
              {hasDisagree && (
                <motion.span
                  key="disagree"
                  initial={{ opacity: 0, scale: 0.92 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={spring.snappy}
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10, fontWeight: 600,
                    color: '#EF4444',
                    background: 'rgba(239,68,68,0.1)',
                    borderRadius: 4, padding: '2px 8px',
                  }}
                >
                  DISAGREE
                </motion.span>
              )}
            </AnimatePresence>
            <motion.span
              variants={headerChild}
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10, color: '#3F3F46',
              }}
            >
              ROUND {msg.round}
            </motion.span>
          </div>
        </motion.div>

        <p style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 13, color: '#A1A1AA',
          lineHeight: 1.8, marginTop: 16,
          whiteSpace: 'pre-wrap',
        }}>
          {displayedText}
          {typewriter && !isDone && (
            <motion.span
              animate={{ opacity: [1, 0.45, 1] }}
              transition={{ repeat: Infinity, duration: 1, times: [0, 0.5, 1] }}
            >
              {'\u258C'}
            </motion.span>
          )}
        </p>
      </div>
    </motion.div>
  )
}

export default function DebateStream({ product, sessionId, onBack, onVerdict }: DebateStreamProps) {
  const [swarmDone, setSwarmDone] = useState(false)
  const [initDone, setInitDone] = useState(false)
  const [rounds, setRounds] = useState<RoundMessage[]>([])
  const [currentRound, setCurrentRound] = useState(0)
  const [completedRounds, setCompletedRounds] = useState(0)
  const [wsError, setWsError] = useState('')
  const [demoMode, setDemoMode] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const demoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const roundsRef = useRef<RoundMessage[]>([])
  const demoModeRef = useRef(false)
  const onVerdictRef = useRef(onVerdict)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { roundsRef.current = rounds }, [rounds])
  useEffect(() => { demoModeRef.current = demoMode }, [demoMode])
  useEffect(() => { onVerdictRef.current = onVerdict }, [onVerdict])

  const handleSwarmComplete = useCallback(() => setSwarmDone(true), [])
  const handleInitComplete = useCallback(() => setInitDone(true), [])
  const handleTypingComplete = useCallback(() => setCompletedRounds(prev => prev + 1), [])

  useEffect(() => {
    if (!swarmDone) return

    const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      if (demoModeRef.current) return
      const msg = JSON.parse(event.data)

      if (msg.type === 'verdict') {
        onVerdictRef.current({
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

      if (demoTimerRef.current) {
        clearTimeout(demoTimerRef.current)
        demoTimerRef.current = null
      }

      setRounds(prev => [...prev, msg as RoundMessage])
      setCurrentRound(msg.round)
      setCompletedRounds(prev => prev + 1)
    }

    ws.onerror = () => {
      if (!demoModeRef.current) {
        setWsError('WebSocket connection failed')
      }
    }

    demoTimerRef.current = setTimeout(() => {
      if (roundsRef.current.length === 0) {
        setDemoMode(true)
      }
    }, 8000)

    return () => {
      ws.close()
      if (demoTimerRef.current) clearTimeout(demoTimerRef.current)
    }
  }, [swarmDone, sessionId])

  useEffect(() => {
    if (!demoMode || !initDone) return

    const timers: ReturnType<typeof setTimeout>[] = []
    DEMO_ROUNDS.forEach((round, i) => {
      timers.push(setTimeout(() => {
        setRounds(prev => [...prev, round])
        setCurrentRound(round.round)
      }, i * 4000))
    })

    return () => timers.forEach(clearTimeout)
  }, [demoMode, initDone])

  useEffect(() => {
    if (rounds.length > 0) {
      setTimeout(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
      }, 100)
    }
  }, [rounds.length])

  useEffect(() => {
    if (demoMode && completedRounds >= 4) {
      const timer = setTimeout(() => {
        onVerdictRef.current(DEMO_VERDICT)
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [demoMode, completedRounds])

  useEffect(() => {
    return () => { wsRef.current?.close() }
  }, [])

  return (
    <div style={{ minHeight: '100vh', background: '#0A0B0F' }}>
      <style>{`
        @keyframes dotPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        @keyframes readyFlash {
          0% { opacity: 0; filter: brightness(2); }
          50% { opacity: 1; filter: brightness(1.5); }
          100% { opacity: 1; filter: brightness(1); }
        }
      `}</style>

      <div style={{ maxWidth: 880, margin: '0 auto', padding: '32px 24px 64px' }}>
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

        <RoundProgress completed={completedRounds} active={currentRound} total={4} />

        <div style={{ marginTop: 24 }}>
          <SwarmCard product={product} onComplete={handleSwarmComplete} />
        </div>

        {swarmDone && (
          <div style={{ marginTop: 12 }}>
            <AgentInitSequence onComplete={handleInitComplete} />
          </div>
        )}

        {wsError && !demoMode && initDone && (
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11, color: '#EF4444',
            marginTop: 16,
          }}>
            Error: {wsError}
          </p>
        )}

        {initDone && rounds.length > 0 && (
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {rounds.map((msg, i) => (
              <RoundCard
                key={`${msg.round}-${i}`}
                msg={msg}
                typewriter={demoMode}
                onTypingComplete={demoMode ? handleTypingComplete : undefined}
              />
            ))}
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
