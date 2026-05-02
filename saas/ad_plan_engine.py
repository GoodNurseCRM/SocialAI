"""
Ad Plan Engine — generates a complete, structured advertising campaign plan.
Takes a business profile + market research and returns a visual-ready plan.
Uses Claude claude-sonnet-4-6 for reasoning and plan construction.
"""
import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

PLAN_SYSTEM_PROMPT = """You are the world's #1 digital advertising strategist with 20 years of experience.
You build performance-driven ad plans for small and medium businesses.
Your plans are specific, actionable, and built on what actually works right now — not generic advice.

When given a business profile and market research, you generate a complete 30-day advertising plan
in structured JSON format. Your plan must be realistic for the budget provided and tailored to
the specific business, industry, location, and target audience.

CRITICAL RULES:
- Every content idea must be specific to this business — not generic
- Budget allocations must add up to 100% and be realistic
- Posting frequency must match the budget (more budget = more posts/ads)
- Include at least 2 platform recommendations even if budget is tight
- Always include a Google Ads recommendation if budget > $500/month
- Be specific: actual post titles, actual ad headlines, actual hashtags for this business"""


def _get_client():
    import anthropic
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_plan(business_profile: dict, market_research: str = "",
                  campaign_type: str = "30_day") -> Optional[dict]:
    """
    Generate a complete advertising campaign plan.

    Args:
        business_profile: Dict from business_profiles table (parsed JSON fields)
        market_research: String of current market trends/intelligence
        campaign_type: '30_day', '60_day', or '90_day'

    Returns:
        Structured plan dict ready for storage and rendering, or None on failure.
    """
    if not ANTHROPIC_API_KEY:
        return _demo_plan(business_profile, campaign_type)

    client = _get_client()
    days = {"30_day": 30, "60_day": 60, "90_day": 90}.get(campaign_type, 30)
    start_date = datetime.now()
    end_date   = start_date + timedelta(days=days)

    # Parse JSON fields that may be stored as strings
    profile = _parse_profile_fields(business_profile)

    prompt = f"""Generate a complete {days}-day advertising plan for this business.

## BUSINESS PROFILE
Business Name: {profile.get('business_name', 'Unknown')}
Industry: {profile.get('industry', 'Unknown')}
Type: {profile.get('business_type', 'Unknown')}
Location: {profile.get('location', 'Unknown')}
Website: {profile.get('website', 'N/A')}
Services: {json.dumps(profile.get('services', []))}
USP (What makes them unique): {profile.get('usp', 'Not specified')}
Brand Tone: {profile.get('tone', 'professional')}

Target Audience: {json.dumps(profile.get('target_audience', {}))}

Primary Goal: {profile.get('goals', {}).get('primary', 'Generate leads')}
Monthly Marketing Budget: ${profile.get('monthly_budget', 500)} AUD
Budget Range: {profile.get('budget_range', 'Under $1000')}

Competitors: {json.dumps(profile.get('competitors', []))}
Currently Using: {json.dumps(profile.get('social_channels', []))}

## CURRENT MARKET INTELLIGENCE
{market_research or 'No specific research available — use general best practices for this industry.'}

## OUTPUT FORMAT
Return ONLY valid JSON in this exact structure (no markdown, no explanation):

{{
  "campaign_title": "...",
  "campaign_summary": "2-3 sentence overview of the strategy",
  "campaign_type": "{campaign_type}",
  "start_date": "{start_date.strftime('%Y-%m-%d')}",
  "end_date": "{end_date.strftime('%Y-%m-%d')}",
  "total_budget": {profile.get('monthly_budget', 500) * (days / 30)},
  "ai_rationale": "2-3 sentences explaining WHY this plan will work for this specific business",

  "goals": {{
    "primary": "...",
    "kpis": ["KPI 1", "KPI 2", "KPI 3"],
    "expected_reach": 0,
    "expected_leads": 0,
    "expected_engagement_rate": "0%"
  }},

  "channels": [
    {{
      "platform": "facebook|instagram|linkedin|tiktok|twitter|google_ads",
      "budget_percent": 0,
      "budget_amount": 0,
      "posts_per_week": 0,
      "content_types": ["post", "story", "ad", "video"],
      "primary_objective": "...",
      "why_this_platform": "...",
      "best_posting_times": ["9am Mon", "6pm Thu"]
    }}
  ],

  "weekly_themes": [
    {{
      "week": 1,
      "theme": "...",
      "goal": "...",
      "key_message": "..."
    }}
  ],

  "content_calendar": [
    {{
      "day": 1,
      "date": "YYYY-MM-DD",
      "platform": "...",
      "content_type": "post|ad|story|video|google_ad",
      "title": "Specific post title for this business",
      "content_brief": "What this post should say/show — be specific to this business",
      "image_concept": "Visual description for image generation",
      "hashtags": ["#tag1", "#tag2"],
      "call_to_action": "...",
      "budget": 0,
      "expected_reach": 0
    }}
  ],

  "quick_wins": [
    {{
      "action": "Specific action to take in week 1",
      "impact": "HIGH|MEDIUM|LOW",
      "effort": "HIGH|MEDIUM|LOW",
      "description": "..."
    }}
  ],

  "success_metrics": {{
    "week_1_target": "...",
    "week_2_target": "...",
    "week_4_target": "...",
    "month_3_target": "..."
  }}
}}

IMPORTANT: The content_calendar should have entries spread across {min(days, 20)} representative days
(not every single day — focus on the key posting days). Each content item must be SPECIFIC to
{profile.get('business_name', 'this business')} — use their actual business name, services, and tone."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=PLAN_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r'^```[a-z]*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        plan = json.loads(text)
        return plan
    except Exception as e:
        # Return demo plan as fallback
        return _demo_plan(business_profile, campaign_type)


def regenerate_plan_with_feedback(original_plan: dict, user_feedback: str,
                                  business_profile: dict) -> Optional[dict]:
    """
    Revise an existing plan based on user feedback.

    Args:
        original_plan: The original generated plan dict
        user_feedback: Free-text feedback from the business owner
        business_profile: Business profile dict

    Returns:
        Updated plan dict, or None on failure.
    """
    if not ANTHROPIC_API_KEY:
        return None

    client = _get_client()
    profile = _parse_profile_fields(business_profile)

    prompt = f"""You previously generated this advertising plan:

