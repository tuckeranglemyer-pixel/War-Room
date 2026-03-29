from dataclasses import dataclass
from typing import List


DELIVERABLE_SCHEMA = """{
  "product_name": "string",
  "product_description": "string",
  "target_user": "string",
  "analysis_timestamp": "ISO 8601 string",

  "verdict": {
    "headline": "string — one sentence, max 15 words, the core takeaway",
    "score": "number 1-10, one decimal place",
    "recommendation": "string — 2-3 sentences, what the founder should do FIRST",
    "market_readiness": "NOT_READY | NEEDS_WORK | COMPETITIVE | STRONG | EXCEPTIONAL"
  },

  "strategist_section": {
    "competitive_positioning": "string — 2-3 sentences on where this product sits in the market",
    "top_risks": [
      {
        "risk": "string — one sentence describing the risk",
        "severity": "LOW | MEDIUM | HIGH | CRITICAL",
        "evidence": "string — specific review quote or data point backing this",
        "competitor_learned_from": "string — which competitor hit this same problem"
      }
    ],
    "top_opportunities": [
      {
        "opportunity": "string — one sentence describing the opportunity",
        "impact": "LOW | MEDIUM | HIGH | TRANSFORMATIVE",
        "evidence": "string — specific review quote or data point backing this",
        "competitor_failed_at": "string — which competitor left this gap open"
      }
    ],
    "moat_assessment": "string — 2-3 sentences on whether the differentiator is defensible",
    "strategist_score": "number 1-10",
    "strategist_summary": "string — 3-4 sentences, the strategist's overall take"
  },

  "ux_analyst_section": {
    "comparison_cards": [
      {
        "card_id": "string",
        "user_screen": {
          "frame_number": "number",
          "image_path": "string — relative path to user's frame",
          "screen_label": "string — e.g. 'Dashboard — Main View'",
          "ux_score": "number 1-10",
          "strengths": ["string — max 3 items, each under 12 words"],
          "weaknesses": ["string — max 3 items, each under 12 words"]
        },
        "competitor_screen": {
          "app": "string",
          "filename": "string",
          "image_path": "string — relative path to competitor screenshot",
          "screen_label": "string",
          "ux_score": "number 1-10",
          "strengths": ["string"],
          "weaknesses": ["string"]
        },
        "similarity_score": "number 0-1",
        "comparison_verdict": "USER_BETTER | COMPETITOR_BETTER | COMPARABLE",
        "what_to_steal": "string — one specific design element to adopt from competitor",
        "what_to_avoid": "string — one specific mistake the competitor made"
      }
    ],
    "onboarding_assessment": {
      "score": "number 1-10",
      "time_to_value_estimate": "string — e.g. '~3 minutes', '15+ minutes'",
      "first_action_clarity": "OBVIOUS | FINDABLE | BURIED | MISSING",
      "cognitive_load": "LOW | MODERATE | HIGH | OVERWHELMING",
      "recommendation": "string — 2-3 sentences"
    },
    "friction_map": [
      {
        "screen": "string — which screen",
        "friction_point": "string — what's wrong",
        "severity": "MINOR | MODERATE | MAJOR | BLOCKER",
        "fix_effort": "QUICK_WIN | MODERATE | SIGNIFICANT_REWORK"
      }
    ],
    "ux_analyst_score": "number 1-10",
    "ux_analyst_summary": "string — 3-4 sentences"
  },

  "market_researcher_section": {
    "sentiment_analysis": {
      "overall_sentiment": "NEGATIVE | MIXED | NEUTRAL | POSITIVE | VERY_POSITIVE",
      "sentiment_by_competitor": [
        {
          "app": "string",
          "sentiment": "string",
          "sample_size": "number",
          "top_praise": "string",
          "top_complaint": "string"
        }
      ]
    },
    "killer_quotes": [
      {
        "quote": "string — max 30 words",
        "source": "reddit | hackernews | google_play",
        "app": "string",
        "relevance": "string"
      }
    ],
    "pricing_positioning": {
      "competitor_range": "string",
      "sweet_spot": "string",
      "pricing_insight": "string"
    },
    "adoption_signals": {
      "easy_wins": ["string"],
      "dealbreakers": ["string"]
    },
    "market_researcher_score": "number 1-10",
    "market_researcher_summary": "string — 3-4 sentences"
  },

  "challenge_layer": {
    "contradictions_found": [
      {
        "between": "string",
        "issue": "string",
        "resolution": "string"
      }
    ],
    "blind_spots": ["string"],
    "final_verdict": "string — 3-4 sentences",
    "final_score": "number 1-10, one decimal",
    "confidence": "LOW | MEDIUM | HIGH",
    "one_thing_to_do_monday": "string"
  }
}"""


