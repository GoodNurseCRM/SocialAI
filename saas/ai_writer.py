"""
AI Content Writer — generates post copy for all platforms.
Primary model: Claude claude-sonnet-4-6 (Anthropic).
Fallback chain: Gemini 2.0 Flash → static templates.
"""
import os
from typing import Optional

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_KEY        = os.environ.get("GEMINI_API_KEY", "")


def _get_text_model_for_tier(tier: str) -> tuple[str, str]:
    """
    Return (model_id, provider) for this subscription tier.
    Priority: Claude (anthropic) → Gemini (google) → fallback flash.
    """
    # Claude is available for all tiers if key exists
    if ANTHROPIC_API_KEY:
        return "claude-sonnet-4-6", "anthropic"
    # Fall back to Gemini
    try:
        import saas.db as db
        config = db.get_model_config("text", tier)
        if config and config.get("model_id"):
            return config["model_id"], config.get("provider", "google")
    except Exception:
        pass
    return "gemini-2.0-flash", "google"

def _generate_text(model_id: str, provider: str, prompt: str,
                   temperature: float = 0.9, max_tokens: int = 2000,
                   use_search: bool = False, system: str = "") -> str:
    """Route text generation to the right provider."""
    if provider == "anthropic":
        import anthropic
        ac = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        kwargs = {
            "model": model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        msg = ac.messages.create(**kwargs)
        return msg.content[0].text

    elif provider == "google":
        from google import genai as _genai
        from google.genai import types as _types
        _client = _genai.Client(api_key=GEMINI_KEY)
        cfg_args = {"temperature": temperature, "max_output_tokens": max_tokens}
        if use_search:
            cfg_args["tools"] = [_types.Tool(google_search=_types.GoogleSearch())]
        response = _client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=_types.GenerateContentConfig(**cfg_args),
        )
        return response.text

    elif provider == "openai":
        from openai import OpenAI as _OAI
        oc = _OAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        resp = oc.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content

    else:
        raise ValueError(f"Unknown text provider: {provider}")

PLATFORM_GUIDELINES = {
    "facebook": "Facebook: conversational, 1-3 paragraphs, end with a question to spark engagement, 1-2 emojis max. Optimal length: 100-250 words.",
    "instagram": "Instagram: visually descriptive, punchy opening line, line breaks for readability, 5-10 relevant hashtags at end. Max 2200 chars. Use emojis sparingly.",
    "linkedin": "LinkedIn: professional tone, insightful/thought-leadership angle, first sentence must hook the reader, add value not promotion. 150-300 words.",
    "tiktok": "TikTok: casual/trendy, hook in first line (what happens next?), short punchy sentences, youthful energy, trending language. Under 150 words.",
    "twitter": "Twitter/X: punchy, opinionated, max 280 chars. Lead with the most interesting part. Optional 2-3 hashtags.",
}

def generate_post(topic: str, platform: str, business_name: str = "",
                  business_type: str = "", tone: str = "professional",
                  include_hashtags: bool = True, count: int = 3,
                  tier: str = "free") -> list[str]:
    """
    Generate `count` post variations for a given topic and platform.
    Uses the model configured for this subscription tier.
    Returns list of post text strings.
    """
    guidelines = PLATFORM_GUIDELINES.get(platform, PLATFORM_GUIDELINES["facebook"])
    biz_ctx = f"Business: {business_name} ({business_type}). " if business_name else ""
    model_id, provider = _get_text_model_for_tier(tier)

    prompt = f"""You are an expert social media copywriter.

{biz_ctx}Tone: {tone}.

{guidelines}

Topic: {topic}

Write {count} different post variations for {platform.title()}.
{"Include relevant hashtags." if include_hashtags and platform not in ("twitter",) else ""}

Format your response as JSON array:
[
  {{"version": 1, "post": "...full post text here..."}},
  {{"version": 2, "post": "..."}},
  {{"version": 3, "post": "..."}}
]

Only return valid JSON, no explanation."""

    import json, re
    text = _generate_text(model_id, provider, prompt, temperature=0.9, max_tokens=2000).strip()
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        data = json.loads(match.group())
        return [item["post"] for item in data if "post" in item]
    return [text]

def generate_hashtags(topic: str, platform: str, count: int = 10,
                       tier: str = "free") -> list[str]:
    """Generate relevant hashtags for a topic."""
    model_id, provider = _get_text_model_for_tier(tier)
    prompt = f"Generate {count} relevant hashtags for a {platform} post about: {topic}. Return only hashtags, one per line, with # prefix."
    text = _generate_text(model_id, provider, prompt, temperature=0.7, max_tokens=300)
    lines = text.strip().split("\n")
    return [l.strip() for l in lines if l.strip().startswith("#")][:count]

def generate_image_prompt(post_text: str, platform: str, business_name: str = "",
                           tier: str = "free") -> str:
    """Generate an image generation prompt from post text."""
    model_id, provider = _get_text_model_for_tier(tier)
    prompt = f"""Based on this social media post, generate a concise image generation prompt (under 200 words).
The image should visually represent the post theme for {platform}.
Business: {business_name}

Post text:
{post_text[:500]}

Respond with ONLY the image prompt, nothing else."""
    return _generate_text(model_id, provider, prompt, temperature=0.7, max_tokens=300).strip()

def generate_strategy_brief(user_id: str, business_name: str, business_type: str,
                              platforms: list[str], recent_posts: list[dict],
                              analytics_summary: dict, tier: str = "free") -> str:
    """Generate an AI strategy brief. Uses the best available model for this tier."""
    post_summary = "\n".join([
        f"- [{p['platform']}] {p['content'][:100]}... (engagement: {p.get('total_engagement', 0)})"
        for p in recent_posts[:10]
    ]) or "No recent posts."

    analytics_text = "\n".join([
        f"- {k}: {v}" for k, v in analytics_summary.items()
    ]) or "No analytics data yet."

    prompt = f"""You are a world-class social media strategist.

Business: {business_name} ({business_type})
Active platforms: {', '.join(platforms)}

Recent post performance:
{post_summary}

Analytics (last 30 days):
{analytics_text}

Generate a concise strategy brief with:
1. What's working well (2-3 points)
2. What needs improvement (2-3 points)
3. Top 3 actionable recommendations for this week
4. Best content types for each platform based on data
5. Suggested posting frequency

Be specific, data-driven, and actionable. Format with clear headings."""

    model_id, provider = _get_text_model_for_tier(tier)
    use_search = (provider == "google")
    system = "You are a world-class social media strategist. Be specific, data-driven, and actionable."
    return _generate_text(model_id, provider, prompt,
                          temperature=0.7, max_tokens=3000,
                          use_search=use_search, system=system)