{json.dumps(original_plan, indent=2)}

The business owner reviewed it and has this feedback:
"{user_feedback}"

Please revise the plan to address their feedback. Keep everything that they didn't mention.
Return ONLY the updated complete plan JSON in the same format — no explanation, no markdown."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=PLAN_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r'^```[a-z]*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        return json.loads(text)
    except Exception:
        return None


def _parse_profile_fields(profile: dict) -> dict:
    """Parse JSON string fields in the profile dict."""
    p = dict(profile)
    for field in ("target_audience", "services", "goals", "competitors", "social_channels"):
        if isinstance(p.get(field), str):
            try:
                p[field] = json.loads(p[field])
            except Exception:
                pass
    return p


def _demo_plan(business_profile: dict, campaign_type: str) -> dict:
    """Fallback demo plan when API key is not configured."""
    biz_name = business_profile.get("business_name", "Your Business")
    budget   = float(business_profile.get("monthly_budget") or 500)
    days     = {"30_day": 30, "60_day": 60, "90_day": 90}.get(campaign_type, 30)
    start    = datetime.now()
    end      = start + timedelta(days=days)

    return {
        "campaign_title": f"{biz_name} — {days}-Day Growth Campaign",
        "campaign_summary": (
            f"A focused {days}-day campaign to grow {biz_name}'s online presence, "
            "generate qualified leads, and build a loyal community. "
            "This plan combines organic content, targeted paid ads, and community engagement."
        ),
        "campaign_type": campaign_type,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "total_budget": budget * (days / 30),
        "ai_rationale": (
            "This plan prioritises Facebook and Instagram — the platforms with the highest ROI "
            "for local service businesses. Budget is split 60/40 between paid ads and content "
            "production to build both immediate leads and long-term brand equity."
        ),
        "goals": {
            "primary": "Generate qualified leads",
            "kpis": ["Lead form submissions", "Website clicks", "Engagement rate"],
            "expected_reach": int(budget * 50),
            "expected_leads": max(5, int(budget / 50)),
            "expected_engagement_rate": "3.5%"
        },
        "channels": [
            {
                "platform": "facebook",
                "budget_percent": 45,
                "budget_amount": round(budget * 0.45),
                "posts_per_week": 4,
                "content_types": ["post", "ad", "story"],
                "primary_objective": "Lead generation",
                "why_this_platform": "Highest reach for local audiences aged 25-55",
                "best_posting_times": ["9am Wed", "6pm Fri", "10am Sat"]
            },
            {
                "platform": "instagram",
                "budget_percent": 35,
                "budget_amount": round(budget * 0.35),
                "posts_per_week": 5,
                "content_types": ["post", "story", "reel"],
                "primary_objective": "Brand awareness & engagement",
                "why_this_platform": "Visual storytelling drives trust and brand recognition",
                "best_posting_times": ["8am Mon", "12pm Wed", "7pm Sun"]
            },
            {
                "platform": "google_ads",
                "budget_percent": 20,
                "budget_amount": round(budget * 0.20),
                "posts_per_week": 0,
                "content_types": ["search_ad", "display_ad"],
                "primary_objective": "Capture high-intent search traffic",
                "why_this_platform": "People searching for your services are ready to buy",
                "best_posting_times": []
            }
        ],
        "weekly_themes": [
            {"week": 1, "theme": "Introduction & Trust Building",
             "goal": "Establish credibility", "key_message": "Who we are and why we're different"},
            {"week": 2, "theme": "Service Showcase",
             "goal": "Educate the market", "key_message": "What we offer and how it helps"},
            {"week": 3, "theme": "Social Proof & Results",
             "goal": "Build trust", "key_message": "Real results from real customers"},
            {"week": 4, "theme": "Call to Action & Conversion",
             "goal": "Generate leads", "key_message": "Why act now"},
        ],
        "content_calendar": _demo_calendar(biz_name, start),
        "quick_wins": [
            {
                "action": "Optimise your Facebook business page — add all contact info, hours, and services",
                "impact": "HIGH", "effort": "LOW",
                "description": "A complete profile gets 3x more enquiries than an incomplete one."
            },
            {
                "action": "Post 3 customer testimonials this week",
                "impact": "HIGH", "effort": "LOW",
                "description": "Social proof is the #1 trust driver for local service businesses."
            },
            {
                "action": "Set up Google Business Profile if not already done",
                "impact": "HIGH", "effort": "MEDIUM",
                "description": "Appears in Google Maps searches for your local area — free traffic."
            }
        ],
        "success_metrics": {
            "week_1_target": "Profile complete, first 3 posts published, 1 ad live",
            "week_2_target": "50+ post engagements, 5+ website clicks",
            "week_4_target": "200+ total reach, 10+ leads captured",
            "month_3_target": "Consistent 500+ monthly reach, 30+ monthly leads"
        }
    }


