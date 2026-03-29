import { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { fade, fadeScale, fadeUp, spring } from '../animations'

const SUGGESTIONS = ['Canvas', 'Notion', 'Google Calendar', 'Asana', 'Microsoft To Do']

interface LandingProps {
  onSelectProduct: (product: string) => void
}

/**
 * Landing page component with the product search input and suggestion chips.
 *
 * Renders the War Room brand mark, a full-width text input with an animated
 * conic-gradient border on focus, an inline "Analyze" button, and a row of
 * quick-select product suggestions. On submission, plays a 200 ms exit animation
 * before calling ``onSelectProduct`` to advance the view.
 *
 * @param onSelectProduct - Callback receiving the trimmed product name string
 *   when the user submits via Enter, button click, or suggestion chip.
 */
export default function Landing({ onSelectProduct }: LandingProps) {
  const [input, setInput] = useState('')
  const [focused, setFocused] = useState(false)
  const [exiting, setExiting] = useState(false)
  const pendingRef = useRef<string | null>(null)

  /**
   * Initiate exit animation and schedule the ``onSelectProduct`` callback.
   *
   * Guards against double-submission via the ``exiting`` flag and ignores
   * blank or whitespace-only input.
   *
   * @param product - The product name string to pass to the parent.
   */
  function submit(product: string) {
    if (!product.trim() || exiting) return
    pendingRef.current = product.trim()
    setExiting(true)
  }

  /**
   * Submit the current input value when the user presses Enter.
   * @param e - Keyboard event from the product input element.
   */
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
          onSelectProduct(pendingRef.current)
          pendingRef.current = null
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
        Multi-model adversarial QA for software products
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
        style={{ marginTop: 20, textAlign: 'center' }}
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
          fontFamily: "'Inter', sans-serif",
          fontSize: 12,
          fontWeight: 400,
          color: '#71717A',
        }}>
          {SUGGESTIONS.map((s, i) => (
            <span key={s}>
              {i > 0 && <span style={{ margin: '0 6px', color: '#3F3F46' }}> · </span>}
              <motion.span
                onClick={() => submit(s)}
                whileHover={{ y: -1 }}
                transition={spring.snappy}
                style={{
                  cursor: 'pointer',
                  display: 'inline-block',
                  transition: 'color 150ms ease',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = '#E4E4E7' }}
                onMouseLeave={(e) => { e.currentTarget.style.color = '#71717A' }}
              >
                {s}
              </motion.span>
            </span>
          ))}
        </div>
      </motion.div>

      <motion.p
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...spring.gentle, delay: 0.5 }}
        style={{
          marginTop: 64,
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
        transition={{ ...spring.gentle, delay: 0.6 }}
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
        31,668 user reviews · 20 scout agents · 3 AI architectures
      </motion.p>
    </motion.div>
  )
}
