"""
Meta Graph API — Facebook + Instagram.
Handles OAuth, page management, posting, and analytics.
"""
import os, requests, json
from typing import Optional
from urllib.parse import urlencode

FB_APP_ID     = os.environ.get("META_APP_ID", "")
FB_APP_SECRET = os.environ.get("META_APP_SECRET", "")
FB_API_VER    = "v22.0"
FB_BASE       = f"https://graph.facebook.com/{FB_API_VER}"

class MetaAPI:
    """Facebook + Instagram via Meta Graph API."""

    def __init__(self, access_token: str = None, page_id: str = None):
        self.access_token = access_token
        self.page_id      = page_id

    # ── OAuth ──────────────────────────────────────────────────────────────────
    @staticmethod
    def get_auth_url(redirect_uri: str, scope: str, state: str = "") -> str:
        """Return the OAuth2 URL the user should be sent to."""
        params = {
            "client_id":     FB_APP_ID,
            "redirect_uri":  redirect_uri,
            "scope":         scope,
            "response_type": "code",
            "state":         state,
        }
        return f"https://www.facebook.com/dialog/oauth?{urlencode(params)}"

    @staticmethod
    def exchange_code(code: str, redirect_uri: str) -> dict:
        """Exchange auth code for short-lived token, then extend it."""
        def _fb_raise(resp):
            """Raise with the Facebook error message if one is present."""
            try:
                body = resp.json()
                err  = body.get("error") or {}
                if err:
                    raise ValueError(f"Facebook error {err.get('code')}: {err.get('message')}")
            except (AttributeError, KeyError, requests.exceptions.JSONDecodeError):
                pass
            resp.raise_for_status()

        # Step 1: get short-lived token
        r = requests.get(f"{FB_BASE}/oauth/access_token", params={
            "client_id":     FB_APP_ID,
            "client_secret": FB_APP_SECRET,
            "redirect_uri":  redirect_uri,
            "code":          code,
        })
        _fb_raise(r)
        short_token = r.json().get("access_token")
        if not short_token:
            raise ValueError(f"No access_token in response: {r.json()}")

        # Step 2: extend to long-lived (60-day) token
        r2 = requests.get(f"{FB_BASE}/oauth/access_token", params={
            "grant_type":        "fb_exchange_token",
            "client_id":         FB_APP_ID,
            "client_secret":     FB_APP_SECRET,
            "fb_exchange_token": short_token,
        })
        _fb_raise(r2)
        return r2.json()   # {"access_token": "...", "token_type": "bearer", "expires_in": ...}

    def get_pages(self) -> list:
        """Return list of Facebook Pages the user manages."""
        r = requests.get(f"{FB_BASE}/me/accounts", params={
            "access_token": self.access_token,
            "fields":       "id,name,access_token,category,picture",
        })
        r.raise_for_status()
        return r.json().get("data", [])

    def get_instagram_account(self, page_id: str, page_token: str) -> Optional[dict]:
        """Return the Instagram Business account linked to a Facebook Page."""
        r = requests.get(f"{FB_BASE}/{page_id}", params={
            "access_token": page_token,
            "fields":       "instagram_business_account{id,username,profile_picture_url,followers_count}",
        })
        r.raise_for_status()
        return r.json().get("instagram_business_account")

    # ── Facebook Posts ─────────────────────────────────────────────────────────
    def post_facebook(self, message: str, image_url: str = None,
                      scheduled_time: int = None) -> dict:
        """Publish a text or photo post to a Facebook Page."""
        if not self.page_id or not self.access_token:
            raise ValueError("page_id and access_token required")

        if image_url:
            endpoint = f"{FB_BASE}/{self.page_id}/photos"
            payload  = {"url": image_url, "caption": message,
                        "access_token": self.access_token}
        else:
            endpoint = f"{FB_BASE}/{self.page_id}/feed"
            payload  = {"message": message, "access_token": self.access_token}

        if scheduled_time:
            payload["scheduled_publish_time"] = scheduled_time
            payload["published"] = False

        r = requests.post(endpoint, data=payload)
        r.raise_for_status()
        return r.json()   # {"id": "page_id_post_id"}

    def get_facebook_posts(self, limit: int = 10) -> list:
        """Return recent posts from the Page."""
        r = requests.get(f"{FB_BASE}/{self.page_id}/posts", params={
            "access_token": self.access_token,
            "fields":       "id,message,story,created_time,full_picture,likes.summary(true),comments.summary(true),shares",
            "limit":        limit,
        })
        r.raise_for_status()
        return r.json().get("data", [])

    def get_facebook_post_insights(self, post_id: str) -> dict:
        """Return engagement metrics for a specific post."""
        metrics = "post_impressions,post_reach,post_engaged_users,post_reactions_like_total"
        r = requests.get(f"{FB_BASE}/{post_id}/insights", params={
            "access_token": self.access_token,
            "metric":       metrics,
        })
        r.raise_for_status()
        data = {item["name"]: item["values"][0]["value"]
                for item in r.json().get("data", []) if item.get("values")}
        return data

    def get_page_insights(self, days: int = 28) -> dict:
        """Return aggregate Page metrics."""
        metrics = "page_fans,page_impressions,page_reach,page_views_total,page_post_engagements"
        r = requests.get(f"{FB_BASE}/{self.page_id}/insights", params={
            "access_token": self.access_token,
            "metric":       metrics,
            "period":       "day",
            "since":        f"-{days}days",
        })
        r.raise_for_status()
        return {item["name"]: sum(v["value"] for v in item.get("values", []))
                for item in r.json().get("data", [])}

    # ── Instagram Posts ────────────────────────────────────────────────────────
    def post_instagram(self, ig_user_id: str, page_token: str,
                        caption: str, image_url: str = None,
                        video_url: str = None) -> dict:
        """Publish an Instagram post (image or video required)."""
        # Step 1: create media container
        container_params = {"access_token": page_token}
        if image_url:
            container_params.update({"image_url": image_url, "caption": caption})
        elif video_url:
            container_params.update({"video_url": video_url, "caption": caption,
                                     "media_type": "REELS"})
        else:
            raise ValueError("Instagram requires image_url or video_url")

        r1 = requests.post(f"{FB_BASE}/{ig_user_id}/media", data=container_params)
        r1.raise_for_status()
        container_id = r1.json()["id"]

        # Step 2: publish the container
        r2 = requests.post(f"{FB_BASE}/{ig_user_id}/media_publish", data={
            "creation_id":  container_id,
            "access_token": page_token,
        })
        r2.raise_for_status()
        return r2.json()   # {"id": "media_id"}

    def get_instagram_insights(self, ig_user_id: str, page_token: str,
                                days: int = 30) -> dict:
        """Return Instagram account-level metrics."""
        metrics = "follower_count,reach,impressions,profile_views"
        r = requests.get(f"{FB_BASE}/{ig_user_id}/insights", params={
            "access_token": page_token,
            "metric":       metrics,
            "period":       "day",
            "since":        f"-{days}days",
        })
        r.raise_for_status()
        return {item["name"]: sum(v["value"] for v in item.get("values", []))
                for item in r.json().get("data", [])}

    def get_instagram_media_insights(self, media_id: str, page_token: str) -> dict:
        """Return engagement metrics for a specific Instagram post."""
        metrics = "impressions,reach,likes,comments,shares,saved"
        r = requests.get(f"{FB_BASE}/{media_id}/insights", params={
            "access_token": page_token,
            "metric":       metrics,
        })
        r.raise_for_status()
        return {item["name"]: item.get("values", [{}])[0].get("value", 0)
                for item in r.json().get("data", [])}
