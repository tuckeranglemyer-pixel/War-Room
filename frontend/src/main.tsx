import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Analytics } from '@vercel/analytics/react'
import './index.css'
import App from './App'
import Report from './components/Report'

const reportMatch = window.location.pathname.match(/^\/report\/([^/?#]+)/)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {reportMatch ? <Report sessionId={reportMatch[1]} /> : <App />}
    <Analytics />
  </StrictMode>,
)
