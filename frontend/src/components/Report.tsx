import { useState, useEffect, useRef, useCallback } from 'react'
import './Report.css'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'https://paplike-hillary-beauteously.ngrok-free.dev'

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
type Impact = 'LOW' | 'MEDIUM' | 'HIGH' | 'TRANSFORMATIVE'
type MarketReadiness = 'NOT_READY' | 'NEEDS_WORK' | 'COMPETITIVE' | 'STRONG' | 'EXCEPTIONAL'
type ComparisonVerdict = 'USER_BETTER' | 'COMPETITOR_BETTER' | 'COMPARABLE'
type FrictionSeverity = 'MINOR' | 'MODERATE' | 'MAJOR' | 'BLOCKER'
type FixEffort = 'QUICK_WIN' | 'MODERATE' | 'SIGNIFICANT_REWORK'
type Sentiment = 'NEGATIVE' | 'MIXED' | 'NEUTRAL' | 'POSITIVE' | 'VERY_POSITIVE'
type FirstActionClarity = 'OBVIOUS' | 'FINDABLE' | 'BURIED' | 'MISSING'
type CognitiveLoad = 'LOW' | 'MODERATE' | 'HIGH' | 'OVERWHELMING'
type Confidence = 'LOW' | 'MEDIUM' | 'HIGH'
type QuoteSource = 'reddit' | 'hackernews' | 'google_play'

interface ScreenData {
  frame_number?: number
  image_path: string
  image_url?: string
  screen_label: string
  ux_score: number
  strengths: string[]
  weaknesses: string[]
}

interface CompetitorScreenData {
  app: string
  filename: string
  image_path: string
  image_url?: string
  screen_label: string
  ux_score: number
  strengths: string[]
  weaknesses: string[]
}

interface ComparisonCard {
  card_id: string
  user_screen: ScreenData
  competitor_screen: CompetitorScreenData
  similarity_score: number
  comparison_verdict: ComparisonVerdict
  what_to_steal: string
  what_to_avoid: string
}

type ExecutionMode = 'dgx' | 'cloud'

interface ExecutionLogEntry {
  round: string
  mode: ExecutionMode
  model: string
  elapsed_seconds: number
  status: string
  gpu_temp_before?: number
  tier?: number
}

interface ExecutionMetadata {
  mode: ExecutionMode
  model: string
  max_context_chars?: number
  execution_log?: ExecutionLogEntry[]
  tier?: number
  thermal_ceiling_c?: number
  thermal_resume_c?: number
  cooldown_seconds?: number
}

