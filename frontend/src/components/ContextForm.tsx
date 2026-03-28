import { useState, useRef } from 'react'

interface ContextFormProps {
  productName: string
  onComplete: (sessionId: string) => void
  onBack: () => void
}

type ProgressStep = '' | 'uploading' | 'extracting' | 'analyzing' | 'done' | 'skipping'

export default function ContextForm({ productName, onComplete, onBack }: ContextFormProps) {
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [teamSize, setTeamSize] = useState('')
  const [currentTools, setCurrentTools] = useState('')
  const [budget, setBudget] = useState('')
  const [mainProblem, setMainProblem] = useState('')
  const [useCase, setUseCase] = useState('')
  const [progress, setProgress] = useState<ProgressStep>('')
  const [framesAnalyzed, setFramesAnalyzed] = useState(0)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const busy = progress !== ''

  const progressLabel =
    progress === 'done'
      ? `Done! ${framesAnalyzed} frames analyzed`
      : progress === 'uploading'
      ? 'Uploading video...'
      : progress === 'extracting'
      ? 'Extracting frames...'
      : progress === 'analyzing'
      ? 'Analyzing with GPT-4o...'
      : progress === 'skipping'
      ? 'Starting analysis...'
      : ''

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(true)
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('video/')) setVideoFile(file)
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) setVideoFile(file)
  }

  async function handleStart() {
    if (busy) return
    setError('')

    try {
      if (videoFile) {
        setProgress('uploading')
        const formData = new FormData()
        formData.append('video', videoFile)
        formData.append('team_size', teamSize)
        formData.append('current_tools', currentTools)
        formData.append('budget', budget)
        formData.append('main_problem', mainProblem)
        formData.append('use_case', useCase)

        const extractTimer = setTimeout(() => setProgress('extracting'), 2000)

        const ingestRes = await fetch('http://localhost:8000/api/ingest/video', {
          method: 'POST',
          body: formData,
        })
        clearTimeout(extractTimer)

        if (!ingestRes.ok) throw new Error(`Ingest error ${ingestRes.status}`)
        const ingestData = await ingestRes.json()
        setFramesAnalyzed(ingestData.frames_analyzed ?? 0)
      }

      setProgress('analyzing')
      const analyzeRes = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_description: productName }),
      })
      if (!analyzeRes.ok) throw new Error(`Analyze error ${analyzeRes.status}`)
      const { session_id } = await analyzeRes.json()

      setProgress('done')
      setTimeout(() => onComplete(session_id), 800)
    } catch {
      setError('Could not reach the backend. Is the API running?')
      setProgress('')
    }
  }

  async function handleSkip() {
    if (busy) return
    setError('')
    setProgress('skipping')
    try {
      const res = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_description: productName }),
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const { session_id } = await res.json()
      onComplete(session_id)
    } catch {
      setError('Could not reach the backend. Is the API running?')
      setProgress('')
    }
  }

  const fields = [
    { key: 'teamSize', value: teamSize, setter: setTeamSize, placeholder: 'e.g. 5' },
    { key: 'currentTools', value: currentTools, setter: setCurrentTools, placeholder: 'e.g. Jira, Slack' },
    { key: 'budget', value: budget, setter: setBudget, placeholder: 'e.g. $20/user/month' },
    { key: 'mainProblem', value: mainProblem, setter: setMainProblem, placeholder: 'e.g. Too many tools, nothing talks to each other' },
    { key: 'useCase', value: useCase, setter: setUseCase, placeholder: 'e.g. Sprint planning, task tracking' },
  ] as const

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '48px 24px 60px',
    }}>
      <style>{`
        .ctx-input {
          width: 100%;
          background: #12141A;
          border: 1px solid #1E2028;
          border-radius: 6px;
          padding: 12px 16px;
          font-family: 'Inter', sans-serif;
          font-size: 14px;
          color: #E4E4E7;
          box-sizing: border-box;
          transition: border-color 150ms ease;
          outline: none;
        }
        .ctx-input:focus {
          border-color: #3B82F6;
        }
        .ctx-input::placeholder {
          color: #3F3F46;
        }
        .ctx-input:disabled {
          opacity: 0.5;
          cursor: default;
        }
        .ctx-upload {
          transition: border-color 200ms ease, background 200ms ease;
        }
        .ctx-back-btn:hover {
          color: #71717A !important;
        }
        .ctx-skip-btn:hover {
          color: #71717A !important;
        }
        .ctx-start-btn:hover:not(:disabled) {
          background: #5B9CF7 !important;
        }
      `}</style>

      <div style={{ width: '100%', maxWidth: 560 }}>
        {/* Back */}
        <button
          className="ctx-back-btn"
          onClick={onBack}
          disabled={busy}
          style={{
            background: 'transparent',
            border: 'none',
            fontFamily: "'Inter', sans-serif",
            fontSize: 13,
            color: '#52525B',
            cursor: busy ? 'default' : 'pointer',
            padding: 0,
            marginBottom: 40,
            display: 'block',
          }}
        >
          ← Back
        </button>

        {/* Product name header */}
        <div style={{ marginBottom: 32 }}>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 11,
            fontWeight: 500,
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            color: '#3B82F6',
            marginBottom: 8,
          }}>
            Analyzing
          </p>
          <p style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 22,
            fontWeight: 600,
            color: '#E4E4E7',
          }}>
            {productName}
          </p>
        </div>

        {/* Video upload */}
        <div
          className="ctx-upload"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !busy && fileInputRef.current?.click()}
          style={{
            background: dragOver ? '#161820' : '#12141A',
            border: `2px dashed ${dragOver ? '#3B82F6' : '#1E2028'}`,
            borderRadius: 8,
            padding: '28px 24px',
            textAlign: 'center',
            cursor: busy ? 'default' : 'pointer',
            marginBottom: 20,
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/webm,video/quicktime"
            style={{ display: 'none' }}
            onChange={handleFileChange}
            disabled={busy}
          />
          {videoFile ? (
            <div>
              <p style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 13,
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
            </div>
          ) : (
            <div>
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
            </div>
          )}
        </div>

        {/* Context fields */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }}>
          {fields.map(({ key, value, setter, placeholder }) => (
            <input
              key={key}
              className="ctx-input"
              type="text"
              value={value}
              onChange={(e) => setter(e.target.value)}
              placeholder={placeholder}
              disabled={busy}
            />
          ))}
        </div>

        {/* Error */}
        {error && (
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: '#EF4444',
            marginBottom: 16,
            textAlign: 'center',
          }}>
            {error}
          </p>
        )}

        {/* Progress */}
        {progressLabel && (
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
            color: progress === 'done' ? '#22C55E' : '#3B82F6',
            marginBottom: 16,
            textAlign: 'center',
          }}>
            {progressLabel}
          </p>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <button
            className="ctx-skip-btn"
            onClick={handleSkip}
            disabled={busy}
            style={{
              background: 'transparent',
              border: 'none',
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              color: '#52525B',
              cursor: busy ? 'default' : 'pointer',
              padding: 0,
              textDecoration: 'underline',
              textDecorationColor: '#3F3F46',
            }}
          >
            Skip — text only
          </button>

          <button
            className="ctx-start-btn"
            onClick={handleStart}
            disabled={busy}
            style={{
              background: busy ? '#1A1C24' : '#3B82F6',
              border: '1px solid',
              borderColor: busy ? '#1E2028' : 'transparent',
              borderRadius: 6,
              padding: '12px 28px',
              fontFamily: "'Inter', sans-serif",
              fontSize: 14,
              fontWeight: 500,
              color: busy ? '#3F3F46' : '#fff',
              cursor: busy ? 'default' : 'pointer',
              transition: 'background 150ms ease',
            }}
          >
            Start Analysis
          </button>
        </div>
      </div>

      <p style={{
        marginTop: 64,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
        color: '#3F3F46',
        textAlign: 'center',
      }}>
        Video is processed locally · frames are never stored
      </p>
    </div>
  )
}
