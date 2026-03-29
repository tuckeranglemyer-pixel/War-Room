import { useState } from 'react'
import { motion } from 'framer-motion'
import { fade, fadeUp, spring } from '../animations'
import { PRELOADED_PRODUCTS } from '../preloadedProducts'

interface LandingProps {
  onSelectProduct: (product: string) => void
}

/** Landing page — product name input with animated background. Entry point for War Room analysis. */
export default function Landing({ onSelectProduct }: LandingProps) {
  const [exiting, setExiting] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)

  function submit(product: string) {
    if (exiting) return
    setSelected(product)
    setExiting(true)
  }

  return (
    <motion.div
      animate={exiting ? { opacity: 0, y: -8 } : { opacity: 1, y: 0 }}
      transition={exiting ? { duration: 0.2 } : undefined}
      onAnimationComplete={() => {
        if (exiting && selected) {
          onSelectProduct(selected)
          setSelected(null)
        }
      }}
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        padding: '0 24px',
        marginTop: '-5vh',
      }}
    >
      <style>{`
        @keyframes finePrintPulse {
          0%, 100% { opacity: 0.15; }
          50%      { opacity: 0.3; }
        }
      `}</style>

      <motion.p
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...spring.gentle, delay: 0 }}
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 16,
          fontWeight: 600,
          letterSpacing: '0.25em',
          textTransform: 'uppercase',
          color: '#52525B',
          marginBottom: 12,
        }}
      >
        WAR ROOM
      </motion.p>

      <motion.p
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...spring.gentle, delay: 0.1 }}
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 14,
          fontWeight: 400,
          color: '#3F3F46',
          marginBottom: 32,
        }}
      >
        What 31,668 real users think about your favorite app
      </motion.p>

      <motion.p
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...spring.gentle, delay: 0.2 }}
        style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 12,
          fontWeight: 400,
          color: '#3F3F46',
          marginBottom: 16,
          textAlign: 'center',
        }}
      >
        Choose a product to analyze
      </motion.p>

      <motion.div
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...spring.gentle, delay: 0.3 }}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 8,
          width: '100%',
          maxWidth: 560,
        }}
      >
        {PRELOADED_PRODUCTS.map((product) => (
          <motion.button
            key={product}
            onClick={() => submit(product)}
            whileHover={{ y: -1 }}
            transition={spring.snappy}
            style={{
              background: '#12141A',
              border: '1px solid #1E2028',
              borderRadius: 8,
              padding: '12px 8px',
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              fontWeight: 400,
              color: '#A1A1AA',
              cursor: 'pointer',
              transition: 'border-color 200ms ease, color 200ms ease, background 200ms ease',
              textAlign: 'center',
              lineHeight: 1.3,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#3B82F6'
              e.currentTarget.style.color = '#E4E4E7'
              e.currentTarget.style.background = '#16181F'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = '#1E2028'
              e.currentTarget.style.color = '#A1A1AA'
              e.currentTarget.style.background = '#12141A'
            }}
          >
            {product}
          </motion.button>
        ))}
      </motion.div>

      <motion.p
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...spring.gentle, delay: 0.5 }}
        style={{
          marginTop: 48,
          textAlign: 'center',
          fontFamily: "'Inter', sans-serif",
          fontSize: 13,
          fontWeight: 500,
          letterSpacing: '0.02em',
          color: '#52525B',
        }}
      >
        $200K in consulting. 4 minutes. Real evidence.
      </motion.p>

      <motion.p
        initial={fade.initial}
        animate={fade.animate}
        transition={{ ...spring.gentle, delay: 0.8 }}
        style={{
          position: 'absolute',
          bottom: 32,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          color: '#3F3F46',
          textAlign: 'center',
          animation: 'finePrintPulse 4s ease-in-out infinite',
        }}
      >
        31,668 evidence chunks · 20 scout agents · 3 debate personas · 2 LLM backends
      </motion.p>
    </motion.div>
  )
}
