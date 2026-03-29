/** Framer Motion spring transition presets. Use ``spring.gentle`` for most UI transitions,
 *  ``spring.snappy`` for micro-interactions, and ``spring.default`` as a neutral baseline. */
export const spring = {
  default: { type: 'spring' as const, stiffness: 300, damping: 30 },
  gentle: { type: 'spring' as const, stiffness: 200, damping: 25 },
  snappy: { type: 'spring' as const, stiffness: 400, damping: 35 },
}

/** Simple opacity fade variant set for Framer Motion ``initial``/``animate``/``exit``. */
export const fade = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
}

/** Opacity + upward-slide variant set; exit slides slightly upward to reinforce directionality. */
export const fadeUp = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -4 },
}

/** Opacity + scale variant set; subtle zoom-in on enter, minimal zoom-out on exit. */
export const fadeScale = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.98 },
}
