import { useState } from 'react'

const SUGGESTIONS = ['Canvas', 'Notion', 'Google Calendar', 'Asana', 'Microsoft To Do']

interface LandingProps {
  onSelectProduct: (product: string) => void
}

export default function Landing({ onSelectProduct }: LandingProps) {
  const [input, setInput] = useState('')

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && input.trim()) {
      onSelectProduct(input.trim())
    }
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
    }}>
      {/* Brand mark */}
      <p style={{
        fontFamily: "'Inter', sans-serif",
        fontSize: 13,
        fontWeight: 600,
        letterSpacing: '0.15em',
        textTransform: 'uppercase',
        color: '#3F3F46',
        marginBottom: 48,
      }}>
        WAR ROOM
      </p>

      {/* The input — the entire interaction */}
      <div style={{ width: '100%', maxWidth: 560 }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a product to analyze..."
          autoFocus
          style={{
            width: '100%',
            background: '#12141A',
            border: '1px solid #1E2028',
            borderRadius: 8,
            padding: '20px 24px',
            fontFamily: "'Inter', sans-serif",
            fontSize: 18,
            fontWeight: 400,
            color: '#E4E4E7',
            caretColor: '#3B82F6',
            outline: 'none',
            transition: 'border-color 150ms ease',
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = '#2A2D38' }}
          onBlur={(e) => { e.currentTarget.style.borderColor = '#1E2028' }}
        />
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          marginTop: 8,
          minHeight: 28,
        }}>
          <button
            onClick={() => { if (hasText) onSelectProduct(input.trim()) }}
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

      {/* Quiet suggestions */}
      <div style={{ marginTop: 32, textAlign: 'center' }}>
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
                onClick={() => onSelectProduct(s)}
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

      {/* Fine print */}
      <p style={{
        position: 'absolute',
        bottom: 32,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
        color: '#3F3F46',
        textAlign: 'center',
      }}>
        31,668 user reviews · 20 scout agents · 3 AI architectures
      </p>
    </div>
  )
}
