export const spring = {
  default: { type: 'spring' as const, stiffness: 300, damping: 30 },
  gentle: { type: 'spring' as const, stiffness: 200, damping: 25 },
  snappy: { type: 'spring' as const, stiffness: 400, damping: 35 },
}

export const fade = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
}

export const fadeUp = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -4 },
}

export const fadeScale = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.98 },
}
