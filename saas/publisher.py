"""
Post Publisher — unified interface to publish a post to any platform.
Called by the scheduler and by the "Post Now" button in the UI.
"""
import json, base64, os, tempfile
import saas.db as db
from saas.config import PLATFORMS

def publish_post(post: dict) -> tuple[bool, str]:
    """
    Publish a single post dict to its platform.
    Returns (success: bool, platform_post_id_or_error: str).
    """
    platform = post["platform"]
    user_id  = post["user_id"]

    conn = db.get_platform_connection(user_id, platform)
    if not conn:
        return False, f"No {platform} connection found. Please reconnect."

    extra = json.loads(conn.get("extra_data") or "{}")

    try:
        if platform == "facebook":
            return _publish_facebook(post, conn, extra)
        elif platform == "instagram":
            return _publish_instagram(post, conn, extra)
        elif platform == "linkedin":
            return _publish_linkedin(post, conn, extra)
        elif platform == "tiktok":
            return _publish_tiktok(post, conn, extra)
        elif platform == "twitter":
            return _publish_twitter(post, conn, extra)
        else:
            return False, f"Unsupported platform: {platform}"
    except Exception as e:
        return False, str(e)

# ── Platform Publishers ────────────────────────────────────────────────────────
def _publish_facebook(post, conn, extra) -> tuple[bool, str]:
    from saas.platforms.meta import MetaAPI
    page_token = extra.get("page_token") or conn["access_token"]
    api = MetaAPI(access_token=page_token, page_id=conn["page_id"])
    result = api.post_facebook(
        message=post["content"],
        image_url=post.get("image_url"),
    )
    post_id = result.get("id", result.get("post_id", ""))
    return bool(post_id), post_id

def _publish_instagram(post, conn, extra) -> tuple[bool, str]:
    from saas.platforms.meta import MetaAPI
    ig_user_id = extra.get("ig_user_id") or conn.get("page_id")
    page_token = extra.get("page_token") or conn["access_token"]
    if not ig_user_id:
        return False, "Instagram user ID not found. Please reconnect."
    api    = MetaAPI(access_token=conn["access_token"])
    result = api.post_instagram(
        ig_user_id=ig_user_id,
        page_token=page_token,
        caption=post["content"],
        image_url=post.get("image_url"),
    )
    media_id = result.get("id", "")
    return bool(media_id), media_id

def _publish_linkedin(post, conn, extra) -> tuple[bool, str]:
    from saas.platforms.linkedin_api import LinkedInAPI
    person_urn = extra.get("person_urn")
    org_urn    = extra.get("org_urn")
    api = LinkedInAPI(access_token=conn["access_token"],
                      person_urn=person_urn, org_urn=org_urn)
    result  = api.create_post(text=post["content"], image_url=post.get("image_url"))
    post_id = result.get("id", "")
    return bool(post_id), post_id

def _publish_tiktok(post, conn, extra) -> tuple[bool, str]:
    from saas.platforms.tiktok_api import TikTokAPI
    api = TikTokAPI(access_token=conn["access_token"], open_id=extra.get("open_id"))
    video_url = post.get("image_url")   # for TikTok, image_url stores video_url
    if not video_url:
        return False, "TikTok requires a video URL. Please attach a video."
    result    = api.upload_video_from_url(video_url=video_url, title=post["content"])
    publish_id = result.get("publish_id", "")
    return bool(publish_id), publish_id

def _publish_twitter(post, conn, extra) -> tuple[bool, str]:
    from saas.platforms.twitter_api import TwitterAPI
    api    = TwitterAPI(access_token=conn["access_token"], user_id=extra.get("twitter_user_id"))
    result = api.create_tweet(text=post["content"][:280], image_url=post.get("image_url"))
    tweet_id = result.get("id", "")
    return bool(tweet_id), tweet_id
