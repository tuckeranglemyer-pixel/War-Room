interface VerdictCardProps {
  onBack: () => void
}

export default function VerdictCard({ onBack }: VerdictCardProps) {
  return (
    <div
      style={{
        position: 'relative',
        zIndex: 10,
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      <div
        style={{
          maxWidth: 400,
          width: '100%',
          textAlign: 'center',
          padding: '80px 20px',
        }}
      >
        <div style={{ marginBottom: 16 }}>
          <span
            style={{
              fontSize: 200,
              fontWeight: 800,
              color: '#E0FB2D',
              lineHeight: 0.85,
              display: 'block',
            }}
          >
            70
          </span>
          <span
            style={{
              fontSize: 32,
              fontWeight: 300,
              color: 'rgba(255,255,255,0.3)',
            }}
          >
            / 100
          </span>
        </div>

        <p
          style={{
            fontSize: 14,
            color: '#E0FB2D',
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            marginBottom: 32,
          }}
        >
          YES WITH CONDITIONS
        </p>

        <div
          style={{
            textAlign: 'left',
            marginBottom: 48,
          }}
        >
          {[
            'Fix calendar sync — events frequently fail to sync across devices',
            'Add offline mode — app is unusable without network connectivity',
            'Rework notification system — users report alert fatigue',
          ].map((fix, i) => (
            <p
              key={i}
              style={{
                fontSize: 12,
                color: 'rgba(255,255,255,0.7)',
                lineHeight: 1.8,
                borderLeft: '2px solid rgba(224, 251, 45, 0.3)',
                paddingLeft: 12,
                marginBottom: 12,
              }}
            >
              {fix}
            </p>
          ))}
        </div>

        <p
          style={{
            fontSize: 9,
            color: 'rgba(255,255,255,0.2)',
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            marginBottom: 32,
          }}
        >
          ADVERSARIALLY TESTED BY 3 AI ARCHITECTURES
        </p>

        <button
          onClick={onBack}
          style={{
            background: 'transparent',
            border: '1px solid rgba(224, 251, 45, 0.3)',
            color: '#fff',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            textTransform: 'uppercase',
            letterSpacing: '0.2em',
            cursor: 'pointer',
            padding: '12px 24px',
            transition: 'all 0.2s ease',
            borderRadius: 0,
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget
            el.style.borderColor = '#E0FB2D'
            el.style.color = '#E0FB2D'
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget
            el.style.borderColor = 'rgba(224, 251, 45, 0.3)'
            el.style.color = '#fff'
          }}
        >
          ← RUN ANOTHER
        </button>
      </div>
    </div>
  )
}
