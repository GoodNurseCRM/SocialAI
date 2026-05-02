"""
Admin Engine — owner-only stats, subscriber health, and platform analytics.
All queries are read-only aggregations over the shared SQLite database.
"""
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
import saas.db as db


# ── Health scoring ─────────────────────────────────────────────────────────────

def subscriber_health(user: dict) -> dict:
    """
    Calculate a health score (0–100) and status for a subscriber.
    Returns: {score, status, color, label, reasons}
    """
    uid = user["id"]
    score = 0
    reasons = []

    last_login = user.get("last_login") or user.get("created_at", "")

    # 1. Login recency (max 25 pts)
    try:
        last_dt = datetime.fromisoformat(last_login.replace("Z", "+00:00"))
        days_since = (datetime.now(timezone.utc) - last_dt).days
        if   days_since <= 3:   score += 25; reasons.append("Active recently")
        elif days_since <= 7:   score += 18
        elif days_since <= 14:  score += 10
        elif days_since <= 30:  score += 5
        else: reasons.append(f"Inactive {days_since}d")
    except Exception:
        pass

    # 2. Business profile complete (max 20 pts)
    profile = db.get_business_profile(uid)
    if profile and profile.get("onboarding_complete"):
        score += 20
        reasons.append("Profile complete")
    elif profile:
        score += 8
        reasons.append("Profile incomplete")
    else:
        reasons.append("No profile")

    # 3. Has ad campaigns (max 20 pts)
    campaigns = db.get_campaigns(uid)
    if campaigns:
        approved = [c for c in campaigns if c["status"] == "approved"]
        score += min(20, 10 + len(approved) * 5)
        reasons.append(f"{len(campaigns)} campaign{'s' if len(campaigns)!=1 else ''}")
    else:
        reasons.append("No campaigns yet")

    # 4. Posts published this month (max 20 pts)
    posts = db.get_posts(uid, status="published", limit=200)
    if posts:
        score += min(20, len(posts) * 2)
        reasons.append(f"{len(posts)} posts published")
    else:
        reasons.append("No posts published")

    # 5. Platforms connected (max 15 pts)
    conns = db.get_all_connections(uid)
    score += min(15, len(conns) * 5)
    if conns:
        reasons.append(f"{len(conns)} platform{'s' if len(conns)!=1 else ''} connected")

    score = min(score, 100)

    if   score >= 75: status, color = "Healthy",  "#22C55E"
    elif score >= 45: status, color = "Growing",  "#F59E0B"
    elif score >= 20: status, color = "Dormant",  "#EF4444"
    else:             status, color = "New",      "#64748B"

    return {"score": score, "status": status, "color": color, "reasons": reasons}


# ── Subscriber list ────────────────────────────────────────────────────────────

def get_all_subscribers(exclude_owner: bool = True) -> list[dict]:
    """Return all users with enriched stats."""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        ).fetchall()
    users = [dict(r) for r in rows]

    if exclude_owner:
        owner_email = _owner_email()
        users = [u for u in users if u["email"] != owner_email]

    enriched = []
    for u in users:
        uid = u["id"]
        profile   = db.get_business_profile(uid)
        sub       = db.get_subscription(uid)
        posts     = db.get_posts(uid, status="published", limit=200)
        campaigns = db.get_campaigns(uid)
        conns     = db.get_all_connections(uid)
        health    = subscriber_health(u)

        # Preferred model
        pref_model = "claude-sonnet-4-6"
        if profile and profile.get("preferred_model"):
            pref_model = profile["preferred_model"]

        enriched.append({
            **u,
            "profile":        profile,
            "tier":           sub.get("tier", "free") if sub else "free",
            "sub_status":     sub.get("status", "active") if sub else "active",
            "posts_total":    len(posts),
            "campaigns_total": len(campaigns),
            "platforms_count": len(conns),
            "health":         health,
            "preferred_model": pref_model,
            "has_profile":    bool(profile and profile.get("onboarding_complete")),
        })

    return enriched


# ── Platform-wide stats ────────────────────────────────────────────────────────