interface ReportData {
  product_name: string
  product_description: string
  target_user: string
  analysis_timestamp: string
  execution_metadata?: ExecutionMetadata
  verdict: {
    headline: string
    score: number
    recommendation: string
    market_readiness: MarketReadiness
  }
  strategist_section: {
    competitive_positioning: string
    top_risks: Array<{ risk: string; severity: Severity; evidence: string; competitor_learned_from: string }>
    top_opportunities: Array<{ opportunity: string; impact: Impact; evidence: string; competitor_failed_at: string }>
    moat_assessment: string
    strategist_score: number
    strategist_summary: string
  }
  ux_analyst_section: {
    comparison_cards: ComparisonCard[]
    onboarding_assessment: {
      score: number
      time_to_value_estimate: string
      first_action_clarity: FirstActionClarity
      cognitive_load: CognitiveLoad
      recommendation: string
    }
    friction_map: Array<{ screen: string; friction_point: string; severity: FrictionSeverity; fix_effort: FixEffort }>
    ux_analyst_score: number
    ux_analyst_summary: string
  }
  market_researcher_section: {
    sentiment_analysis: {
      overall_sentiment: Sentiment
      sentiment_by_competitor: Array<{ app: string; sentiment: string; sample_size: number; top_praise: string; top_complaint: string }>
    }
    killer_quotes: Array<{ quote: string; source: QuoteSource; app: string; relevance: string }>
    pricing_positioning: { competitor_range: string; sweet_spot: string; pricing_insight: string }
    adoption_signals: { easy_wins: string[]; dealbreakers: string[] }
    market_researcher_score: number
    market_researcher_summary: string
  }
  challenge_layer: {
    contradictions_found: Array<{ between: string; issue: string; resolution: string }>
    blind_spots: string[]
    final_verdict: string
    final_score: number
    confidence: Confidence
    one_thing_to_do_monday: string
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Mock Data
// ─────────────────────────────────────────────────────────────────────────────

const MOCK_DATA: ReportData = {
  product_name: 'Notion',
  product_description: 'All-in-one workspace for notes, docs, databases, and project management',
  target_user: 'Knowledge workers, startup teams, solopreneurs',
  analysis_timestamp: '2026-03-29T10:00:00Z',
  execution_metadata: {
    mode: 'cloud',
    model: 'gpt-4o',
    execution_log: [
      { round: 'Strategist', mode: 'cloud', model: 'gpt-4o', elapsed_seconds: 18.4, status: 'OK' },
      { round: 'UX Analyst', mode: 'cloud', model: 'gpt-4o', elapsed_seconds: 21.1, status: 'OK' },
      { round: 'Market Researcher', mode: 'cloud', model: 'gpt-4o', elapsed_seconds: 19.7, status: 'OK' },
      { round: 'Partner Review', mode: 'cloud', model: 'gpt-4o', elapsed_seconds: 11.2, status: 'OK' },
    ],
  },
  verdict: {
    headline: 'Strong product, fragile onboarding wall blocking mass adoption',
    score: 7.1,
    recommendation: "Notion's flexible architecture creates durable competitive moats, but the steep learning curve is ceding the SMB segment to Notion-lite competitors. Prioritize onboarding redesign and mobile performance before attempting enterprise expansion.",
    market_readiness: 'COMPETITIVE',
  },
  strategist_section: {
    competitive_positioning:
      "Notion occupies a unique horizontal position between note-taking apps and full project management suites. Its block-based architecture creates high switching costs once teams build their workflows, but this same flexibility creates a 'blank canvas paralysis' that competitors like Linear and Coda are actively exploiting.",
    top_risks: [
      {
        risk: 'Mobile experience significantly lags desktop, creating churn in mobile-first markets',
        severity: 'HIGH',
        evidence: '22 of 50 recent Play Store reviews cite crashes or performance issues on Android',
        competitor_learned_from: 'Linear',
      },
      {
        risk: 'Onboarding drop-off in first 7 days estimated at 40–60% for free-tier users',
        severity: 'CRITICAL',
        evidence: 'New users consistently report confusion around workspace setup and template discovery',
        competitor_learned_from: 'Coda',
      },
      {
        risk: 'AI features feel bolted-on rather than native, risking commoditization of core value prop',
        severity: 'MEDIUM',
        evidence: 'AI writing assistant usage low relative to competitors who ship AI as table stakes',
        competitor_learned_from: 'Craft',
      },
    ],
    top_opportunities: [
      {
        opportunity: 'Enterprise workflow automation — Notion API is powerful but critically underutilized',
        impact: 'TRANSFORMATIVE',
        evidence: 'Only 8% of power users use the API despite 40%+ citing automation as a top need',
        competitor_failed_at: 'Evernote Teams',
      },
      {
        opportunity: 'Notion-as-website builder gaining organic traction with no-code makers',
        impact: 'HIGH',
        evidence: 'Subreddit growth for Notion site building doubled YoY; Fruition & Super.so expanding fast',
        competitor_failed_at: 'Confluence',
      },
      {
        opportunity: 'Verticalize templates for high-value sectors: legal, finance, medical',
        impact: 'MEDIUM',
        evidence: 'Template marketplace top downloads skew heavily toward these three verticals',
        competitor_failed_at: 'Airtable',
      },
    ],
    moat_assessment:
      "Notion's moat is real but conditional. The block-based data model creates genuine structural lock-in for teams with complex linked databases. However, the moat is nearly non-existent for individual users in the note-taking use case, where Bear, Obsidian, and Apple Notes provide 80% of the value with 20% of the friction.",
    strategist_score: 7.5,
    strategist_summary:
      'Notion is a category-defining product with genuine network effects in team contexts, but faces an existential onboarding challenge that compounds with every new AI-native entrant. The competitive window is 18–24 months before AI-assisted workspace setup becomes table stakes. Long-term defensibility hinges on deepening the database and API layer, not on incremental feature additions.',
  },
  ux_analyst_section: {
    comparison_cards: [
      {
        card_id: 'onboarding-flow',
        user_screen: {
          frame_number: 1,
          image_path: 'sessions/test/frames/frame_001.jpg',
          screen_label: 'Notion — Empty Workspace',
          ux_score: 5.5,
          strengths: ['Clean visual hierarchy', 'Template suggestion visible', 'Dark mode available'],
          weaknesses: ['No guided next step', 'Overwhelming sidebar options', 'No progress indicator'],
        },
        competitor_screen: {
          app: 'linear',
          filename: 'linear_onboarding_01.jpg',
          image_path: 'data/linear/screenshots/linear_onboarding_01.jpg',
          screen_label: 'Linear — New Team Setup',
          ux_score: 8.5,
          strengths: ['Clear 3-step progress bar', 'Sensible defaults pre-selected', 'Team invite prominent'],
          weaknesses: ['Less customizable', 'Opinionated workflow limits edge cases'],
        },
        similarity_score: 0.45,
        comparison_verdict: 'COMPETITOR_BETTER',
        what_to_steal:
          "Linear's 3-step wizard with progress indicator. Users need a 'minimum viable workspace' set up in under 90 seconds, not an infinite canvas with no direction.",
        what_to_avoid:
          "Linear's opinionated structure — Notion's flexibility is core to its value prop, don't trade it for false simplicity.",
      },
      {
        card_id: 'database-view',
        user_screen: {
          frame_number: 8,
          image_path: 'sessions/test/frames/frame_008.jpg',
          screen_label: 'Notion — Database Table View',
          ux_score: 7.8,
          strengths: ['Multiple view types accessible', 'Inline editing fluid', 'Filter/sort controls intuitive'],
          weaknesses: ['Relation fields confusing for new users', 'Formula syntax undiscoverable', 'Performance degrades at 500+ rows'],
        },
        competitor_screen: {
          app: 'airtable',
          filename: 'airtable_grid_view.jpg',
          image_path: 'data/airtable/screenshots/airtable_grid_view.jpg',
          screen_label: 'Airtable — Grid View',
          ux_score: 8.2,
          strengths: ['Field type picker excellent', 'Bulk edit streamlined', 'Extensions marketplace prominent'],
          weaknesses: ['Pricing wall hits earlier', 'Less writing-friendly', 'UI feels older'],
        },
        similarity_score: 0.72,
        comparison_verdict: 'COMPARABLE',
        what_to_steal:
          "Airtable's field type picker UX — visual icons + description for each field type reduces trial-and-error by ~60%.",
        what_to_avoid:
          "Airtable's extension marketplace placement — creates cognitive overhead before users understand the core product.",
      },
    ],
    onboarding_assessment: {
      score: 5.0,
      time_to_value_estimate: '45–90 minutes for average user',
      first_action_clarity: 'BURIED',
      cognitive_load: 'HIGH',
      recommendation:
        'Implement a role-based onboarding flow (Student / Solo / Team) that pre-populates a starter workspace. Target <5 minutes to first aha moment. Add interactive tooltips for the first 3 sessions.',
    },
    friction_map: [
      {
        screen: 'Workspace Setup',
        friction_point: 'No guided setup — user lands on blank canvas with no clear first action',
        severity: 'BLOCKER',
        fix_effort: 'SIGNIFICANT_REWORK',
      },
      {
        screen: 'Database Creation',
        friction_point: 'Turning pages into databases requires knowing to type /database — undiscoverable',
        severity: 'MAJOR',
        fix_effort: 'MODERATE',
      },
      {
        screen: 'Mobile App',
        friction_point: 'Offline mode unreliable — users lose work when switching WiFi to cellular',
        severity: 'MAJOR',
        fix_effort: 'SIGNIFICANT_REWORK',
      },
      {
        screen: 'Template Gallery',
        friction_point: 'Applying template creates duplicate blocks on existing page rather than replacing',
        severity: 'MODERATE',
        fix_effort: 'QUICK_WIN',
      },
      {
        screen: 'Sharing & Permissions',
        friction_point: 'Guest vs. Member distinction unclear — users accidentally over-share sensitive pages',
        severity: 'MODERATE',
        fix_effort: 'QUICK_WIN',
      },
      {
        screen: 'Search',
        friction_point: 'Full-text search does not index inside databases by default, returning zero results',
        severity: 'MAJOR',
        fix_effort: 'MODERATE',
      },
    ],
    ux_analyst_score: 6.5,
    ux_analyst_summary:
      "Notion's UI is deceptively powerful but rewards expertise over discovery. The gap between power user and casual user UX is the widest of any tool in this category. Onboarding is the bleeding wound — every percentage point of first-week retention improvement translates directly to LTV. The comparison analysis shows competitors have solved the onboarding problem without sacrificing flexibility, which removes Notion's last excuse for not fixing it.",
  },
  market_researcher_section: {
    sentiment_analysis: {
      overall_sentiment: 'MIXED',
      sentiment_by_competitor: [
        { app: 'Notion', sentiment: 'MIXED', sample_size: 847, top_praise: 'Infinitely customizable, changed how I work', top_complaint: 'Too slow on mobile, crashes constantly' },
        { app: 'Linear', sentiment: 'POSITIVE', sample_size: 312, top_praise: 'Best issue tracker ever built, period', top_complaint: 'Not flexible enough for non-engineering teams' },
        { app: 'Coda', sentiment: 'POSITIVE', sample_size: 198, top_praise: 'Docs that actually do things', top_complaint: 'Pricing jumped too fast' },
        { app: 'Airtable', sentiment: 'MIXED', sample_size: 523, top_praise: 'Spreadsheet power with database flexibility', top_complaint: 'Automation tier pricing is insulting' },
      ],
    },
    killer_quotes: [
      {
        quote: "I've rebuilt my entire company's operations in Notion. Nothing else even comes close for the way we work.",
        source: 'reddit',
        app: 'Notion',
        relevance: 'Power user retention signal — once embedded, stays embedded',
      },
      {
        quote: 'Switched from Notion to Linear for engineering. Notion is a blank canvas. Linear is an opinionated tool. I needed the opinion.',
        source: 'hackernews',
        app: 'Linear',
        relevance: 'Clear segmentation signal — different tools for different team types',
      },
      {
        quote: 'The mobile app is an embarrassment for a product at this price point. Crashes 3–4 times per session.',
        source: 'google_play',
        app: 'Notion',
        relevance: 'Mobile UX is active churn driver, not just a complaint signal',
      },
      {
        quote: 'Onboarding is a disaster. I watched 4 coworkers give up in the first hour. We went back to Confluence.',
        source: 'reddit',
        app: 'Notion',
        relevance: 'Onboarding failure has org-level switching cost implications',
      },
    ],
    pricing_positioning: {
      competitor_range: '$0–$20/user/month across all tiers',
      sweet_spot: '$8–12/user/month for team plan',
      pricing_insight:
        "Notion Plus at $10/user/month sits squarely in the sweet spot, but the free tier is too limited to convert power users who need unlimited blocks. The 'unlimited guests' positioning resonates strongly with agency and consulting teams.",
    },
    adoption_signals: {
      easy_wins: [
        'Students and educators — 2M+ active users, strong word-of-mouth flywheel',
        'Remote-first startups — 78% of YC S22 batch use Notion as default workspace',
        "Personal knowledge management — growing 'second brain' community and creator ecosystem",
      ],
      dealbreakers: [
        'Enterprise IT compliance — SOC 2 gaps vs. Confluence in regulated industries',
        'Mobile-heavy workflows — iOS/Android quality unacceptable to field-based teams',
        'Real-time collaboration at scale — 10+ simultaneous editors causes degraded performance',
      ],
    },
    market_researcher_score: 7.0,
    market_researcher_summary:
      "Notion's brand equity is exceptional for B2B SaaS — few tools generate the religious devotion visible in Reddit communities. However, there's a clear bifurcation: power users evangelise fiercely while casual users churn silently. The market research confirms that mobile quality and onboarding are not nice-to-haves but active revenue risks, with documented org-level churns attributable to both issues directly.",
  },
  challenge_layer: {
    contradictions_found: [
      {
        between: 'UX Analyst score and Strategist strategic assessment',
        issue:
          "UX Analyst scores onboarding 5/10 as a critical blocker. Strategist rates overall product 7.5/10 treating onboarding as 'fixable'. These cannot both be true — if onboarding is truly blocking mass adoption, the strategic score should be materially lower.",
        resolution:
          'Align on 6.8–7.0 overall. Onboarding is a strategic risk that compounds competitive position, not an isolated UX issue.',
      },
      {
        between: 'Market Researcher positive sentiment and UX friction severity',
        issue:
          "Market Researcher finds 'strong brand equity' and positive community sentiment, while UX analysis shows multiple BLOCKER-level friction points. If UX is this broken, how does sentiment stay positive?",
        resolution:
          'Power user selection bias in review data. Reddit/HN reviews overrepresent embedded users. Churn is silent — people who left do not post reviews. The positive sentiment reflects survivors, not the full funnel.',
      },
    ],
    blind_spots: [
      'Analysis focused on US/English market — international growth trajectory not assessed',
      'No assessment of enterprise sales motion, which may offset consumer churn numbers',
      'AI product evolution not modelled — Notion AI could become primary differentiation in 12 months',
      'No cohort analysis — we cannot determine if the onboarding problem is worsening or improving over time',
    ],
    final_verdict:
      "Notion is a category winner that has created its own existential risk through neglect of the new-user experience. The product's depth and flexibility give it a 7+ year competitive moat with embedded teams, but first-time users are walking into a beautiful, empty store with no guidance. The next 18 months are critical: fix onboarding, ship a credible mobile experience, and double down on the API/automation layer before AI-native competitors commoditize the core writing and database features.",
    final_score: 7.1,
    confidence: 'HIGH',
    one_thing_to_do_monday:
      'Run a moderated usability test with 5 non-Notion users and record the first 10 minutes of each session. Watch where they stop. That timestamp is your roadmap.',
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function scoreColor(score: number): string {
  if (score >= 7) return 'var(--accent-green)'
  if (score >= 5) return 'var(--accent-amber)'
  return 'var(--accent-red)'
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
  } catch {
    return iso
  }
}

function getImageUrl(imagePath: string, imageUrl?: string): string {
  if (imageUrl) return imageUrl
  return `${API_BASE}/${imagePath}`
}

const MARKET_READINESS_STYLE: Record<MarketReadiness, { label: string; color: string; bg: string; border: string }> = {
  NOT_READY:   { label: 'Not Ready',   color: 'var(--accent-red)',    bg: 'rgba(239,68,68,0.1)',    border: 'rgba(239,68,68,0.3)'   },
  NEEDS_WORK:  { label: 'Needs Work',  color: 'var(--accent-amber)',  bg: 'rgba(245,158,11,0.1)',   border: 'rgba(245,158,11,0.3)'  },
  COMPETITIVE: { label: 'Competitive', color: 'var(--accent-blue)',   bg: 'rgba(59,130,246,0.1)',   border: 'rgba(59,130,246,0.3)'  },
  STRONG:      { label: 'Strong',      color: 'var(--accent-green)',  bg: 'rgba(34,197,94,0.1)',    border: 'rgba(34,197,94,0.3)'   },
  EXCEPTIONAL: { label: 'Exceptional', color: 'var(--accent-purple)', bg: 'rgba(168,85,247,0.1)',   border: 'rgba(168,85,247,0.3)'  },
}

const SEVERITY_STYLE: Record<Severity, { color: string; bg: string; border: string }> = {
  LOW:      { color: 'var(--text-muted)',       bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.08)' },
  MEDIUM:   { color: 'var(--accent-amber)',      bg: 'rgba(245,158,11,0.1)',   border: 'rgba(245,158,11,0.25)'  },
  HIGH:     { color: '#fb923c',                  bg: 'rgba(251,146,60,0.1)',   border: 'rgba(251,146,60,0.25)'  },
  CRITICAL: { color: 'var(--accent-red)',        bg: 'rgba(239,68,68,0.1)',    border: 'rgba(239,68,68,0.3)'    },
}

const IMPACT_STYLE: Record<Impact, { color: string; bg: string; border: string }> = {
  LOW:           { color: 'var(--text-muted)',       bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.08)' },
  MEDIUM:        { color: 'var(--accent-blue)',       bg: 'rgba(59,130,246,0.1)',   border: 'rgba(59,130,246,0.25)'  },
  HIGH:          { color: 'var(--accent-green)',      bg: 'rgba(34,197,94,0.1)',    border: 'rgba(34,197,94,0.25)'   },
  TRANSFORMATIVE:{ color: 'var(--accent-purple)',     bg: 'rgba(168,85,247,0.1)',   border: 'rgba(168,85,247,0.3)'   },
}

const FRICTION_SEVERITY_STYLE: Record<FrictionSeverity, { color: string; bg: string; border: string }> = {
  MINOR:    { color: 'var(--text-muted)',  bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.08)' },
  MODERATE: { color: 'var(--accent-amber)', bg: 'rgba(245,158,11,0.1)',  border: 'rgba(245,158,11,0.25)'  },
  MAJOR:    { color: '#fb923c',             bg: 'rgba(251,146,60,0.1)',   border: 'rgba(251,146,60,0.25)'  },
  BLOCKER:  { color: 'var(--accent-red)',   bg: 'rgba(239,68,68,0.1)',    border: 'rgba(239,68,68,0.3)'    },
}

const FIX_EFFORT_STYLE: Record<FixEffort, { label: string; color: string; bg: string; border: string }> = {
  QUICK_WIN:          { label: 'Quick Win',     color: 'var(--accent-green)',  bg: 'rgba(34,197,94,0.1)',   border: 'rgba(34,197,94,0.25)'  },
  MODERATE:           { label: 'Moderate',      color: 'var(--accent-blue)',   bg: 'rgba(59,130,246,0.1)',  border: 'rgba(59,130,246,0.25)' },
  SIGNIFICANT_REWORK: { label: 'Major Rework',  color: 'var(--accent-amber)',  bg: 'rgba(245,158,11,0.1)',  border: 'rgba(245,158,11,0.25)' },
}

const SENTIMENT_STYLE: Record<string, { color: string; bg: string; pct: number }> = {
  NEGATIVE:     { color: 'var(--accent-red)',    bg: 'rgba(239,68,68,0.7)',    pct: 15 },
  MIXED:        { color: 'var(--accent-amber)',  bg: 'rgba(245,158,11,0.7)',   pct: 50 },
  NEUTRAL:      { color: 'var(--text-muted)',    bg: 'rgba(255,255,255,0.25)', pct: 45 },
  POSITIVE:     { color: 'var(--accent-green)',  bg: 'rgba(34,197,94,0.7)',    pct: 75 },
  VERY_POSITIVE:{ color: 'var(--accent-purple)', bg: 'rgba(168,85,247,0.7)',   pct: 92 },
}

const SOURCE_STYLE: Record<QuoteSource, { label: string; color: string; bg: string }> = {
  reddit:     { label: 'Reddit',      color: '#fff', bg: '#FF4500' },
  hackernews: { label: 'HN',          color: '#fff', bg: '#FF6600' },
  google_play:{ label: 'Play Store',  color: '#fff', bg: '#34A853' },
}

const VERDICT_BADGE: Record<ComparisonVerdict, { label: string; color: string; bg: string; border: string }> = {
  USER_BETTER:       { label: 'Your App Wins',       color: 'var(--accent-green)',  bg: 'rgba(34,197,94,0.1)',   border: 'rgba(34,197,94,0.3)'   },
  COMPETITOR_BETTER: { label: 'Competitor Leads',    color: 'var(--accent-red)',    bg: 'rgba(239,68,68,0.1)',   border: 'rgba(239,68,68,0.3)'   },
  COMPARABLE:        { label: 'Comparable',          color: 'var(--accent-amber)',  bg: 'rgba(245,158,11,0.1)',  border: 'rgba(245,158,11,0.3)'  },
}

const CONFIDENCE_STYLE: Record<Confidence, { color: string; bg: string; border: string }> = {
  LOW:    { color: 'var(--accent-amber)',  bg: 'rgba(245,158,11,0.1)',  border: 'rgba(245,158,11,0.3)'  },
  MEDIUM: { color: 'var(--accent-blue)',   bg: 'rgba(59,130,246,0.1)',  border: 'rgba(59,130,246,0.3)'  },
  HIGH:   { color: 'var(--accent-green)',  bg: 'rgba(34,197,94,0.1)',   border: 'rgba(34,197,94,0.3)'   },
}

const FRICTION_SEVERITY_ORDER: Record<FrictionSeverity, number> = {
  BLOCKER: 0, MAJOR: 1, MODERATE: 2, MINOR: 3,
}

// ─────────────────────────────────────────────────────────────────────────────
// Hooks
// ─────────────────────────────────────────────────────────────────────────────

function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setInView(true); obs.disconnect() } },
      { threshold },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])

  return { ref, inView }
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function Badge({ label, color, bg, border }: { label: string; color: string; bg: string; border: string }) {
  return (
    <span style={{
      display: 'inline-block',
      fontFamily: 'var(--font-mono)',
      fontSize: 10,
      fontWeight: 500,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      color,
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 100,
      padding: '3px 10px',
      whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  )
}

function SectionTitle({ label, subtitle }: { label: string; subtitle?: string }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <p style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        fontWeight: 500,
        letterSpacing: '0.2em',
        textTransform: 'uppercase',
        color: 'var(--text-muted)',
        margin: '0 0 8px',
      }}>
        {label}
      </p>
      {subtitle && (
        <p style={{
          fontFamily: 'var(--font-body)',
          fontSize: 13,
          color: 'var(--text-secondary)',
          margin: 0,
          lineHeight: 1.5,
        }}>
          {subtitle}
        </p>
      )}
      <div style={{ width: 32, height: 1, background: 'rgba(255,255,255,0.1)', marginTop: 12 }} />
    </div>
  )
}

