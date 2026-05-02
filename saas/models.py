"""
Model Registry — all supported AI models across providers.
Single source of truth for model IDs, costs, capabilities, and display metadata.
Used by the model picker UI and the AI writer.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class AIModel:
    id: str                      # API model ID (exact string to pass to API)
    name: str                    # Display name
    provider: str                # 'anthropic' | 'google' | 'openai'
    provider_label: str          # 'Claude (Anthropic)' etc.
    tier: str                    # 'premium' | 'standard' | 'economy'
    cost_input_per_m: float      # USD per 1M input tokens
    cost_output_per_m: float     # USD per 1M output tokens
    context_window: int          # Max tokens in context window
    description: str             # One-line capability description
    best_for: list               # List of use-case tags
    speed: str                   # 'fast' | 'medium' | 'slow'
    supports_vision: bool = False
    supports_search: bool = False  # Has built-in web search
    is_recommended: bool = False   # Show "Recommended" badge

ALL_MODELS: list[AIModel] = [

    # ── Anthropic Claude ──────────────────────────────────────────────────────
    AIModel(
        id="claude-opus-4-7",
        name="Claude Opus 4.7",
        provider="anthropic",
        provider_label="Anthropic",
        tier="premium",
        cost_input_per_m=15.0,
        cost_output_per_m=75.0,
        context_window=200000,
        description="Most powerful Claude. Best reasoning, complex strategy, nuanced writing.",
        best_for=["complex_plans", "long_strategy", "nuanced_writing"],
        speed="slow",
        supports_vision=True,
    ),
    AIModel(
        id="claude-sonnet-4-6",
        name="Claude Sonnet 4.6",
        provider="anthropic",
        provider_label="Anthropic",
        tier="standard",
        cost_input_per_m=3.0,
        cost_output_per_m=15.0,
        context_window=200000,
        description="Best balance of intelligence and speed. Ideal for ad plans, chat, and content.",
        best_for=["ad_plans", "chat", "content_writing", "onboarding"],
        speed="medium",
        supports_vision=True,
        is_recommended=True,
    ),
    AIModel(
        id="claude-haiku-4-5",
        name="Claude Haiku 4.5",
        provider="anthropic",
        provider_label="Anthropic",
        tier="economy",
        cost_input_per_m=0.80,
        cost_output_per_m=4.0,
        context_window=200000,
        description="Fastest Claude. Great for quick posts, hashtags, and high-volume tasks.",
        best_for=["quick_posts", "hashtags", "bulk_content"],
        speed="fast",
        supports_vision=True,
    ),

    # ── Google Gemini ─────────────────────────────────────────────────────────
    AIModel(
        id="gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        provider="google",
        provider_label="Google",
        tier="premium",
        cost_input_per_m=1.25,
        cost_output_per_m=10.0,
        context_window=1000000,
        description="Google's most capable model. 1M token context. Great for deep research.",
        best_for=["market_research", "long_documents", "complex_analysis"],
        speed="slow",
        supports_vision=True,
        supports_search=True,
    ),
    AIModel(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider="google",
        provider_label="Google",
        tier="standard",
        cost_input_per_m=0.10,
        cost_output_per_m=0.40,
        context_window=1000000,
        description="Fast, cheap, excellent for market research with live Google Search.",
        best_for=["market_research", "quick_content", "search_grounding"],
        speed="fast",
        supports_vision=True,
        supports_search=True,
        is_recommended=True,
    ),
    AIModel(
        id="gemini-1.5-flash",
        name="Gemini 1.5 Flash",
        provider="google",
        provider_label="Google",
        tier="economy",
        cost_input_per_m=0.075,
        cost_output_per_m=0.30,
        context_window=1000000,
        description="Budget option with generous free tier (1,500 req/day free).",
        best_for=["budget_content", "free_tier", "high_volume"],
        speed="fast",
        supports_vision=True,
        supports_search=True,
    ),

    # ── OpenAI ────────────────────────────────────────────────────────────────
    AIModel(
        id="gpt-4o",
        name="GPT-4o",
        provider="openai",
        provider_label="OpenAI",
        tier="premium",
        cost_input_per_m=2.50,
        cost_output_per_m=10.0,
        context_window=128000,
        description="OpenAI's flagship. Strong at creative writing and structured output.",
        best_for=["creative_writing", "structured_output", "content_writing"],
        speed="medium",
        supports_vision=True,
    ),
    AIModel(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider="openai",
        provider_label="OpenAI",
        tier="economy",
        cost_input_per_m=0.15,
        cost_output_per_m=0.60,
        context_window=128000,
        description="Affordable GPT-4 class. Good for bulk content at low cost.",
        best_for=["bulk_content", "simple_posts", "low_cost"],
        speed="fast",
        supports_vision=True,
    ),
]

# ── Quick lookups ──────────────────────────────────────────────────────────────

MODEL_BY_ID: dict[str, AIModel] = {m.id: m for m in ALL_MODELS}

MODELS_BY_PROVIDER: dict[str, list[AIModel]] = {}
for _m in ALL_MODELS:
    MODELS_BY_PROVIDER.setdefault(_m.provider, []).append(_m)

PROVIDER_ICONS = {
    "anthropic": "🟣",
    "google":    "🔵",
    "openai":    "🟢",
}

PROVIDER_COLORS = {
    "anthropic": "#7C3AED",
    "google":    "#1877F2",
    "openai":    "#10A37F",
}

TIER_BADGE = {
    "premium":  ("PREMIUM",  "#F59E0B"),
    "standard": ("STANDARD", "#7C3AED"),
    "economy":  ("ECONOMY",  "#22C55E"),
}


def get_model(model_id: str) -> Optional[AIModel]:
    return MODEL_BY_ID.get(model_id)


def models_for_provider(provider: str) -> list[AIModel]:
    return MODELS_BY_PROVIDER.get(provider, [])


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Return estimated USD cost for a call."""
    m = get_model(model_id)
    if not m:
        return 0.0
    return (input_tokens / 1_000_000 * m.cost_input_per_m +
            output_tokens / 1_000_000 * m.cost_output_per_m)


def monthly_cost_estimate(model_id: str, usage_level: str = "medium") -> float:
    """
    Rough monthly cost estimate in USD.
    usage_level: 'light' | 'medium' | 'heavy'
    Based on typical SocialAI usage patterns.
    """
    # Approximate token usage per month at each level
    USAGE = {
        "light":  {"input": 50_000,  "output": 30_000},
        "medium": {"input": 200_000, "output": 120_000},
        "heavy":  {"input": 800_000, "output": 500_000},
    }
    u = USAGE.get(usage_level, USAGE["medium"])
    return estimate_cost(model_id, u["input"], u["output"])


# Default models per use-case (used when no subscriber preference is set)
DEFAULTS = {
    "onboarding":         "claude-sonnet-4-6",
    "ad_plan":            "claude-sonnet-4-6",
    "chat":               "claude-sonnet-4-6",
    "content_writing":    "claude-sonnet-4-6",
    "market_research":    "gemini-2.0-flash",
    "image_generation":   "dall-e-3",       # OpenAI image model — separate pipeline
}
