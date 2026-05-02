"""
Analytics Engine — pulls performance metrics from all connected platforms.
"""
import json
from datetime import datetime, timezone
import saas.db as db

def refresh_all_analytics(user_id: str):
    """Pull latest metrics for all connected platforms and store in DB."""
    connections = db.get_all_connections(user_id)
    for conn in connections:
        try:
            _refresh_platform(user_id, conn)
        except Exception as e:
            print(f"Analytics refresh failed for {conn['platform']}: {e}")

def _refresh_platform(user_id: str, conn: dict):
    platform = conn["platform"]
    extra    = json.loads(conn.get("extra_data") or "{}")

    if platform == "facebook":
        from saas.platforms.meta import MetaAPI
        api = MetaAPI(access_token=conn["access_token"], page_id=conn["page_id"])
        _refresh_facebook_posts(user_id, api)

    elif platform == "instagram":
        from saas.platforms.meta import MetaAPI
        ig_id  = extra.get("ig_user_id") or conn.get("page_id")
        ptok   = extra.get("page_token") or conn["access_token"]
        api    = MetaAPI(access_token=conn["access_token"])
        _refresh_instagram_posts(user_id, api, ig_id, ptok)

    elif platform == "linkedin":
        from saas.platforms.linkedin_api import LinkedInAPI
        api = LinkedInAPI(access_token=conn["access_token"])
        _refresh_linkedin_posts(user_id, api)

    elif platform == "twitter":
        from saas.platforms.twitter_api import TwitterAPI
        api = TwitterAPI(access_token=conn["access_token"],
                         user_id=extra.get("twitter_user_id"))
        _refresh_twitter_posts(user_id, api)

    elif platform == "tiktok":
        from saas.platforms.tiktok_api import TikTokAPI
        api = TikTokAPI(access_token=conn["access_token"],
                        open_id=extra.get("open_id"))
        _refresh_tiktok_videos(user_id, api)

def _refresh_facebook_posts(user_id: str, api):
    posts = api.get_facebook_posts(limit=20)
    for fp in posts:
        # find matching post in DB by platform_post_id
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM posts WHERE user_id=? AND platform='facebook' AND platform_post_id=?",
                (user_id, fp["id"])
            ).fetchone()
        if row:
            insights = api.get_facebook_post_insights(fp["id"])
            db.upsert_post_analytics(
                post_id=row["id"], user_id=user_id, platform="facebook",
                likes=fp.get("likes", {}).get("summary", {}).get("total_count", 0),
                comments=fp.get("comments", {}).get("summary", {}).get("total_count", 0),
                shares=fp.get("shares", {}).get("count", 0) if fp.get("shares") else 0,
                impressions=insights.get("post_impressions", 0),
                reach=insights.get("post_reach", 0),
            )

def _refresh_instagram_posts(user_id: str, api, ig_user_id: str, page_token: str):
    if not ig_user_id: return
    import requests
    r = requests.get(f"https://graph.facebook.com/v19.0/{ig_user_id}/media", params={
        "access_token": page_token,
        "fields": "id,caption,like_count,comments_count,timestamp,media_type",
        "limit": 20,
    })
    if not r.ok: return
    for media in r.json().get("data", []):
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM posts WHERE user_id=? AND platform='instagram' AND platform_post_id=?",
                (user_id, media["id"])
            ).fetchone()
        if row:
            insights = api.get_instagram_media_insights(media["id"], page_token)
            db.upsert_post_analytics(
                post_id=row["id"], user_id=user_id, platform="instagram",
                likes=media.get("like_count", 0),
                comments=media.get("comments_count", 0),
                impressions=insights.get("impressions", 0),
                reach=insights.get("reach", 0),
                saves=insights.get("saved", 0),
            )

def _refresh_linkedin_posts(user_id: str, api):
    # LinkedIn UGC posts — fetch recent and update analytics
    import requests
    author = api.org_urn or api.person_urn
    if not author: return
    r = requests.get("https://api.linkedin.com/v2/ugcPosts",
                     headers=api._headers,
                     params={"q": "authors", "authors": f"List({author})",
                             "sortBy": "LAST_MODIFIED", "count": 20})
    if not r.ok: return
    for item in r.json().get("elements", []):
        post_urn = item.get("id", "")
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM posts WHERE user_id=? AND platform='linkedin' AND platform_post_id=?",
                (user_id, post_urn)
            ).fetchone()
        if row:
            stats = api.get_post_stats(post_urn)
            db.upsert_post_analytics(
                post_id=row["id"], user_id=user_id, platform="linkedin",
                likes=stats.get("likes", 0),
                comments=stats.get("comments", 0),
                shares=stats.get("shares", 0),
            )