function ExecutionBadge({ meta }: { meta: ExecutionMetadata }) {
  const isDgx = meta.mode === 'dgx'
  const totalElapsed = meta.execution_log
    ? meta.execution_log.reduce((sum, e) => sum + e.elapsed_seconds, 0)
    : null

  const color = isDgx ? '#a78bfa' : 'var(--accent-blue)'
  const bg = isDgx ? 'rgba(167,139,250,0.08)' : 'rgba(59,130,246,0.08)'
  const border = isDgx ? 'rgba(167,139,250,0.2)' : 'rgba(59,130,246,0.2)'

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 10,
      padding: '6px 14px 6px 10px',
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 100,
    }}>
      <span style={{ fontSize: 12 }}>{isDgx ? '⚡' : '☁️'}</span>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        fontWeight: 500,
        color,
        letterSpacing: '0.06em',
      }}>
        {isDgx
          ? `DGX Spark — Local Inference (${meta.model})`
          : `Cloud API — OpenAI ${meta.model}`}
      </span>
      {totalElapsed !== null && (
        <>
          <span style={{ width: 1, height: 12, background: border, flexShrink: 0 }} />
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'var(--text-muted)',
          }}>
            {totalElapsed.toFixed(1)}s total
          </span>
        </>
      )}
      {isDgx && meta.tier !== undefined && (
        <>
          <span style={{ width: 1, height: 12, background: border, flexShrink: 0 }} />
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'var(--text-muted)',
          }}>
            Tier {meta.tier}
          </span>
        </>
      )}
    </div>
  )
}

