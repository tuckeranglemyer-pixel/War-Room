interface DebateStreamProps {
  product: string
  onBack: () => void
}

export default function DebateStream({ product, onBack }: DebateStreamProps) {
  return (
    <div
      style={{
        position: 'relative',
        zIndex: 10,
        minHeight: '100vh',
        background: '#000',
        padding: '40px 40px',
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      <button
        onClick={onBack}
        style={{
          background: 'transparent',
          border: 'none',
          color: 'rgba(255,255,255,0.4)',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          textTransform: 'uppercase',
          letterSpacing: '0.2em',
          cursor: 'pointer',
          padding: 0,
          marginBottom: 40,
          transition: 'color 0.2s ease',
          borderRadius: 0,
        }}
        onMouseEnter={(e) => { e.currentTarget.style.color = '#E0FB2D' }}
        onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.4)' }}
      >
        ← BACK
      </button>

      <div style={{ marginBottom: 32 }}>
        <p
          style={{
            fontSize: 10,
            color: 'rgba(255,255,255,0.3)',
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            marginBottom: 8,
          }}
        >
          ANALYZING
        </p>
        <p
          style={{
            fontSize: 14,
            color: '#E0FB2D',
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
          }}
        >
          {product}
        </p>
      </div>

      <div
        style={{
          width: '100%',
          height: 1,
          background: 'rgba(224, 251, 45, 0.2)',
          marginBottom: 32,
        }}
      />

      <p
        style={{
          fontSize: 14,
          color: '#E0FB2D',
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
          marginBottom: 24,
        }}
      >
        ROUND 1 — INITIAL ANALYSIS
      </p>

      <p
        style={{
          fontSize: 12,
          color: 'rgba(255,255,255,0.3)',
          lineHeight: 1.8,
        }}
      >
        Debate streaming will connect to WebSocket at ws://localhost:8000/ws/
      </p>
    </div>
  )
}
