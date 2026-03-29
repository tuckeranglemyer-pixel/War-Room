export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'https://war-room-production.up.railway.app'

/** Session id reserved for bundled report JSON — never call the backend (static / Vercel). */
export const STATIC_DEMO_REPORT_SESSION_ID = 'demo'
