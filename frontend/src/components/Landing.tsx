import { useState } from 'react'

const SUGGESTIONS = ['Canvas', 'Notion', 'Google Calendar', 'Asana', 'Microsoft To Do']

interface LandingProps {
  onSelectProduct: (product: string) => void
}

export default function Landing({ onSelectProduct }: LandingProps) {
  const [input, setInput] = useState('')
  const [focused, setFocused] = useState(false)

  function submit(product: string) {
    if (!product.trim()) return
    onSelectProduct(product.trim())
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') submit(input)
  }

  const hasText = input.trim().length > 0

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      padding: '0 24px',
      marginTop: '-5vh',
    }}>
      <style>{`
        @keyframes borderRotate {
          0%   { --angle: 0deg; }
          100% { --angle: 360deg; }
        }
        @keyframes finePrintPulse {
          0%, 100% { opacity: 0.15; }
          50%      { opacity: 0.3; }
        }
        @property --angle {
          syntax: "<angle>";
          initial-value: 0deg;
          inherits: false;
        }
        .input-border-wrap {
          position: relative;
          border-radius: 9px;
          padding: 1px;
          background: #1E2028;
          transition: background 300ms ease;
        }
        .input-border-wrap.active {
          background: conic-gradient(from var(--angle), #1E2028 0%, #3B82F6 25%, #1E2028 50%, #3B82F6 75%, #1E2028 100%);
          animation: borderRotate 8s linear infinite;
        }
        .input-border-wrap > input {
          display: block;
          width: 100%;
          border-radius: 8px;
        }
      `}</style>

      {/* Brand mark */}
      <p style={{
        fontFamily: "'Inter', sans-serif",
        fontSize: 16,
        fontWeight: 600,
        letterSpacing: '0.25em',
        textTransform: 'uppercase',
        color: '#52525B',
        marginBottom: 12,
      }}>
        WAR ROOM
      </p>

      {/* Tagline */}
      <p style={{
        fontFamily: "'Inter', sans-serif",
        fontSize: 14,
        fontWeight: 400,
        color: '#3F3F46',
        marginBottom: 40,
      }}>
        Multi-model adversarial QA for software products
      </p>

      {/* Input with animated gradient border */}
      <div style={{ width: '100%', maxWidth: 560 }}>
        <div className={`input-border-wrap${focused ? ' active' : ''}`}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="Enter a product to analyze..."
            autoFocus
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
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          marginTop: 8,
          minHeight: 28,
        }}>
          <button
            onClick={() => submit(input)}
            style={{
              background: 'transparent',
              border: 'none',
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              fontWeight: 500,
              color: '#3B82F6',
              cursor: hasText ? 'pointer' : 'default',
              padding: '4px 0',
              opacity: hasText ? 1 : 0,
              transition: 'opacity 200ms ease, color 150ms ease',
            }}
            onMouseEnter={(e) => { if (hasText) e.currentTarget.style.color = '#5B9CF7' }}
            onMouseLeave={(e) => { e.currentTarget.style.color = '#3B82F6' }}
          >
            Analyze
          </button>
        </div>
      </div>

      {/* Quiet suggestions — tightened to input */}
      <div style={{ marginTop: 20, textAlign: 'center' }}>
        <p style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 12,
          fontWeight: 400,
          color: '#3F3F46',
          marginBottom: 12,
        }}>
          or try one of these
        </p>
        <div style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 12,
          fontWeight: 400,
          color: '#71717A',
        }}>
          {SUGGESTIONS.map((s, i) => (
            <span key={s}>
              {i > 0 && <span style={{ margin: '0 6px', color: '#3F3F46' }}> · </span>}
              <span
                onClick={() => submit(s)}
                style={{
                  cursor: 'pointer',
                  transition: 'color 150ms ease',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = '#E4E4E7' }}
                onMouseLeave={(e) => { e.currentTarget.style.color = '#71717A' }}
              >
                {s}
              </span>
            </span>
          ))}
        </div>
      </div>

      <p style={{
        marginTop: 64,
        textAlign: 'center',
        fontFamily: "'Inter', sans-serif",
        fontSize: 13,
        fontWeight: 500,
        letterSpacing: '0.02em',
        color: '#52525B',
      }}>
        $200K in consulting. 4 minutes. Real evidence.
      </p>

      {/* Fine print — breathing pulse on the numbers */}
      <p style={{
        position: 'absolute',
        bottom: 32,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
        color: '#3F3F46',
        textAlign: 'center',
        animation: 'finePrintPulse 4s ease-in-out infinite',
      }}>
        31,668 user reviews · 20 scout agents · 3 AI architectures
      </p>
    </div>
  )
}