function ExecutionLogPanel({ meta }: { meta: ExecutionMetadata }) {
  const [open, setOpen] = useState(false)
  const log = meta.execution_log ?? []
  if (!log.length) return null
  const isDgx = meta.mode === 'dgx'

  return (
    <div style={{ marginTop: 12 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
          display: 'flex', alignItems: 'center', gap: 6,
        }}
      >
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em',
          textTransform: 'uppercase', color: 'var(--text-muted)',
        }}>
          {open ? '↑ Hide' : '↓ Show'} execution log
        </span>
      </button>
      {open && (
        <div style={{
          marginTop: 10,
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border)',
          borderRadius: 4,
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'var(--bg-card)' }}>
                {['Round', 'Model', isDgx ? 'GPU Temp' : 'Mode', 'Elapsed', 'Status'].map(h => (
                  <th key={h} style={{
                    padding: '8px 14px', textAlign: 'left',
                    fontFamily: 'var(--font-mono)', fontSize: 9,
                    letterSpacing: '0.1em', textTransform: 'uppercase',
                    color: 'var(--text-muted)', fontWeight: 500,
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {log.map((entry, i) => (
                <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: '9px 14px', fontFamily: 'var(--font-body)', fontSize: 12, color: 'var(--text-primary)' }}>
                    {entry.round}
                  </td>
                  <td style={{ padding: '9px 14px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)' }}>
                    {entry.model}
                  </td>
                  <td style={{ padding: '9px 14px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                    {isDgx
                      ? (entry.gpu_temp_before !== undefined && entry.gpu_temp_before >= 0
                          ? `${entry.gpu_temp_before}°C`
                          : '—')
                      : 'parallel'}
                  </td>
                  <td style={{ padding: '9px 14px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent-blue)' }}>
                    {entry.elapsed_seconds}s
                  </td>
                  <td style={{ padding: '9px 14px', fontFamily: 'var(--font-mono)', fontSize: 11,
                    color: entry.status === 'OK' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    {entry.status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function ScoreRing({ score, size = 'medium' }: { score: number; size?: 'large' | 'medium' | 'small' }) {
  const [animated, setAnimated] = useState(0)

  const cfg = {
    large:  { radius: 52, stroke: 4, fontSize: 44, subSize: 12, wh: 120 },
    medium: { radius: 36, stroke: 3, fontSize: 28, subSize: 10, wh: 84  },
    small:  { radius: 22, stroke: 2.5, fontSize: 17, subSize: 8,  wh: 52  },
  }[size]

  const circumference = 2 * Math.PI * cfg.radius
  const svgSize = (cfg.radius + cfg.stroke + 2) * 2
  const filled = (animated / 10) * circumference
  const color = scoreColor(score)

  useEffect(() => {
    const start = performance.now()
    const duration = 1400
    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setAnimated(parseFloat((score * eased).toFixed(1)))
      if (progress < 1) requestAnimationFrame(tick)
    }
    const raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [score])

  return (
    <div className="score-ring-wrap" style={{ width: cfg.wh, height: cfg.wh }}>
      <svg
        width={svgSize} height={svgSize}
        viewBox={`0 0 ${svgSize} ${svgSize}`}
        style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
      >
        <circle
          cx={svgSize / 2} cy={svgSize / 2} r={cfg.radius}
          fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={cfg.stroke}
        />
        <circle
          cx={svgSize / 2} cy={svgSize / 2} r={cfg.radius}
          fill="none" stroke={color} strokeWidth={cfg.stroke}
          strokeDasharray={`${filled} ${circumference - filled}`}
          strokeDashoffset={circumference * 0.25}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 80ms linear' }}
        />
      </svg>
      <div style={{ position: 'relative', textAlign: 'center', lineHeight: 1 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: cfg.fontSize, fontWeight: 400, color, display: 'block' }}>
          {animated.toFixed(size === 'large' ? 1 : 0)}
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: cfg.subSize, color: 'var(--text-muted)' }}>
          / 10
        </span>
      </div>
    </div>
  )
}

function ImageWithFallback({ src, alt, label, score }: { src: string; alt: string; label: string; score: number }) {
  const [failed, setFailed] = useState(false)
  const color = scoreColor(score)

  if (failed) {
    return (
      <div className="img-placeholder" style={{ aspectRatio: '9/16', maxHeight: 320, minHeight: 200 }}>
        <svg width={32} height={32} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1}>
          <rect x={3} y={3} width={18} height={18} rx={2} />
          <path d="M3 9h18M9 21V9" />
        </svg>
        <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-body)', fontSize: 12 }}>{label}</span>
        <span style={{ color, fontFamily: 'var(--font-mono)', fontSize: 11 }}>{score}/10</span>
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      onError={() => setFailed(true)}
      style={{
        width: '100%',
        objectFit: 'cover',
        borderRadius: 8,
        display: 'block',
        maxHeight: 320,
        minHeight: 200,
        background: 'var(--bg-card)',
      }}
    />
  )
}

function SectionWrap({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const { ref, inView } = useInView()
  return (
    <div
      ref={ref}
      className={`report-section${inView ? ' in-view' : ''}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  )
}

function Collapsible({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', background: 'transparent', border: 'none',
          padding: '14px 20px', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
        }}
      >
        <span style={{ fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', textAlign: 'left' }}>
          {title}
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.25s ease', flexShrink: 0,
        }}>
          ↓
        </span>
      </button>
      {open && (
        <div style={{ padding: '0 20px 20px', borderTop: '1px solid var(--border)' }}>
          {children}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 1: Hero
// ─────────────────────────────────────────────────────────────────────────────

function HeroSection({ data }: { data: ReportData }) {
  const mr = MARKET_READINESS_STYLE[data.verdict.market_readiness] ?? MARKET_READINESS_STYLE['NEEDS_WORK']

  return (
    <div
      className="report-hero"
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '80px 0',
        position: 'relative',
        background: 'radial-gradient(ellipse 80% 60% at 50% 0%, rgba(59,130,246,0.06) 0%, transparent 70%), var(--bg-primary)',
      }}
    >
      {/* Top bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            War Room Analysis
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', margin: '0 10px' }}>·</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
            {formatDate(data.analysis_timestamp)}
          </span>
        </div>
        <button className="pdf-btn" onClick={() => window.print()}>
          <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
          </svg>
          Download PDF
        </button>
      </div>

      {/* Execution badge */}
      {data.execution_metadata && (
        <div style={{ marginBottom: 48 }}>
          <ExecutionBadge meta={data.execution_metadata} />
          <ExecutionLogPanel meta={data.execution_metadata} />
        </div>
      )}

      {/* Product name */}
      <p style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: '0.25em',
        textTransform: 'uppercase',
        color: 'var(--text-muted)',
        margin: '0 0 20px',
      }}>
        {data.product_name}
      </p>

      {/* Headline */}
      <h1 style={{
        fontFamily: 'var(--font-display)',
        fontSize: 'clamp(36px, 5vw, 58px)',
        fontWeight: 400,
        color: 'var(--text-primary)',
        lineHeight: 1.1,
        letterSpacing: '-0.02em',
        margin: '0 0 48px',
        maxWidth: 760,
      }}>
        {data.verdict.headline}
      </h1>

      {/* Score + readiness */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 28, marginBottom: 36, flexWrap: 'wrap' }}>
        <ScoreRing score={data.verdict.score} size="large" />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Badge label={mr.label} color={mr.color} bg={mr.bg} border={mr.border} />
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            color: 'var(--text-muted)',
            letterSpacing: '0.06em',
          }}>
            Market Readiness
          </span>
        </div>
      </div>

      {/* Recommendation */}
      <p style={{
        fontFamily: 'var(--font-body)',
        fontSize: 17,
        fontWeight: 300,
        color: 'var(--text-secondary)',
        lineHeight: 1.75,
        maxWidth: 660,
        margin: 0,
        borderLeft: '2px solid rgba(255,255,255,0.1)',
        paddingLeft: 20,
      }}>
        {data.verdict.recommendation}
      </p>

      {/* Target user */}
      <p style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        color: 'var(--text-muted)',
        marginTop: 28,
        letterSpacing: '0.06em',
      }}>
        Target: {data.target_user}
      </p>

      {/* Scroll indicator */}
      <div style={{ position: 'absolute', bottom: 32, left: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6, opacity: 0.3 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-primary)' }}>Scroll</span>
        <div style={{ width: 1, height: 32, background: 'var(--text-primary)' }} />
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 2: Analyst Scores
// ─────────────────────────────────────────────────────────────────────────────

function AnalystCard({
  title, subtitle, score, summary,
}: {
  title: string; subtitle: string; score: number; summary: string
}) {
  return (
    <div style={{
      flex: 1,
      padding: '32px 28px',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      gap: 20,
    }}>
      <div>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 6px' }}>
          {subtitle}
        </p>
        <p style={{ fontFamily: 'var(--font-body)', fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
          {title}
        </p>
      </div>
      <ScoreRing score={score} size="medium" />
      <p style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>
        {summary}
      </p>
    </div>
  )
}

function AnalystScoresSection({ data }: { data: ReportData }) {
  return (
    <SectionWrap>
      <SectionTitle label="Analyst Scores" subtitle="Three independent perspectives, one unified signal" />
      <div style={{ display: 'flex', border: '1px solid var(--border)', borderRadius: 2, overflow: 'hidden' }}>
        <AnalystCard
          title="The Strategist"
          subtitle="Competitive Analysis"
          score={data.strategist_section.strategist_score}
          summary={data.strategist_section.strategist_summary}
        />
        <AnalystCard
          title="The UX Analyst"
          subtitle="User Experience"
          score={data.ux_analyst_section.ux_analyst_score}
          summary={data.ux_analyst_section.ux_analyst_summary}
        />
        <div style={{ flex: 1, padding: '32px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 6px' }}>
              Market Research
            </p>
            <p style={{ fontFamily: 'var(--font-body)', fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
              The Market Researcher
            </p>
          </div>
          <ScoreRing score={data.market_researcher_section.market_researcher_score} size="medium" />
          <p style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>
            {data.market_researcher_section.market_researcher_summary}
          </p>
        </div>
      </div>
    </SectionWrap>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 3: Comparison Cards
// ─────────────────────────────────────────────────────────────────────────────

function ScreenCard({ screen, imageUrl }: { screen: ScreenData | CompetitorScreenData; imageUrl: string }) {
  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <ImageWithFallback
        src={imageUrl}
        alt={screen.screen_label}
        label={screen.screen_label}
        score={screen.ux_score}
      />
      <div style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <p style={{ fontFamily: 'var(--font-body)', fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', margin: 0 }}>
            {screen.screen_label}
          </p>
          <ScoreRing score={screen.ux_score} size="small" />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {screen.strengths.map((s, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              <span style={{ color: 'var(--accent-green)', fontSize: 12, flexShrink: 0, marginTop: 1 }}>✓</span>
              <span style={{ fontFamily: 'var(--font-body)', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{s}</span>
            </div>
          ))}
          {screen.weaknesses.map((w, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              <span style={{ color: 'var(--accent-red)', fontSize: 12, flexShrink: 0, marginTop: 1 }}>✗</span>
              <span style={{ fontFamily: 'var(--font-body)', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{w}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function ComparisonCardItem({ card }: { card: ComparisonCard }) {
  const vb = VERDICT_BADGE[card.comparison_verdict]
  const userUrl = getImageUrl(card.user_screen.image_path, card.user_screen.image_url)
  const compUrl = getImageUrl(card.competitor_screen.image_path, card.competitor_screen.image_url)

  return (
    <div
      className="comparison-card"
      style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 2,
        padding: '32px',
      }}
    >
      {/* Images side by side */}
      <div style={{ display: 'flex', gap: 24, marginBottom: 24, alignItems: 'flex-start' }}>
        <ScreenCard screen={card.user_screen} imageUrl={userUrl} />

        {/* Center divider with meta */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          gap: 12, paddingTop: 24, flexShrink: 0,
        }}>
          <div style={{ width: 1, height: 32, background: 'var(--border)' }} />
          <Badge label={vb.label} color={vb.color} bg={vb.bg} border={vb.border} />
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            color: 'var(--text-muted)',
            textAlign: 'center',
          }}>
            <div style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
              {Math.round(card.similarity_score * 100)}%
            </div>
            <div style={{ fontSize: 9, letterSpacing: '0.1em', marginTop: 2 }}>SIMILAR</div>
          </div>
          <div style={{ width: 1, height: 32, background: 'var(--border)' }} />
        </div>

        <ScreenCard screen={card.competitor_screen} imageUrl={compUrl} />
      </div>

      {/* Steal / Avoid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, borderTop: '1px solid var(--border)', paddingTop: 20 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>💡</span>
          <div>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent-green)', margin: '0 0 6px' }}>
              What to steal
            </p>
            <p style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
              {card.what_to_steal}
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>⚠</span>
          <div>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent-amber)', margin: '0 0 6px' }}>
              What to avoid
            </p>
            <p style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
              {card.what_to_avoid}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function ComparisonCardsSection({ data }: { data: ReportData }) {
  const cards = data.ux_analyst_section.comparison_cards ?? []
  if (!cards.length) return null

  return (
    <SectionWrap>
      <SectionTitle
        label="UX Comparison"
        subtitle={`Side-by-side analysis across ${cards.length} screen pair${cards.length !== 1 ? 's' : ''}`}
      />

      {/* Onboarding assessment strip */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 2,
        padding: '20px 24px',
        marginBottom: 32,
        display: 'flex',
        gap: 32,
        flexWrap: 'wrap',
        alignItems: 'center',
      }}>
        {data.ux_analyst_section.onboarding_assessment && (
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Onboarding Score
          </span>
          <ScoreRing score={data.ux_analyst_section.onboarding_assessment.score ?? 5} size="small" />
        </div>
        )}
        {data.ux_analyst_section.onboarding_assessment?.time_to_value_estimate && (
        <div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Time to Value · </span>
          <span style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-primary)' }}>
            {data.ux_analyst_section.onboarding_assessment.time_to_value_estimate}
          </span>
        </div>
        )}
        {data.ux_analyst_section.onboarding_assessment?.first_action_clarity && (
        <div style={{ display: 'flex', gap: 8 }}>
          {(['OBVIOUS','FINDABLE','BURIED','MISSING'] as FirstActionClarity[]).map(v => {
            const active = v === data.ux_analyst_section.onboarding_assessment!.first_action_clarity
            return (
              <span key={v} style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 9,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: active ? 'var(--accent-red)' : 'var(--text-muted)',
                background: active ? 'rgba(239,68,68,0.1)' : 'transparent',
                border: `1px solid ${active ? 'rgba(239,68,68,0.3)' : 'var(--border)'}`,
                borderRadius: 100,
                padding: '2px 8px',
              }}>
                {v}
              </span>
            )
          })}
        </div>
        )}
      </div>

      <div className="comparison-scroll">
        {cards.map(card => (
          <ComparisonCardItem key={card.card_id} card={card} />
        ))}
      </div>
    </SectionWrap>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 4: Risks & Opportunities
// ─────────────────────────────────────────────────────────────────────────────

function RisksOpportunitiesSection({ data }: { data: ReportData }) {
  const s = data.strategist_section
  const topRisks = s.top_risks ?? []
  const topOpportunities = s.top_opportunities ?? []
  return (
    <SectionWrap>
      <SectionTitle label="Strategic Landscape" subtitle={s.competitive_positioning} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Risks */}
        <div>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--accent-red)', marginBottom: 16 }}>
            Top Risks
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {topRisks.map((risk, i) => {
              const st = SEVERITY_STYLE[risk.severity]
              return (
                <div key={i} style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  borderRadius: 2,
                  padding: '16px 18px',
                  borderLeft: `2px solid ${st.color}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
                    <p style={{ fontFamily: 'var(--font-body)', fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', margin: 0, lineHeight: 1.4 }}>
                      {risk.risk}
                    </p>
                    <Badge label={risk.severity} color={st.color} bg={st.bg} border={st.border} />
                  </div>
                  <p style={{ fontFamily: 'var(--font-body)', fontSize: 12, color: 'var(--text-secondary)', fontStyle: 'italic', lineHeight: 1.55, margin: '0 0 8px' }}>
                    "{risk.evidence}"
                  </p>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                    Learned from: {risk.competitor_learned_from}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Opportunities */}
        <div>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--accent-green)', marginBottom: 16 }}>
            Top Opportunities
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {topOpportunities.map((opp, i) => {
              const it = IMPACT_STYLE[opp.impact]
              return (
                <div key={i} style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  borderRadius: 2,
                  padding: '16px 18px',
                  borderLeft: `2px solid ${it.color}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
                    <p style={{ fontFamily: 'var(--font-body)', fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', margin: 0, lineHeight: 1.4 }}>
                      {opp.opportunity}
                    </p>
                    <Badge label={opp.impact} color={it.color} bg={it.bg} border={it.border} />
                  </div>
                  <p style={{ fontFamily: 'var(--font-body)', fontSize: 12, color: 'var(--text-secondary)', fontStyle: 'italic', lineHeight: 1.55, margin: '0 0 8px' }}>
                    "{opp.evidence}"
                  </p>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                    Gap left by: {opp.competitor_failed_at}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Moat assessment */}
      <div style={{ marginTop: 24, padding: '20px 24px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 2 }}>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 10px' }}>
          Moat Assessment
        </p>
        <p style={{ fontFamily: 'var(--font-body)', fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>
          {s.moat_assessment}
        </p>
      </div>
    </SectionWrap>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 5: Market Intelligence
// ─────────────────────────────────────────────────────────────────────────────

function MarketIntelligenceSection({ data }: { data: ReportData }) {
  const mr = data.market_researcher_section
  const sentimentData = mr.sentiment_analysis ?? { overall_sentiment: 'NEUTRAL', sentiment_by_competitor: [] }
  const overallSt = SENTIMENT_STYLE[sentimentData.overall_sentiment] ?? SENTIMENT_STYLE['NEUTRAL']
  const killerQuotes = mr.killer_quotes ?? []
  const sentimentByComp = sentimentData.sentiment_by_competitor ?? []
  const pricingPos = mr.pricing_positioning ?? { competitor_range: 'N/A', sweet_spot: 'N/A', pricing_insight: '' }
  const adoptionSignals = mr.adoption_signals ?? { easy_wins: [], dealbreakers: [] }

  return (
    <SectionWrap>
      <SectionTitle label="Market Intelligence" subtitle="Sentiment, quotes, and pricing from real user data" />

      {/* Killer Quotes */}
      <div style={{ marginBottom: 32 }}>
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>
          Killer Quotes
        </p>
        <div className="killer-quotes-grid">
          {killerQuotes.map((q, i) => {
            const src = SOURCE_STYLE[q.source] ?? SOURCE_STYLE['reddit']
            return (
              <div key={i} style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                borderRadius: 2,
                padding: '20px 22px',
              }}>
                <p style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: 17,
                  fontStyle: 'italic',
                  color: 'var(--text-primary)',
                  lineHeight: 1.55,
                  margin: '0 0 16px',
                }}>
                  "{q.quote}"
                </p>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 500,
                      color: src.color, background: src.bg,
                      borderRadius: 100, padding: '2px 8px', letterSpacing: '0.07em',
                    }}>
                      {src.label}
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                      {q.app}
                    </span>
                  </div>
                  <span style={{ fontFamily: 'var(--font-body)', fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    {q.relevance}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Sentiment by competitor */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: 0 }}>
            Sentiment by Competitor
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>Overall:</span>
            <Badge
              label={(sentimentData.overall_sentiment ?? 'NEUTRAL').replace('_', ' ')}
              color={overallSt.color}
              bg={`${overallSt.color}18`}
              border={`${overallSt.color}40`}
            />
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {sentimentByComp.map((item, i) => {
            const st = SENTIMENT_STYLE[item.sentiment.toUpperCase()] ?? SENTIMENT_STYLE['NEUTRAL']
            return (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '80px 1fr 48px', gap: 16, alignItems: 'center' }}>
                <span style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>
                  {item.app}
                </span>
                <div className="sentiment-bar-track">
                  <div className="sentiment-bar-fill" style={{ width: `${st.pct}%`, background: st.bg }} />
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', textAlign: 'right' }}>
                  n={item.sample_size}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Pricing positioning */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 32 }}>
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 2, padding: '18px 20px' }}>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 8px' }}>
            Competitor Range
          </p>
          <p style={{ fontFamily: 'var(--font-display)', fontSize: 20, color: 'var(--text-primary)', margin: '0 0 8px' }}>
            {pricingPos.competitor_range}
          </p>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--accent-green)', margin: 0 }}>
            Sweet spot: {pricingPos.sweet_spot}
          </p>
        </div>
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 2, padding: '18px 20px' }}>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 8px' }}>
            Pricing Insight
          </p>
          <p style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.65, margin: 0 }}>
            {pricingPos.pricing_insight}
          </p>
        </div>
      </div>

      {/* Adoption signals */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 2, padding: '18px 20px' }}>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent-green)', margin: '0 0 12px' }}>
            Easy Wins
          </p>
          {(adoptionSignals.easy_wins ?? []).map((w, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, alignItems: 'flex-start' }}>
              <span style={{ color: 'var(--accent-green)', fontSize: 11, flexShrink: 0, marginTop: 2 }}>✓</span>
              <span style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{w}</span>
            </div>
          ))}
        </div>
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 2, padding: '18px 20px' }}>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent-red)', margin: '0 0 12px' }}>
            Dealbreakers
          </p>
          {(adoptionSignals.dealbreakers ?? []).map((d, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, alignItems: 'flex-start' }}>
              <span style={{ color: 'var(--accent-red)', fontSize: 11, flexShrink: 0, marginTop: 2 }}>✗</span>
              <span style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{d}</span>
            </div>
          ))}
        </div>
      </div>
    </SectionWrap>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 6: Friction Map
// ─────────────────────────────────────────────────────────────────────────────

function FrictionMapSection({ data }: { data: ReportData }) {
  const frictionMap = data.ux_analyst_section.friction_map ?? []
  if (!frictionMap.length) return null
  const sorted = [...frictionMap].sort(
    (a, b) => FRICTION_SEVERITY_ORDER[a.severity] - FRICTION_SEVERITY_ORDER[b.severity],
  )

  return (
    <SectionWrap>
      <SectionTitle label="Friction Map" subtitle="User experience blockers, sorted by severity" />
      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 2, overflow: 'hidden' }}>
        <table className="friction-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--bg-card)' }}>
              <th style={{ padding: '12px 16px', textAlign: 'left', fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500, width: '18%' }}>
                Screen
              </th>
              <th style={{ padding: '12px 16px', textAlign: 'left', fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500 }}>
                Friction Point
              </th>
              <th style={{ padding: '12px 16px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500, width: '110px' }}>
                Severity
              </th>
              <th style={{ padding: '12px 16px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500, width: '120px' }}>
                Fix Effort
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item, i) => {
              const ss = FRICTION_SEVERITY_STYLE[item.severity]
              const fe = FIX_EFFORT_STYLE[item.fix_effort]
              return (
                <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: '14px 16px', fontFamily: 'var(--font-body)', fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', verticalAlign: 'top' }}>
                    {item.screen}
                  </td>
                  <td style={{ padding: '14px 16px', fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.55, verticalAlign: 'top' }}>
                    {item.friction_point}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'center', verticalAlign: 'top' }}>
                    <Badge label={item.severity} color={ss.color} bg={ss.bg} border={ss.border} />
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'center', verticalAlign: 'top' }}>
                    <Badge label={fe.label} color={fe.color} bg={fe.bg} border={fe.border} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </SectionWrap>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Section 7: Partner's Verdict
// ─────────────────────────────────────────────────────────────────────────────

function PartnerVerdictSection({ data }: { data: ReportData }) {
  const cl = data.challenge_layer
  const confSt = CONFIDENCE_STYLE[cl.confidence] ?? CONFIDENCE_STYLE['MEDIUM']

  return (
    <SectionWrap>
      <SectionTitle label="The Partner's Verdict" subtitle="Challenge layer synthesis — where analysts contradict each other" />

      {/* Final verdict */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(59,130,246,0.06) 0%, rgba(168,85,247,0.04) 100%)',
        border: '1px solid rgba(59,130,246,0.15)',
        borderRadius: 2,
        padding: '28px 32px',
        marginBottom: 24,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 20 }}>
          <ScoreRing score={cl.final_score} size="medium" />
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <Badge label={`Confidence: ${cl.confidence}`} color={confSt.color} bg={confSt.bg} border={confSt.border} />
          </div>
        </div>
        <p style={{
          fontFamily: 'var(--font-display)',
          fontSize: 18,
          fontStyle: 'italic',
          color: 'var(--text-primary)',
          lineHeight: 1.65,
          margin: 0,
        }}>
          {cl.final_verdict}
        </p>
      </div>

      {/* Monday action callout */}
      <div style={{
        background: 'rgba(245,158,11,0.06)',
        border: '1px solid rgba(245,158,11,0.2)',
        borderRadius: 2,
        padding: '22px 28px',
        marginBottom: 24,
        display: 'flex',
        gap: 16,
        alignItems: 'flex-start',
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          background: 'rgba(245,158,11,0.15)',
          border: '1px solid rgba(245,158,11,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0, fontSize: 16,
        }}>
          →
        </div>
        <div>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--accent-amber)', margin: '0 0 8px' }}>
            One Thing to Do Monday
          </p>
          <p style={{ fontFamily: 'var(--font-body)', fontSize: 15, fontWeight: 500, color: 'var(--text-primary)', lineHeight: 1.6, margin: 0 }}>
            {cl.one_thing_to_do_monday}
          </p>
        </div>
      </div>

      {/* Contradictions */}
      {(cl.contradictions_found ?? []).length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12 }}>
            Contradictions Found
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(cl.contradictions_found ?? []).map((c, i) => (
              <Collapsible key={i} title={c.between}>
                <div style={{ paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div>
                    <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent-red)', margin: '0 0 6px' }}>
                      The Issue
                    </p>
                    <p style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
                      {c.issue}
                    </p>
                  </div>
                  <div>
                    <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent-green)', margin: '0 0 6px' }}>
                      Resolution
                    </p>
                    <p style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
                      {c.resolution}
                    </p>
                  </div>
                </div>
              </Collapsible>
            ))}
          </div>
        </div>
      )}

      {/* Blind spots */}
      {(cl.blind_spots ?? []).length > 0 && (
        <div>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12 }}>
            Known Blind Spots
          </p>
          <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 2, padding: '16px 20px' }}>
            {(cl.blind_spots ?? []).map((bs, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, marginBottom: i < cl.blind_spots.length - 1 ? 10 : 0, alignItems: 'flex-start' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', flexShrink: 0, marginTop: 2 }}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                  {bs}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </SectionWrap>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Analyzing Screen (shown while background analysis is running)
// ─────────────────────────────────────────────────────────────────────────────

function AnalyzingScreen({ mode }: { mode?: ExecutionMode }) {
  const [dots, setDots] = useState('.')
  useEffect(() => {
    const id = setInterval(() => setDots(d => d.length >= 3 ? '.' : d + '.'), 600)
    return () => clearInterval(id)
  }, [])

  const isDgx = mode === 'dgx'

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-primary)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 24,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 16 }}>{isDgx ? '⚡' : '☁️'}</span>
        <p style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
          color: 'var(--accent-blue)',
          margin: 0,
        }}>
          Analysis in progress{dots}
        </p>
      </div>
      <p style={{
        fontFamily: 'var(--font-body)',
        fontSize: 14,
        color: 'var(--text-secondary)',
        maxWidth: 420,
        textAlign: 'center',
        lineHeight: 1.7,
        margin: 0,
      }}>
        Running the 4-round pipeline — Strategist, UX Analyst, Market Researcher, and Partner Review.
        {isDgx
          ? ' Running sequentially with thermal management on the DGX Spark. Typically 15–45 minutes.'
          : ' Running analysts in parallel via OpenAI GPT-4o. Typically 2–5 minutes.'}
      </p>
      <p style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        color: 'var(--text-muted)',
        letterSpacing: '0.08em',
        margin: 0,
      }}>
        {isDgx ? 'Thermal governor active — cooling pauses between rounds.' : 'Parallel inference — no GPU constraints.'}
        {' '}This page checks for updates every 10 seconds.
      </p>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Loading Skeleton
// ─────────────────────────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ maxWidth: 900, width: '100%', padding: '0 40px' }}>
        <div className="report-skeleton" style={{ height: 12, width: '30%', marginBottom: 24 }} />
        <div className="report-skeleton" style={{ height: 52, width: '80%', marginBottom: 16 }} />
        <div className="report-skeleton" style={{ height: 52, width: '60%', marginBottom: 40 }} />
        <div className="report-skeleton" style={{ height: 120, width: 120, borderRadius: '50%', marginBottom: 32 }} />
        <div className="report-skeleton" style={{ height: 14, width: '70%', marginBottom: 10 }} />
        <div className="report-skeleton" style={{ height: 14, width: '55%' }} />
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────

interface ReportProps {
  sessionId: string
}

export default function Report({ sessionId }: ReportProps) {
  const [data, setData] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [currentMode, setCurrentMode] = useState<ExecutionMode | undefined>(undefined)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Fetch current execution mode for the analyzing screen
  useEffect(() => {
    fetch(`${API_BASE}/api/config/mode`)
      .then(r => r.json())
      .then((d: { mode: ExecutionMode }) => setCurrentMode(d.mode))
      .catch(() => {/* non-critical */})
  }, [])

  const fetchReport = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/report/${sessionId}`)
      if (res.status === 202) {
        setAnalyzing(true)
        setLoading(false)
        pollTimerRef.current = setTimeout(() => { void fetchReport() }, 10_000)
        return
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json() as ReportData
      setAnalyzing(false)
      setData(json)
    } catch {
      setData(MOCK_DATA)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    void fetchReport()
    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    }
  }, [fetchReport])

  if (loading) return <LoadingSkeleton />
  if (analyzing) return <AnalyzingScreen mode={currentMode} />
  if (!data) return null

  return (
    <div
      ref={containerRef}
      style={{
        minHeight: '100vh',
        background: 'var(--bg-primary)',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-body)',
      }}
    >
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '0 40px 120px' }}>

        {/* Section 1: Hero */}
        <HeroSection data={data} />

        {/* Divider */}
        <div style={{ height: 1, background: 'var(--border)', margin: '0 0 80px' }} />

        {/* Section 2: Analyst Scores */}
        <div style={{ marginBottom: 80 }}>
          <AnalystScoresSection data={data} />
        </div>

        {/* Section 3: Comparison Cards */}
        <div style={{ marginBottom: 80 }}>
          <ComparisonCardsSection data={data} />
        </div>

        {/* Section 4: Risks & Opportunities */}
        <div style={{ marginBottom: 80 }}>
          <RisksOpportunitiesSection data={data} />
        </div>

        {/* Section 5: Market Intelligence */}
        <div style={{ marginBottom: 80 }}>
          <MarketIntelligenceSection data={data} />
        </div>

        {/* Section 6: Friction Map */}
        <div style={{ marginBottom: 80 }}>
          <FrictionMapSection data={data} />
        </div>

        {/* Section 7: Partner's Verdict */}
        <div style={{ marginBottom: 80 }}>
          <PartnerVerdictSection data={data} />
        </div>

        {/* Footer */}
        <div style={{
          borderTop: '1px solid var(--border)',
          paddingTop: 32,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12,
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
            War Room · {data.product_name} · {formatDate(data.analysis_timestamp)}
          </span>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <button
              className="pdf-btn"
              onClick={() => window.print()}
            >
              <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
              </svg>
              Export PDF
            </button>
            <button
              className="pdf-btn"
              onClick={() => { window.location.href = '/' }}
            >
              ← New Analysis
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}
