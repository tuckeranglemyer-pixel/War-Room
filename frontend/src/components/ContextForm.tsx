import { useState, useRef, useEffect } from 'react'

interface ContextFormProps {
  productName: string
  onComplete: (sessionId: string) => void
  onBack: () => void
}

const TOTAL_STEPS = 6

const TEXT_STEPS = [
  {
    field: 'teamSize' as const,
    question: 'How big is your team?',
    placeholder: 'e.g. 5 people',
  },
  {
    field: 'currentTools' as const,
    question: 'What tools are you currently using?',
    placeholder: 'e.g. Jira, Slack, Notion',
  },
  {
    field: 'budget' as const,
    question: "What's your budget?",
    placeholder: 'e.g. $20/user/month',
  },
  {
    field: 'mainProblem' as const,
    question: "What's the #1 problem you're trying to solve?",
    placeholder: 'e.g. Too many tools, nothing talks to each other',
  },
  {
    field: 'useCase' as const,
    question: 'What will you use this for?',
    placeholder: 'e.g. Sprint planning, daily standups',
  },
]

type Answers = {
  teamSize: string
  currentTools: string
  budget: string
  mainProblem: string
  useCase: string
}

type SubmitStatus = 'uploading' | 'extracting' | 'analyzing'

export default function ContextForm({ productName, onComplete, onBack }: ContextFormProps) {
  const [step, setStep] = useState(0)
  const [visible, setVisible] = useState(true)
  const [inputFocused, setInputFocused] = useState(false)
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [answers, setAnswers] = useState<Answers>({
    teamSize: '',
    currentTools: '',
    budget: '',
    mainProblem: '',
    useCase: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitStatus, setSubmitStatus] = useState<SubmitStatus>('uploading')
  const [framesAnalyzed, setFramesAnalyzed] = useState(0)
  const [error, setError] = useState('')

  const fileInputRef = useRef<HTMLInputElement>(null)
  const textInputRef = useRef<HTMLInputElement>(null)

  const isVideoStep = step === 0
  const isLastStep = step === TOTAL_STEPS - 1
  const currentTextStep = isVideoStep ? null : TEXT_STEPS[step - 1]

  // Auto-focus the text input after each step transition completes
  useEffect(() => {
    if (visible && step > 0 && !submitting) {
      const t = setTimeout(() => textInputRef.current?.focus(), 160)
      return () => clearTimeout(t)
    }
  }, [step, visible, submitting])

  function transition(nextStep: number) {
    setVisible(false)
    setTimeout(() => {
      setStep(nextStep)
      setVisible(true)
    }, 150)
  }

  function advance() {
    if (step < TOTAL_STEPS - 1) {
      transition(step + 1)
    } else {
      runSubmit()
    }
  }

  function goBack() {
    if (step === 0) {
      onBack()
    } else {
      transition(step - 1)
    }
  }

  function skipStep() {
    if (isVideoStep) {
      setVideoFile(null)
      transition(1)
    } else {
      advance()
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') advance()
  }

  function setAnswer(field: keyof Answers, value: string) {
    setAnswers(prev => ({ ...prev, [field]: value }))
  }

  async function runSubmit() {
    setSubmitting(true)
    setError('')
    try {
      if (videoFile) {
        setSubmitStatus('uploading')
        const formData = new FormData()
        formData.append('video', videoFile)
        formData.append('team_size', answers.teamSize)
        formData.append('current_tools', answers.currentTools)
        formData.append('budget', answers.budget)
        formData.append('main_problem', answers.mainProblem)
        formData.append('use_case', answers.useCase)

        const extractTimer = setTimeout(() => setSubmitStatus('extracting'), 2000)
        const ingestRes = await fetch('http://localhost:8000/api/ingest/video', {
          method: 'POST',
          body: formData,
        })
        clearTimeout(extractTimer)
        if (!ingestRes.ok) throw new Error(`Ingest error ${ingestRes.status}`)
        const { frames_analyzed = 0 } = await ingestRes.json()
        setFramesAnalyzed(frames_analyzed)
      }

      setSubmitStatus('analyzing')
      const analyzeRes = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_description: productName }),
      })
      if (!analyzeRes.ok) throw new Error(`Analyze error ${analyzeRes.status}`)
      const { session_id } = await analyzeRes.json()

      setTimeout(() => onComplete(session_id), 400)
    } catch {
      setError('Could not reach the backend. Is the API running?')
      setSubmitting(false)
    }
  }

  const submitLabel =
    submitStatus === 'uploading'
      ? 'Uploading video...'
      : submitStatus === 'extracting'
      ? `Analyzing video... ${framesAnalyzed} frames processed`
      : 'Starting War Room...'

  // ── Submitting screen ──────────────────────────────────────────────────
  if (submitting) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 24px',
        marginTop: '-5vh',
      }}>
        {error ? (
          <div style={{ textAlign: 'center' }}>
            <p style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              color: '#EF4444',
              marginBottom: 20,
            }}>
              {error}
            </p>
            <button
              onClick={() => { setSubmitting(false); setError('') }}
              style={{
                background: 'transparent',
                border: 'none',
                fontFamily: "'Inter', sans-serif",
                fontSize: 13,
                color: '#52525B',
                cursor: 'pointer',
                transition: 'color 150ms ease',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = '#E4E4E7' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = '#52525B' }}
            >
              ← Try again
            </button>
          </div>
        ) : (
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 14,
            color: '#3B82F6',
            letterSpacing: '0.02em',
          }}>
            {submitLabel}
          </p>
        )}
      </div>
    )
  }

  // ── Wizard screen ──────────────────────────────────────────────────────
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0 24px',
    }}>
      <style>{`
        @keyframes ctxBorderRotate {
          0%   { --ctx-angle: 0deg; }
          100% { --ctx-angle: 360deg; }
        }
        @property --ctx-angle {
          syntax: "<angle>";
          initial-value: 0deg;
          inherits: false;
        }
        .ctx-input-wrap {
          position: relative;
          border-radius: 9px;
          padding: 1px;
          background: #1E2028;
          transition: background 300ms ease;
        }
        .ctx-input-wrap.focused {
          background: conic-gradient(from var(--ctx-angle), #1E2028 0%, #3B82F6 25%, #1E2028 50%, #3B82F6 75%, #1E2028 100%);
          animation: ctxBorderRotate 8s linear infinite;
        }
        .ctx-input-wrap > input {
          display: block;
          width: 100%;
          border-radius: 8px;
        }
        .ctx-upload-zone {
          transition: border-color 200ms ease, background 200ms ease;
          cursor: pointer;
        }
        .ctx-upload-zone:hover {
          border-color: #3B82F6 !important;
          background: #161820 !important;
        }
        .ctx-nav-btn {
          background: transparent;
          border: none;
          font-family: 'Inter', sans-serif;
          font-size: 13px;
          cursor: pointer;
          padding: 0;
          transition: color 150ms ease;
        }
        .ctx-nav-btn:hover {
          color: #E4E4E7 !important;
        }
        .ctx-next-btn {
          transition: background 150ms ease;
        }
        .ctx-next-btn:hover {
          background: #5B9CF7 !important;
        }
      `}</style>

      <div style={{
        width: '100%',
        maxWidth: 560,
        opacity: visible ? 1 : 0,
        transition: 'opacity 150ms ease',
        marginTop: '-5vh',
      }}>
        {/* Question */}
        <p style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 20,
          fontWeight: 400,
          color: '#E4E4E7',
          marginBottom: 24,
          lineHeight: 1.4,
        }}>
          {isVideoStep
            ? `Upload a walkthrough video of ${productName}`
            : currentTextStep!.question}
        </p>

        {/* Input area */}
        {isVideoStep ? (
          <div
            className="ctx-upload-zone"
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={(e) => { e.preventDefault(); setDragOver(false) }}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              const f = e.dataTransfer.files[0]
              if (f?.type.startsWith('video/')) setVideoFile(f)
            }}
            onClick={() => fileInputRef.current?.click()}
            style={{
              background: dragOver ? '#161820' : '#12141A',
              border: `2px dashed ${dragOver ? '#3B82F6' : '#1E2028'}`,
              borderRadius: 8,
              padding: '32px 24px',
              textAlign: 'center',
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/webm,video/quicktime"
              style={{ display: 'none' }}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) setVideoFile(f) }}
            />
            {videoFile ? (
              <>
                <p style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 14,
                  fontWeight: 500,
                  color: '#E4E4E7',
                  marginBottom: 4,
                }}>
                  {videoFile.name}
                </p>
                <p style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                  color: '#52525B',
                }}>
                  {(videoFile.size / (1024 * 1024)).toFixed(1)} MB · click to change
                </p>
              </>
            ) : (
              <>
                <p style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 14,
                  fontWeight: 500,
                  color: '#52525B',
                  marginBottom: 4,
                }}>
                  Drop a screen recording here
                </p>
                <p style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 12,
                  color: '#3F3F46',
                }}>
                  or click to browse · MP4, WebM, MOV
                </p>
              </>
            )}
          </div>
        ) : (
          <div className={`ctx-input-wrap${inputFocused ? ' focused' : ''}`}>
            <input
              ref={textInputRef}
              type="text"
              value={answers[currentTextStep!.field]}
              onChange={(e) => setAnswer(currentTextStep!.field, e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setInputFocused(true)}
              onBlur={() => setInputFocused(false)}
              placeholder={currentTextStep!.placeholder}
              style={{
                background: '#12141A',
                border: 'none',
                padding: '24px 28px',
                fontFamily: "'Inter', sans-serif",
                fontSize: 20,
                fontWeight: 400,
                color: '#E4E4E7',
                caretColor: '#3B82F6',
                outline: 'none',
              }}
            />
          </div>
        )}

        {/* Navigation row */}
        <div style={{
          marginTop: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          {/* Back */}
          <button
            className="ctx-nav-btn"
            onClick={goBack}
            style={{ color: '#52525B' }}
          >
            ← Back
          </button>

          {/* Step counter */}
          <span style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 12,
            color: '#3F3F46',
            userSelect: 'none',
          }}>
            {step + 1} of {TOTAL_STEPS}
          </span>

          {/* Skip + Next / Start */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <button
              className="ctx-nav-btn"
              onClick={skipStep}
              style={{ color: '#52525B' }}
            >
              {isVideoStep ? 'Skip — no video' : 'Skip'}
            </button>

            <button
              className="ctx-next-btn"
              onClick={advance}
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
              }}
            >
              {isLastStep ? 'Start War Room' : 'Next →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