def _refresh_twitter_posts(user_id: str, api):
    if not api.user_id: return
    import requests
    r = requests.get(f"https://api.twitter.com/2/users/{api.user_id}/tweets",
                     headers=api._headers,
                     params={"max_results": 20, "tweet.fields": "public_metrics,created_at"})
    if not r.ok: return
    for tweet in r.json().get("data", []):
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM posts WHERE user_id=? AND platform='twitter' AND platform_post_id=?",
                (user_id, tweet["id"])
            ).fetchone()
        if row:
            m = tweet.get("public_metrics", {})
            db.upsert_post_analytics(
                post_id=row["id"], user_id=user_id, platform="twitter",
                likes=m.get("like_count", 0),
                comments=m.get("reply_count", 0),
                shares=m.get("retweet_count", 0),
                impressions=m.get("impression_count", 0),
            )

def _refresh_tiktok_videos(user_id: str, api):
    videos = api.get_video_list()
    for v in videos:
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM posts WHERE user_id=? AND platform='tiktok' AND platform_post_id=?",
                (user_id, v.get("id", ""))
            ).fetchone()
        if row:
            db.upsert_post_analytics(
                post_id=row["id"], user_id=user_id, platform="tiktok",
                likes=v.get("like_count", 0),
                comments=v.get("comment_count", 0),
                shares=v.get("share_count", 0),
                reach=v.get("view_count", 0),
            )

# ── Aggregate Insights ─────────────────────────────────────────────────────────
def get_top_posts(user_id: str, platform: str = None, limit: int = 5) -> list:
    query = """
        SELECT p.id, p.platform, p.content, p.published_at, p.image_url,
               COALESCE(a.likes,0)+COALESCE(a.comments,0)+COALESCE(a.shares,0) as total_engagement,
               COALESCE(a.likes,0) as likes, COALESCE(a.comments,0) as comments,
               COALESCE(a.shares,0) as shares, COALESCE(a.reach,0) as reach
        FROM posts p
        LEFT JOIN post_analytics a ON a.post_id=p.id
        WHERE p.user_id=? AND p.status='published'
    """
    params = [user_id]
    if platform:
        query += " AND p.platform=?"
        params.append(platform)
    query += " ORDER BY total_engagement DESC LIMIT ?"
    params.append(limit)
    with db.get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def get_engagement_trend(user_id: str, platform: str = None, days: int = 30) -> list:
    """Daily engagement totals for charting."""
    query = """
        SELECT DATE(p.published_at) as day,
               SUM(COALESCE(a.likes,0)+COALESCE(a.comments,0)+COALESCE(a.shares,0)) as engagement,
               COUNT(p.id) as posts
        FROM posts p
        LEFT JOIN post_analytics a ON a.post_id=p.id
        WHERE p.user_id=? AND p.status='published'
        AND p.published_at >= datetime('now', ?)
    """
    params = [user_id, f"-{days} days"]
    if platform:
        query += " AND p.platform=?"
        params.append(platform)
    query += " GROUP BY DATE(p.published_at) ORDER BY day"
    with db.get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def get_best_post_times(user_id: str, platform: str = None) -> list:
    """Return average engagement by hour of day."""
    query = """
        SELECT CAST(strftime('%H', p.published_at) AS INTEGER) as hour,
               AVG(COALESCE(a.likes,0)+COALESCE(a.comments,0)+COALESCE(a.shares,0)) as avg_engagement,
               COUNT(*) as post_count
        FROM posts p
        LEFT JOIN post_analytics a ON a.post_id=p.id
        WHERE p.user_id=? AND p.status='published'
    """
    params = [user_id]
    if platform:
        query += " AND p.platform=?"
        params.append(platform)
    query += " GROUP BY hour ORDER BY avg_engagement DESC"
    with db.get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