def owner_stats() -> dict:
    """Aggregate stats for the owner dashboard header."""
    with db.get_conn() as conn:
        total_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE email != ?", (_owner_email(),)
        ).fetchone()[0]

        # Active this month
        active_month = conn.execute("""
            SELECT COUNT(DISTINCT user_id) FROM sessions
            WHERE expires_at > datetime('now')
        """).fetchone()[0]

        # New this week
        new_week = conn.execute("""
            SELECT COUNT(*) FROM users
            WHERE created_at >= datetime('now', '-7 days')
            AND email != ?
        """, (_owner_email(),)).fetchone()[0]

        # Total posts published
        total_posts = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE status='published'"
        ).fetchone()[0]

        # Total campaigns
        total_campaigns = conn.execute(
            "SELECT COUNT(*) FROM ad_campaigns"
        ).fetchone()[0]

        # Approved campaigns
        approved_campaigns = conn.execute(
            "SELECT COUNT(*) FROM ad_campaigns WHERE status='approved'"
        ).fetchone()[0]

        # Plans by tier
        tier_counts = {}
        rows = conn.execute("""
            SELECT tier, COUNT(*) as cnt FROM subscriptions
            WHERE status='active' GROUP BY tier
        """).fetchall()
        for r in rows:
            tier_counts[r["tier"]] = r["cnt"]

        # Total profiles with onboarding complete
        profiles_done = conn.execute(
            "SELECT COUNT(*) FROM business_profiles WHERE onboarding_complete=1"
        ).fetchone()[0]

        # Posts in last 30 days
        posts_30d = conn.execute("""
            SELECT COUNT(*) FROM posts
            WHERE status='published'
            AND published_at >= datetime('now', '-30 days')
        """).fetchone()[0]

    # Health breakdown
    subscribers = get_all_subscribers()
    health_counts = {"Healthy": 0, "Growing": 0, "Dormant": 0, "New": 0}
    for s in subscribers:
        h = s["health"]["status"]
        health_counts[h] = health_counts.get(h, 0) + 1

    return {
        "total_subscribers":   total_users,
        "active_sessions":     active_month,
        "new_this_week":       new_week,
        "total_posts":         total_posts,
        "posts_last_30d":      posts_30d,
        "total_campaigns":     total_campaigns,
        "approved_campaigns":  approved_campaigns,
        "profiles_complete":   profiles_done,
        "tier_breakdown":      tier_counts,
        "health_breakdown":    health_counts,
    }


# ── Per-subscriber drill-in ────────────────────────────────────────────────────

def subscriber_detail(user_id: str) -> dict:
    """Deep stats for a single subscriber (shown in drill-in view)."""
    user = db.get_user_by_id(user_id)
    if not user:
        return {}

    profile   = db.get_business_profile(user_id)
    posts     = db.get_posts(user_id, limit=200)
    campaigns = db.get_campaigns(user_id)
    conns     = db.get_all_connections(user_id)
    analytics = db.get_analytics_summary(user_id, days=30)
    per_plat  = db.get_posts_per_platform(user_id, days=30)
    health    = subscriber_health(user)

    # Post status breakdown
    status_counts = {}
    for p in posts:
        status_counts[p["status"]] = status_counts.get(p["status"], 0) + 1

    # Campaign status breakdown
    camp_status = {}
    for c in campaigns:
        camp_status[c["status"]] = camp_status.get(c["status"], 0) + 1

    return {
        "user":             user,
        "profile":          profile,
        "health":           health,
        "posts_total":      len(posts),
        "post_status":      status_counts,
        "campaigns_total":  len(campaigns),
        "campaign_status":  camp_status,
        "platforms":        conns,
        "analytics_30d":    analytics,
        "per_platform":     per_plat,
        "recent_campaigns": campaigns[:5],
        "recent_posts":     posts[:10],
    }


# ── Model usage analytics ──────────────────────────────────────────────────────

def model_usage_summary() -> list[dict]:
    """Count how many subscribers use each model (from business_profiles)."""
    with db.get_conn() as conn:
        rows = conn.execute("""
            SELECT COALESCE(preferred_model, 'claude-sonnet-4-6') as model,
                   COUNT(*) as count
            FROM business_profiles
            WHERE onboarding_complete=1
            GROUP BY model
            ORDER BY count DESC
        """).fetchall()
    return [dict(r) for r in rows]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _owner_email() -> str:
    import os
    return os.environ.get("OWNER_EMAIL", "").lower().strip()
