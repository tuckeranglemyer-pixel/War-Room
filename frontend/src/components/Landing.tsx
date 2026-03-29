import { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { fade, fadeScale, fadeUp, spring } from '../animations'
import { PRELOADED_PRODUCTS } from '../preloadedProducts'

interface LandingProps {
  onSelectProduct: (product: string) => void
  onFeaturedProduct: (product: string) => void
}

/** Landing page — product name input with animated background. Entry point for War Room analysis. */
export default function Landing({ onSelectProduct, onFeaturedProduct }: LandingProps) {
  const [input, setInput] = useState('')
  const [focused, setFocused] = useState(false)
  const [exiting, setExiting] = useState(false)
  const pendingRef = useRef<string | null>(null)
  const isFeaturedRef = useRef(false)

  function submit(product: string) {
    if (!product.trim() || exiting) return
    pendingRef.current = product.trim()
    isFeaturedRef.current = false
    setExiting(true)
  }

  function submitFeatured(product: string) {
    if (!product.trim() || exiting) return
    pendingRef.current = product.trim()
    isFeaturedRef.current = true
    setExiting(true)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') submit(input)
  }

  const hasText = input.trim().length > 0

  return (
    <motion.div
      animate={exiting ? { opacity: 0, y: -8 } : { opacity: 1, y: 0 }}
      transition={exiting ? { duration: 0.2 } : undefined}
      onAnimationComplete={() => {
        if (exiting && pendingRef.current) {
          const name = pendingRef.current
          pendingRef.current = null
          if (isFeaturedRef.current) {
            isFeaturedRef.current = false
            onFeaturedProduct(name)
          } else {
            onSelectProduct(name)
          }
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
          marginBottom: 40,
        }}
      >
        What 31,668 real users think about your favorite app
      </motion.p>

      <div style={{ width: '100%', maxWidth: 560 }}>
        <motion.div
          initial={fadeScale.initial}
          animate={{
            ...fadeScale.animate,
            scale: focused ? 1.005 : 1,
          }}
          transition={focused ? spring.default : { ...spring.gentle, delay: 0.2 }}
        >
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
        </motion.div>
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

      <motion.div
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...spring.gentle, delay: 0.4 }}
        style={{ marginTop: 20, textAlign: 'center', width: '100%', maxWidth: 640 }}
      >
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
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: 8,
        }}>
          {PRELOADED_PRODUCTS.map((s) => (
            <motion.button
              key={s}
              onClick={() => submitFeatured(s)}
              whileHover={{ y: -1 }}
              transition={spring.snappy}
              style={{
                background: '#12141A',
                border: '1px solid #1E2028',
                borderRadius: 100,
                padding: '7px 16px',
                fontFamily: "'Inter', sans-serif",
                fontSize: 13,
                fontWeight: 400,
                color: '#A1A1AA',
                cursor: 'pointer',
                transition: 'border-color 200ms ease, color 200ms ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#3B82F6'
                e.currentTarget.style.color = '#E4E4E7'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#1E2028'
                e.currentTarget.style.color = '#A1A1AA'
              }}
            >
              {s}
            </motion.button>
          ))}
        </div>
        <p style={{
          marginTop: 14,
          fontFamily: "'Inter', sans-serif",
          fontSize: 11,
          fontWeight: 400,
          color: '#3F3F46',
          lineHeight: 1.5,
        }}>
          Type any product above — featured products include 31,668 real user reviews for deeper analysis
        </p>
      </motion.div>

      <motion.p
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...spring.gentle, delay: 0.6 }}
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
