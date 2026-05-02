"""
Market Intelligence — pulls live marketing strategy data for a given business profile.
Uses Claude with web search (via Gemini search tool fallback) to gather:
  - Current industry advertising trends
  - Competitor insights
  - Platform algorithm updates relevant to the business
  - Best-performing content types for the industry right now
"""
import os
import json
from typing import Optional

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")


def research_business(business_profile: dict) -> str:
    """
    Run live market research for a business profile.
    Returns a rich text summary of current market intelligence.

    Tries Claude first (no native search yet — uses knowledge),
    then tries Gemini with Google Search for real-time data.
    """
    industry   = business_profile.get("industry", "business")
    location   = business_profile.get("location", "Australia")
    biz_type   = business_profile.get("business_type", "local_service")
    budget     = business_profile.get("monthly_budget", 500)
    competitors = business_profile.get("competitors", [])
    if isinstance(competitors, str):
        try:
            competitors = json.loads(competitors)
        except Exception:
            competitors = []

    # Try Gemini with live Google Search first (most current data)
    if GEMINI_API_KEY:
        result = _research_via_gemini(industry, location, biz_type, budget, competitors)
        if result:
            return result

    # Fall back to Claude knowledge-based research
    if ANTHROPIC_API_KEY:
        result = _research_via_claude(industry, location, biz_type, budget, competitors)
        if result:
            return result

    return _static_research(industry, location)


def _research_via_gemini(industry: str, location: str, biz_type: str,
                          budget: float, competitors: list) -> Optional[str]:
    """Use Gemini with Google Search grounding for live research."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        comp_str = ", ".join(str(c) for c in competitors[:3]) if competitors else "not specified"

        prompt = f"""You are a digital marketing researcher. Research the following and provide
a comprehensive marketing intelligence report.

Business Context:
- Industry: {industry}
- Business Type: {biz_type}
- Location: {location}
- Monthly Budget: ~${budget} AUD
- Known Competitors: {comp_str}

Research and report on:
1. Current advertising trends in the {industry} industry in {location} (2025)
2. What types of social media content are performing best for {biz_type} businesses right now
3. Current Facebook/Instagram ad costs and benchmarks for {industry} in Australia
4. Top marketing strategies working for local {industry} businesses today
5. Any recent platform algorithm changes affecting {biz_type} businesses
6. Competitor marketing tactics being used in this space
7. Underutilised marketing channels for {industry} businesses that have high ROI

Be specific, data-driven, and current. Focus on actionable insights."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                max_output_tokens=3000,
                temperature=0.3,
            ),
        )
        return response.text
    except Exception:
        return None


def _research_via_claude(industry: str, location: str, biz_type: str,
                          budget: float, competitors: list) -> Optional[str]:
    """Use Claude's knowledge base for market research (no live search)."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        comp_str = ", ".join(str(c) for c in competitors[:3]) if competitors else "not specified"

        prompt = f"""You are a senior digital marketing strategist specialising in {location} markets.
Provide a comprehensive marketing intelligence briefing for a {biz_type} business in the {industry} industry.

Business context: Located in {location}, monthly budget ~${budget} AUD, competitors: {comp_str}

Cover:
1. Most effective advertising channels for {industry} businesses with this budget in 2025
2. Content types and formats getting the best organic reach right now
3. Facebook/Instagram ad strategy for {biz_type} businesses (targeting, formats, objectives)
4. Google Ads strategy if budget supports it
5. Specific tactics competitors in {industry} are using successfully
6. 3 quick wins achievable within the first 30 days
7. Common mistakes {biz_type} businesses make with advertising (and how to avoid them)
8. Expected benchmarks: CPM, CPC, CTR, conversion rate for this industry/location

Be specific and actionable. Tailor advice to the {location} market."""

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception:
        return None


def _static_research(industry: str, location: str) -> str:
    """Minimal static fallback when no API keys are available."""
    return f"""## Market Intelligence for {industry} in {location}

**Key 2025 Advertising Trends:**
- Short-form video (Reels, TikTok) continues to outperform static images by 3-4x on reach
- Facebook/Instagram lead ads reduce friction — users convert without leaving the platform
- Google Search ads remain the highest-intent traffic source for local service businesses
- User-generated content and testimonials outperform polished brand content on trust metrics

**Recommended Channel Mix for Local Businesses:**
- Facebook/Instagram: 50-60% of budget (best for awareness + lead gen)
- Google Ads: 25-35% of budget (captures active searchers)
- Organic content: 10-15% of budget (builds long-term authority)

**Content Best Practices:**
- Behind-the-scenes content drives 2x engagement vs. product-only posts
- Posts with questions in captions get 50% more comments
- Consistent posting (4-5x/week) builds algorithm trust faster than sporadic posting

**Local Business Quick Wins:**
1. Google Business Profile fully optimised — appears in local map searches for free
2. Collect and display customer reviews — 88% of people trust online reviews as much as personal recommendations
3. Facebook remarketing to website visitors — 10x cheaper than cold traffic

Note: Connect your ANTHROPIC_API_KEY or GEMINI_API_KEY for live, personalised market research."""


def get_competitor_insights(competitors: list, industry: str) -> str:
    """
    Analyse specific competitors and return strategic insights.
    Used in the ad plan to differentiate the client's strategy.
    """
    if not competitors or (not ANTHROPIC_API_KEY and not GEMINI_API_KEY):
        return ""

    comp_str = ", ".join(str(c) for c in competitors[:5])

    if GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"""Research these {industry} competitors: {comp_str}
Analyse their social media strategy, ad approach, and positioning.
What are they doing well? What gaps can we exploit?
Be specific and actionable.""",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    max_output_tokens=1500,
                    temperature=0.3,
                ),
            )
            return response.text
        except Exception:
            pass

    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                messages=[{"role": "user", "content": f"""Analyse these {industry} competitors: {comp_str}
Based on typical strategies in this industry, what are they likely doing for marketing?
What positioning gaps can we exploit? What should we do DIFFERENTLY to stand out?"""}],
            )
            return response.content[0].text
        except Exception:
            pass

    return ""
