"""
SaaS Configuration — Subscription tiers, platform definitions, constants.
"""
from dataclasses import dataclass, field
from typing import List, Optional

# ── Subscription Tiers ─────────────────────────────────────────────────────────
@dataclass
class Tier:
    id: str
    name: str
    price_monthly: float          # AUD
    price_yearly: float           # AUD
    platforms: List[str]          # which platforms are allowed
    platform_limit: int           # -1 = unlimited
    ai_images: bool               # image generation enabled at all
    image_gen_limit: int          # AI images per month; 0 = disabled, -1 = unlimited
    post_scheduling: bool         # schedule posts
    analytics: bool               # performance analytics
    ai_strategy_briefs: bool      # daily strategy engine
    google_ads: bool              # Google Ads manager
    posts_per_month: int          # -1 = unlimited
    team_members: int             # users per account
    stripe_price_id_monthly: str  # fill in after Stripe setup
    stripe_price_id_yearly: str   # fill in after Stripe setup
    description: str
    highlight: bool = False       # show as "most popular"

TIERS: dict[str, Tier] = {
    "free": Tier(
        id="free",
        name="Free Trial",
        price_monthly=0,
        price_yearly=0,
        platforms=["facebook"],
        platform_limit=1,
        ai_images=False,
        image_gen_limit=0,          # no image generation on free
        post_scheduling=False,
        analytics=False,
        ai_strategy_briefs=False,
        google_ads=False,
        posts_per_month=10,
        team_members=1,
        stripe_price_id_monthly="",
        stripe_price_id_yearly="",
        description="Try it free — 1 platform, 10 posts/month",
    ),
    "starter": Tier(
        id="starter",
        name="Starter",
        price_monthly=29,
        price_yearly=290,
        platforms=["facebook", "instagram"],
        platform_limit=2,
        ai_images=True,
        image_gen_limit=15,         # 15 AI images/month (~$0.83 cost at FLUX Pro)
        post_scheduling=True,
        analytics=True,
        ai_strategy_briefs=False,
        google_ads=False,
        posts_per_month=60,
        team_members=1,
        stripe_price_id_monthly="price_starter_monthly",
        stripe_price_id_yearly="price_starter_yearly",
        description="2 platforms, 15 AI images/month, scheduling & analytics",
    ),
    "growth": Tier(
        id="growth",
        name="Growth",
        price_monthly=79,
        price_yearly=790,
        platforms=["facebook", "instagram", "linkedin", "tiktok"],
        platform_limit=4,
        ai_images=True,
        image_gen_limit=60,         # 60 AI images/month (~$3.30 cost at FLUX Pro)
        post_scheduling=True,
        analytics=True,
        ai_strategy_briefs=True,
        google_ads=False,
        posts_per_month=200,
        team_members=3,
        stripe_price_id_monthly="price_growth_monthly",
        stripe_price_id_yearly="price_growth_yearly",
        description="4 platforms, 60 AI images/month + AI strategy briefs",
        highlight=True,
    ),
    "agency": Tier(
        id="agency",
        name="Agency",
        price_monthly=199,
        price_yearly=1990,
        platforms=["facebook", "instagram", "linkedin", "tiktok", "twitter"],
        platform_limit=-1,
        ai_images=True,
        image_gen_limit=200,        # 200 AI images/month (~$11 cost at FLUX Pro)
        post_scheduling=True,
        analytics=True,
        ai_strategy_briefs=True,
        google_ads=True,
        posts_per_month=-1,
        team_members=10,
        stripe_price_id_monthly="price_agency_monthly",
        stripe_price_id_yearly="price_agency_yearly",
        description="All platforms, 200 AI images/month, Google Ads, unlimited posts",
    ),
}

# ── Platform Registry ──────────────────────────────────────────────────────────
@dataclass
class PlatformDef:
    id: str
    name: str
    icon: str
    color: str
    auth_type: str          # "oauth2" | "playwright"
    oauth_scope: str        # space-separated OAuth scopes
    features: List[str]     # what actions are supported
    api_docs: str

PLATFORMS: dict[str, PlatformDef] = {
    "facebook": PlatformDef(
        id="facebook",
        name="Facebook",
        icon="📘",
        color="#1877F2",
        auth_type="oauth2",
        oauth_scope="public_profile",
        features=["post", "image_post", "schedule", "analytics", "comment", "reply"],
        api_docs="https://developers.facebook.com/docs/graph-api",
    ),
    "instagram": PlatformDef(
        id="instagram",
        name="Instagram",
        icon="📸",
        color="#E1306C",
        auth_type="oauth2",
        oauth_scope="public_profile,email,instagram_basic,instagram_content_publish,instagram_manage_insights,pages_show_list",
        features=["post", "image_post", "reels", "schedule", "analytics"],
        api_docs="https://developers.facebook.com/docs/instagram-api",
    ),
    "linkedin": PlatformDef(
        id="linkedin",
        name="LinkedIn",
        icon="💼",
        color="#0A66C2",
        auth_type="oauth2",
        oauth_scope="r_liteprofile r_emailaddress w_member_social r_organization_social w_organization_social rw_organization_admin",
        features=["post", "image_post", "article", "schedule", "analytics"],
        api_docs="https://docs.microsoft.com/en-us/linkedin/marketing/",
    ),
    "tiktok": PlatformDef(
        id="tiktok",
        name="TikTok",
        icon="🎵",
        color="#000000",
        auth_type="oauth2",
        oauth_scope="user.info.basic,video.upload,video.publish",
        features=["video_post", "schedule", "analytics"],
        api_docs="https://developers.tiktok.com/doc/",
    ),
    "twitter": PlatformDef(
        id="twitter",
        name="Twitter / X",
        icon="🐦",
        color="#1DA1F2",
        auth_type="oauth2",
        oauth_scope="tweet.read tweet.write users.read offline.access",
        features=["post", "image_post", "schedule", "analytics"],
        api_docs="https://developer.twitter.com/en/docs/twitter-api",
    ),
}

# ── App Settings ───────────────────────────────────────────────────────────────
APP_NAME       = "SocialAI"
APP_TAGLINE    = "Your AI-powered social media manager"
APP_VERSION    = "1.0.0"
SUPPORT_EMAIL  = "support@socialai.app"

# Image generation
DALLE_MODEL    = "dall-e-3"
DALLE_SIZE     = "1024x1024"
DALLE_QUALITY  = "standard"     # "standard" | "hd"

# Scheduling
SCHEDULER_TZ   = "Australia/Sydney"

# Post status values
POST_STATUS    = ["draft", "scheduled", "published", "failed", "deleted"]

# Analytics refresh interval (seconds)
ANALYTICS_TTL  = 3600