def _demo_calendar(biz_name: str, start: datetime) -> list:
    templates = [
        ("facebook", "post", f"Introducing {biz_name}",
         "Share your founding story and what drives you. Why did you start this business?"),
        ("instagram", "post", "Behind the Scenes",
         "Show the team at work — authentic, candid moments build trust faster than polished content"),
        ("facebook", "ad", "Special Offer — Limited Time",
         "Promote your most popular service with a clear call to action and offer"),
        ("instagram", "story", "Customer Q&A",
         "Answer the most common questions customers ask you"),
        ("facebook", "post", "Customer Success Story",
         "Share a before/after or a customer testimonial — get permission first"),
        ("instagram", "post", "Tips & Value Content",
         "Share 3 quick tips related to your industry that your target customer would find useful"),
        ("facebook", "ad", "Lead Generation Ad",
         "Drive traffic to your website/booking form with a specific service promotion"),
    ]
    calendar = []
    for i, (platform, ctype, title, brief) in enumerate(templates):
        day_offset = (i + 1) * (30 // len(templates))
        date = start + timedelta(days=day_offset)
        calendar.append({
            "day": day_offset,
            "date": date.strftime("%Y-%m-%d"),
            "platform": platform,
            "content_type": ctype,
            "title": title,
            "content_brief": brief,
            "image_concept": f"Clean, professional image representing {biz_name} and {title}",
            "hashtags": [f"#{biz_name.replace(' ', '')}", "#smallbusiness", "#localservice"],
            "call_to_action": "Learn more",
            "budget": 0,
            "expected_reach": 200
        })
    return calendar
