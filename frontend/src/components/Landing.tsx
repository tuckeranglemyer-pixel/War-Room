import { useState } from 'react'

const PRODUCTS = ['CANVAS', 'NOTION', 'GOOGLE CALENDAR', 'ASANA', 'MICROSOFT TO DO']

interface LandingProps {
  onSelectProduct: (product: string) => void
}

export default function Landing({ onSelectProduct }: LandingProps) {
  const [customInput, setCustomInput] = useState('')

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && customInput.trim()) {
      onSelectProduct(customInput.trim())
    }
  }

  return (
    <div
      style={{
        position: 'relative',
        zIndex: 10,
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
      }}
    >
      {/* Hero title */}
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <h1
          style={{
            fontSize: 'clamp(48px, 10vw, 120px)',
            fontWeight: 800,
            color: '#E0FB2D',
            letterSpacing: '0.15em',
            lineHeight: 0.85,
            textTransform: 'uppercase',
            fontFamily: "'JetBrains Mono', monospace",
            textShadow: '0 0 80px rgba(224, 251, 45, 0.3)',
            margin: 0,
          }}
        >
          THE WAR
          <br />
          ROOM
        </h1>
        <p
          style={{
            fontSize: 'clamp(11px, 1.2vw, 16px)',
            color: 'rgba(255,255,255,0.5)',
            letterSpacing: '0.3em',
            fontWeight: 300,
            textTransform: 'uppercase',
            fontFamily: "'JetBrains Mono', monospace",
            marginTop: 16,
          }}
        >
          3 AI ARCHITECTURES. 4 ROUNDS OF DEBATE. REAL EVIDENCE. ONE VERDICT.
        </p>
      </div>

      {/* Separator */}
      <div
        style={{
          width: '60%',
          height: 1,
          background: 'rgba(224, 251, 45, 0.2)',
          marginBottom: 32,
        }}
      />

      {/* Product section */}
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <p
          style={{
            fontSize: 10,
            color: '#E0FB2D',
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            fontFamily: "'JetBrains Mono', monospace",
            marginBottom: 16,
          }}
        >
          PICK A PRODUCT
        </p>
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 12,
            justifyContent: 'center',
          }}
        >
          {PRODUCTS.map((product) => (
            <button
              key={product}
              onClick={() => onSelectProduct(product)}
              style={{
                border: '1px solid rgba(224, 251, 45, 0.3)',
                background: 'transparent',
                padding: '12px 24px',
                color: '#fff',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 12,
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                borderRadius: 0,
              }}
              onMouseEnter={(e) => {
                const el = e.currentTarget
                el.style.borderColor = '#E0FB2D'
                el.style.color = '#E0FB2D'
                el.style.background = 'rgba(224, 251, 45, 0.05)'
              }}
              onMouseLeave={(e) => {
                const el = e.currentTarget
                el.style.borderColor = 'rgba(224, 251, 45, 0.3)'
                el.style.color = '#fff'
                el.style.background = 'transparent'
              }}
              onMouseDown={(e) => {
                e.currentTarget.style.background = 'rgba(224, 251, 45, 0.15)'
              }}
              onMouseUp={(e) => {
                e.currentTarget.style.background = 'rgba(224, 251, 45, 0.05)'
              }}
            >
              {product}
            </button>
          ))}
        </div>
      </div>

      {/* Custom input */}
      <div style={{ textAlign: 'center', marginBottom: 80 }}>
        <p
          style={{
            fontSize: 10,
            color: 'rgba(255,255,255,0.4)',
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            fontFamily: "'JetBrains Mono', monospace",
            marginBottom: 12,
          }}
        >
          OR ANALYZE YOUR OWN →
        </p>
        <input
          type="text"
          value={customInput}
          onChange={(e) => setCustomInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder=""
          style={{
            background: 'transparent',
            border: 'none',
            borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
            outline: 'none',
            color: '#fff',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 14,
            width: '100%',
            maxWidth: 400,
            padding: '8px 0',
            caretColor: '#E0FB2D',
            transition: 'border-color 0.2s ease',
            borderRadius: 0,
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderBottomColor = '#E0FB2D'
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderBottomColor = 'rgba(255, 255, 255, 0.2)'
          }}
        />
      </div>

      {/* Footer */}
      <div
        style={{
          position: 'absolute',
          bottom: 30,
          left: 0,
          right: 0,
          textAlign: 'center',
        }}
      >
        <p
          style={{
            fontSize: 9,
            color: 'rgba(255, 255, 255, 0.2)',
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            fontFamily: "'JetBrains Mono', monospace",
            marginBottom: 8,
          }}
        >
          POWERED BY NVIDIA DGX SPARK · CREWAI · CHROMADB
        </p>
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            gap: 4,
          }}
        >
          <div style={{ width: 6, height: 6, background: '#E0FB2D' }} />
          <div style={{ width: 6, height: 6, background: '#FFFFFF' }} />
          <div style={{ width: 6, height: 6, background: '#00D4FF' }} />
        </div>
      </div>
    </div>
  )
}
