"""
Onboarding Agent — Claude-powered conversational business interview.
Asks smart questions to build a complete business profile.
Returns structured JSON ready to store in business_profiles table.
"""
import os
import json
import re
from typing import Optional

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """You are a friendly, expert marketing consultant named Alex.
Your job is to interview a business owner to understand their business deeply so you can create
a powerful, personalised advertising plan for them.

## Your Personality
- Warm, enthusiastic, and professional
- Ask ONE question at a time — never multiple questions in the same message
- After each answer, acknowledge what they said briefly before asking the next question
- Be encouraging — make the business owner feel their business is exciting
- Sound like a real person having a real conversation, not a form

## Information You Need to Collect
Collect ALL of the following (track internally what you have vs. haven't asked yet):

1. **business_name** — What is the name of their business?
2. **industry** — What industry are they in? (e.g., healthcare, retail, restaurant, fitness, etc.)
3. **services** — What specific products or services do they offer? Any pricing?
4. **location** — Where is the business located? (city/suburb/region) Is it local-only or can they serve customers online?
5. **target_audience** — Who is their ideal customer? (age, gender, income level, interests, what problems they solve)
6. **usp** — What makes them different from competitors? Why should a customer choose them?
7. **goals** — What is their #1 marketing goal right now? (get more leads, grow awareness, drive sales, build community)
8. **monthly_budget** — What is their monthly marketing budget? (approximate is fine — give ranges: under $500, $500-$1500, $1500-$5000, $5000+)
9. **competitors** — Who are their main 2-3 competitors?
10. **tone** — How would they describe their brand personality? (professional, casual/friendly, luxury/premium, playful, authoritative)
11. **current_channels** — What marketing channels are they using now? (Facebook, Instagram, Google Ads, etc.) What's working?
12. **website** — Do they have a website? What's the URL?

## Rules
- Ask about business_name FIRST if you don't know it
- After you have all 12 pieces of information, do NOT ask more questions
- When you have everything, output EXACTLY this JSON block (no other text around it):

```json_profile
{
  "business_name": "...",
  "industry": "...",
  "business_type": "...",
  "location": "...",
  "website": "...",
  "services": [...],
  "target_audience": {
    "description": "...",
    "age_range": "...",
    "interests": [...],
    "pain_points": [...]
  },
  "usp": "...",
  "goals": {
    "primary": "...",
    "secondary": []
  },
  "monthly_budget": 0,
  "budget_range": "...",
  "tone": "...",
  "competitors": [...],
  "social_channels": [...],
  "ready_for_plan": true
}
```

- business_type should be one of: local_service, ecommerce, restaurant, healthcare, fitness, education, real_estate, professional_services, retail, saas, other
- monthly_budget should be the midpoint number of the range they gave (e.g., "$500-$1500" → 1000)
- Keep all values concise and factual"""


def _get_client():
    import anthropic
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def chat(conversation_history: list, user_message: str) -> tuple[str, Optional[dict]]:
    """
    Send a message in the onboarding conversation.

    Args:
        conversation_history: List of {"role": "user"|"assistant", "content": str}
        user_message: The latest user input

    Returns:
        (assistant_reply, extracted_profile_or_None)
        If the profile JSON is detected in the reply, it's parsed and returned.
    """
    if not ANTHROPIC_API_KEY:
        return (
            "Hi! I'm Alex, your marketing consultant. To get started, I'll need an Anthropic API key "
            "configured. Please add ANTHROPIC_API_KEY to your .env file.",
            None
        )

    client = _get_client()

    messages = list(conversation_history)
    messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    reply = response.content[0].text
    profile = _extract_profile(reply)

    return reply, profile


def start_conversation() -> str:
    """Return the opening message from the onboarding agent."""
    if not ANTHROPIC_API_KEY:
        return (
            "⚠️ Anthropic API key not configured. Please add ANTHROPIC_API_KEY to your .env file "
            "and restart the app."
        )

    client = _get_client()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": "Hi, I just signed up and I'm ready to set up my business profile."
        }],
    )
    return response.content[0].text


def _extract_profile(text: str) -> Optional[dict]:
    """Parse the structured JSON block from the agent response, if present."""
    match = re.search(r'```json_profile\s*(.*?)\s*```', text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def build_profile_from_answers(raw_conversation: list) -> Optional[dict]:
    """
    Force-extract a business profile from a completed conversation using Claude.
    Used as fallback if the agent didn't output JSON naturally.
    """
    if not ANTHROPIC_API_KEY:
        return None

    client = _get_client()

    convo_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in raw_conversation
    )

    extraction_prompt = f"""Based on this onboarding conversation, extract the business profile as JSON.

Conversation:
{convo_text}

Output ONLY valid JSON (no markdown, no explanation):
{{
  "business_name": "...",
  "industry": "...",
  "business_type": "local_service|ecommerce|restaurant|healthcare|fitness|education|real_estate|professional_services|retail|saas|other",
  "location": "...",
  "website": "...",
  "services": ["service1", "service2"],
  "target_audience": {{
    "description": "...",
    "age_range": "...",
    "interests": [],
    "pain_points": []
  }},
  "usp": "...",
  "goals": {{
    "primary": "...",
    "secondary": []
  }},
  "monthly_budget": 0,
  "budget_range": "...",
  "tone": "professional|casual|luxury|playful|authoritative",
  "competitors": [],
  "social_channels": [],
  "ready_for_plan": true
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": extraction_prompt}],
    )

    try:
        text = response.content[0].text.strip()
        # Strip markdown code fences if present
        text = re.sub(r'^```[a-z]*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        return json.loads(text)
    except Exception:
        return None
