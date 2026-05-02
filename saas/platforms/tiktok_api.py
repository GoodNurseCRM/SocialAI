"""
TikTok for Developers API — OAuth2, video upload, and analytics.
"""
import os, requests
from urllib.parse import urlencode

TT_CLIENT_KEY    = os.environ.get("TIKTOK_CLIENT_KEY", "")
TT_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "")
TT_API_BASE      = "https://open.tiktokapis.com/v2"

class TikTokAPI:

    def __init__(self, access_token: str = None, open_id: str = None):
        self.access_token = access_token
        self.open_id      = open_id

    @property
    def _headers(self):
        return {"Authorization": f"Bearer {self.access_token}",
                "Content-Type":  "application/json; charset=UTF-8"}

    # ── OAuth ──────────────────────────────────────────────────────────────────
    @staticmethod
    def get_auth_url(redirect_uri: str, scope: str, state: str = "") -> str:
        params = {
            "client_key":     TT_CLIENT_KEY,
            "response_type":  "code",
            "scope":          scope,
            "redirect_uri":   redirect_uri,
            "state":          state,
        }
        return f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(params)}"

    @staticmethod
    def exchange_code(code: str, redirect_uri: str, code_verifier: str = "") -> dict:
        payload = {
            "client_key":    TT_CLIENT_KEY,
            "client_secret": TT_CLIENT_SECRET,
            "code":          code,
            "grant_type":    "authorization_code",
            "redirect_uri":  redirect_uri,
        }
        if code_verifier:
            payload["code_verifier"] = code_verifier
        r = requests.post("https://open.tiktokapis.com/v2/oauth/token/",
                          headers={"Content-Type": "application/x-www-form-urlencoded"},
                          data=payload)
        r.raise_for_status()
        return r.json()   # {"access_token", "refresh_token", "open_id", "expires_in", ...}

    @staticmethod
    def refresh_token(refresh_token: str) -> dict:
        r = requests.post("https://open.tiktokapis.com/v2/oauth/token/",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"client_key": TT_CLIENT_KEY, "client_secret": TT_CLIENT_SECRET,
                  "grant_type": "refresh_token", "refresh_token": refresh_token})
        r.raise_for_status()
        return r.json()

    def get_user_info(self) -> dict:
        r = requests.get(f"{TT_API_BASE}/user/info/",
                         headers=self._headers,
                         params={"fields": "open_id,union_id,display_name,avatar_url,follower_count,following_count,likes_count,video_count"})
        r.raise_for_status()
        return r.json().get("data", {}).get("user", {})

    # ── Video Upload ───────────────────────────────────────────────────────────
    def upload_video_from_url(self, video_url: str, title: str,
                               privacy: str = "PUBLIC_TO_EVERYONE") -> dict:
        """
        Upload a video to TikTok via URL pull.
        Returns creator_post_id.
        """
        # Step 1: init upload
        init_r = requests.post(f"{TT_API_BASE}/post/publish/video/init/",
            headers=self._headers,
            json={
                "post_info": {
                    "title":           title[:150],
                    "privacy_level":   privacy,
                    "disable_duet":    False,
                    "disable_comment": False,
                    "disable_stitch":  False,
                },
                "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
            })
        init_r.raise_for_status()
        return init_r.json().get("data", {})   # {"publish_id": "..."}

    def get_post_status(self, publish_id: str) -> dict:
        r = requests.post(f"{TT_API_BASE}/post/publish/status/fetch/",
                          headers=self._headers,
                          json={"publish_id": publish_id})
        r.raise_for_status()
        return r.json().get("data", {})

    # ── Analytics ──────────────────────────────────────────────────────────────
    def get_video_list(self, fields: str = None, max_count: int = 20) -> list:
        fields = fields or "id,title,cover_image_url,share_url,view_count,like_count,comment_count,share_count,create_time"
        r = requests.post(f"{TT_API_BASE}/video/list/",
                          headers=self._headers,
                          json={"max_count": max_count, "fields": fields})
        r.raise_for_status()
        return r.json().get("data", {}).get("videos", [])