# ---------------------------------------------------------------------------
# Dataclass mirrors of the schema for type-safe construction
# ---------------------------------------------------------------------------

@dataclass
class Risk:
    risk: str
    severity: str
    evidence: str
    competitor_learned_from: str


@dataclass
class Opportunity:
    opportunity: str
    impact: str
    evidence: str
    competitor_failed_at: str


@dataclass
class StrategistSection:
    competitive_positioning: str
    top_risks: List[Risk]
    top_opportunities: List[Opportunity]
    moat_assessment: str
    strategist_score: float
    strategist_summary: str


@dataclass
class UserScreen:
    frame_number: int
    image_path: str
    screen_label: str
    ux_score: float
    strengths: List[str]
    weaknesses: List[str]


@dataclass
class CompetitorScreen:
    app: str
    filename: str
    image_path: str
    screen_label: str
    ux_score: float
    strengths: List[str]
    weaknesses: List[str]


@dataclass
class ComparisonCard:
    card_id: str
    user_screen: UserScreen
    competitor_screen: CompetitorScreen
    similarity_score: float
    comparison_verdict: str
    what_to_steal: str
    what_to_avoid: str


@dataclass
class OnboardingAssessment:
    score: float
    time_to_value_estimate: str
    first_action_clarity: str
    cognitive_load: str
    recommendation: str


@dataclass
class FrictionPoint:
    screen: str
    friction_point: str
    severity: str
    fix_effort: str


@dataclass
class UXAnalystSection:
    comparison_cards: List[ComparisonCard]
    onboarding_assessment: OnboardingAssessment
    friction_map: List[FrictionPoint]
    ux_analyst_score: float
    ux_analyst_summary: str


@dataclass
class SentimentByCompetitor:
    app: str
    sentiment: str
    sample_size: int
    top_praise: str
    top_complaint: str


@dataclass
class SentimentAnalysis:
    overall_sentiment: str
    sentiment_by_competitor: List[SentimentByCompetitor]


@dataclass
class KillerQuote:
    quote: str
    source: str
    app: str
    relevance: str


@dataclass
class PricingPositioning:
    competitor_range: str
    sweet_spot: str
    pricing_insight: str


@dataclass
class AdoptionSignals:
    easy_wins: List[str]
    dealbreakers: List[str]


@dataclass
class MarketResearcherSection:
    sentiment_analysis: SentimentAnalysis
    killer_quotes: List[KillerQuote]
    pricing_positioning: PricingPositioning
    adoption_signals: AdoptionSignals
    market_researcher_score: float
    market_researcher_summary: str


@dataclass
class Contradiction:
    between: str
    issue: str
    resolution: str


@dataclass
class ChallengeLayer:
    contradictions_found: List[Contradiction]
    blind_spots: List[str]
    final_verdict: str
    final_score: float
    confidence: str
    one_thing_to_do_monday: str


@dataclass
class Verdict:
    headline: str
    score: float
    recommendation: str
    market_readiness: str


@dataclass
class WarRoomDeliverable:
    product_name: str
    product_description: str
    target_user: str
    analysis_timestamp: str
    verdict: Verdict
    strategist_section: StrategistSection
    ux_analyst_section: UXAnalystSection
    market_researcher_section: MarketResearcherSection
    challenge_layer: ChallengeLayer
