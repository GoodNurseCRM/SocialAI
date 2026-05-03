"""
Stripe billing integration.
Handles subscription creation, webhooks, and tier enforcement.
"""
import os, stripe, json
from typing import Optional
from saas.config import TIERS, Tier
import saas.db as db

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")


def _app_base_url() -> str:
    base_url = os.environ.get("APP_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise ValueError("APP_BASE_URL is required when no callback URL is provided.")
    return base_url

# ── Stripe Customers ───────────────────────────────────────────────────────────
def get_or_create_customer(user_id: str, email: str, name: str) -> str:
    """Return existing Stripe customer ID or create a new one."""
    sub = db.get_subscription(user_id)
    if sub.get("stripe_customer_id"):
        return sub["stripe_customer_id"]
    customer = stripe.Customer.create(email=email, name=name,
                                      metadata={"user_id": user_id})
    db.update_subscription(user_id, stripe_customer_id=customer.id)
    return customer.id

# ── Checkout ───────────────────────────────────────────────────────────────────
def create_checkout_session(user_id: str, email: str, name: str,
                             tier_id: str, billing: str = "monthly",
                             success_url: str = None,
                             cancel_url: str = None) -> str:
    """Create a Stripe Checkout session and return the URL."""
    if not success_url or not cancel_url:
        base_url = _app_base_url()
        success_url = success_url or f"{base_url}/?checkout=success"
        cancel_url = cancel_url or f"{base_url}/?checkout=cancel"

    tier = TIERS.get(tier_id)
    if not tier or tier.id == "free":
        raise ValueError(f"Invalid tier: {tier_id}")

    price_id = (tier.stripe_price_id_yearly if billing == "yearly"
                else tier.stripe_price_id_monthly)
    if not price_id or price_id.startswith("price_starter"):
        raise ValueError("Stripe price IDs not configured yet. Add them to saas/config.py after setting up Stripe.")

    customer_id = get_or_create_customer(user_id, email, name)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url + "&session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"user_id": user_id, "tier": tier_id},
        subscription_data={"metadata": {"user_id": user_id, "tier": tier_id}},
    )
    return session.url

# ── Customer Portal ────────────────────────────────────────────────────────────
def create_portal_session(user_id: str,
                           return_url: str = None) -> str:
    """Return Stripe Customer Portal URL for managing subscriptions."""
    return_url = return_url or _app_base_url()
    sub = db.get_subscription(user_id)
    if not sub.get("stripe_customer_id"):
        raise ValueError("No Stripe customer found.")
    session = stripe.billing_portal.Session.create(
        customer=sub["stripe_customer_id"],
        return_url=return_url,
    )
    return session.url

# ── Webhook Handler ────────────────────────────────────────────────────────────
def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Process Stripe webhooks.
    Call this from a FastAPI/Flask endpoint or a standalone webhook server.
    """
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return {"error": str(e)}

    etype = event["type"]
    obj   = event["data"]["object"]

    if etype == "checkout.session.completed":
        user_id = obj["metadata"].get("user_id")
        tier_id = obj["metadata"].get("tier")
        sub_id  = obj.get("subscription")
        if user_id and tier_id:
            _activate_subscription(user_id, tier_id, sub_id)

    elif etype in ("customer.subscription.updated", "customer.subscription.created"):
        _sync_subscription(obj)

    elif etype == "customer.subscription.deleted":
        user_id = obj["metadata"].get("user_id")
        if user_id:
            db.update_subscription(user_id, tier="free", status="cancelled",
                                   stripe_subscription_id=None)

    elif etype == "invoice.payment_failed":
        sub_id = obj.get("subscription")
        if sub_id:
            _handle_payment_failure(sub_id)

    return {"received": True}

def _activate_subscription(user_id: str, tier_id: str, stripe_sub_id: str):
    if stripe_sub_id:
        sub = stripe.Subscription.retrieve(stripe_sub_id)
        period_start = str(sub["current_period_start"])
        period_end   = str(sub["current_period_end"])
    else:
        period_start = period_end = None

    db.update_subscription(
        user_id,
        tier=tier_id,
        status="active",
        stripe_subscription_id=stripe_sub_id,
        current_period_start=period_start,
        current_period_end=period_end,
    )

def _sync_subscription(stripe_sub: dict):
    meta    = stripe_sub.get("metadata", {})
    user_id = meta.get("user_id")
    tier_id = meta.get("tier")
    if not user_id: return
    db.update_subscription(
        user_id,
        tier=tier_id or "free",
        status=stripe_sub["status"],
        stripe_subscription_id=stripe_sub["id"],
        current_period_start=str(stripe_sub["current_period_start"]),
        current_period_end=str(stripe_sub["current_period_end"]),
        cancel_at_period_end=int(stripe_sub.get("cancel_at_period_end", False)),
    )

def _handle_payment_failure(stripe_sub_id: str):
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT user_id FROM subscriptions WHERE stripe_subscription_id=?",
            (stripe_sub_id,)
        ).fetchone()
        if row:
            db.update_subscription(row["user_id"], status="past_due")

# ── Tier Enforcement ───────────────────────────────────────────────────────────
def get_user_tier(user_id: str) -> Tier:
    sub = db.get_subscription(user_id)
    tier_id = sub.get("tier", "free")
    if sub.get("status") not in ("active", "trialing"):
        tier_id = "free"
    return TIERS.get(tier_id, TIERS["free"])

def can_connect_platform(user_id: str, platform: str) -> tuple[bool, str]:
    tier = get_user_tier(user_id)
    if tier.platform_limit == -1:
        return True, ""
    connected = db.get_all_connections(user_id)
    if platform in [c["platform"] for c in connected]:
        return True, ""   # already connected — no new slot used
    if len(connected) >= tier.platform_limit:
        return False, f"Your {tier.name} plan allows {tier.platform_limit} platform(s). Upgrade to connect more."
    if platform not in tier.platforms:
        return False, f"{platform.title()} is not included in your {tier.name} plan."
    return True, ""

def can_create_post(user_id: str) -> tuple[bool, str]:
    tier = get_user_tier(user_id)
    if tier.posts_per_month == -1:
        return True, ""
    usage = db.get_usage(user_id, "post_created")
    used  = sum(v for k, v in usage.items())
    if used >= tier.posts_per_month:
        return False, f"You've used {used}/{tier.posts_per_month} posts this month. Upgrade for more."
    return True, ""

def can_generate_image(user_id: str) -> tuple[bool, str]:
    """Check if the user can generate another AI image this month."""
    tier = get_user_tier(user_id)
    if tier.image_gen_limit == 0:
        return False, "AI image generation is not included in your Free Trial. Upgrade to Starter or higher."
    if tier.image_gen_limit == -1:
        return True, ""   # unlimited
    usage   = db.get_usage(user_id, "image_generated")
    used    = sum(v for v in usage.values())
    limit   = tier.image_gen_limit
    if used >= limit:
        return False, (
            f"You've used {used}/{limit} AI images this month. "
            f"Upgrade to generate more — your limit resets on the 1st of each month."
        )
    remaining = limit - used
    return True, f"{remaining} of {limit} AI images remaining this month."

def images_used_this_month(user_id: str) -> tuple[int, int]:
    """Return (used, limit) for image generation this month."""
    tier  = get_user_tier(user_id)
    usage = db.get_usage(user_id, "image_generated")
    used  = sum(v for v in usage.values())
    return used, tier.image_gen_limit

def can_use_scheduling(user_id: str) -> tuple[bool, str]:
    tier = get_user_tier(user_id)
    if not tier.post_scheduling:
        return False, f"Post scheduling requires the Starter plan or higher."
    return True, ""

def can_use_analytics(user_id: str) -> tuple[bool, str]:
    tier = get_user_tier(user_id)
    if not tier.analytics:
        return False, f"Analytics requires the Starter plan or higher."
    return True, ""

def can_use_strategy(user_id: str) -> tuple[bool, str]:
    tier = get_user_tier(user_id)
    if not tier.ai_strategy_briefs:
        return False, f"AI strategy briefs require the Growth plan or higher."
    return True, ""
