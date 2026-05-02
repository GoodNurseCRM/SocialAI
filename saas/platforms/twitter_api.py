"""
Twitter API v2 — OAuth 2.0 PKCE, posting, and analytics.
"""
import os, requests, base64, hashlib, secrets
from urllib.parse import urlencode

TW_CLIENT_ID     = os.environ.get("TWITTER_CLIENT_ID", "")
TW_CLIENT_SECRET = os.environ.get("TWITTER_CLIENT_SECRET", "")
TW_API_BASE      = "https://api.twitter.com/2"

class TwitterAPI:

    def __init__(self, access_token: str = None, user_id: str = None):
        self.access_token = access_token
        self.user_id      = user_id

    @property
    def _headers(self):
        return {"Authorization": f"Bearer {self.access_token}",
                "Content-Type":  "application/json"}

    # ── PKCE helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def generate_pkce() -> tuple[str, str]:
        """Return (code_verifier, code_challenge) for PKCE flow."""
        verifier  = secrets.token_urlsafe(43)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return verifier, challenge

    @staticmethod
    def get_auth_url(redirect_uri: str, scope: str, state: str,
                     code_challenge: str) -> str:
        params = {
            "response_type":         "code",
            "client_id":             TW_CLIENT_ID,
            "redirect_uri":          redirect_uri,
            "scope":                 scope,
            "state":                 state,
            "code_challenge":        code_challenge,
            "code_challenge_method": "S256",
        }
        return f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"

    @staticmethod
    def exchange_code(code: str, redirect_uri: str, code_verifier: str) -> dict:
        r = requests.post("https://api.twitter.com/2/oauth2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "code":          code,
                "grant_type":    "authorization_code",
                "client_id":     TW_CLIENT_ID,
                "redirect_uri":  redirect_uri,
                "code_verifier": code_verifier,
            },
            auth=(TW_CLIENT_ID, TW_CLIENT_SECRET),
        )
        r.raise_for_status()
        return r.json()   # {"access_token", "refresh_token", "expires_in", ...}

    @staticmethod
    def refresh_token(refresh_token: str) -> dict:
        r = requests.post("https://api.twitter.com/2/oauth2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "refresh_token", "refresh_token": refresh_token,
                  "client_id": TW_CLIENT_ID},
            auth=(TW_CLIENT_ID, TW_CLIENT_SECRET),
        )
        r.raise_for_status()
        return r.json()

    def get_me(self) -> dict:
        r = requests.get(f"{TW_API_BASE}/users/me", headers=self._headers,
                         params={"user.fields": "id,name,username,profile_image_url,public_metrics"})
        r.raise_for_status()
        return r.json().get("data", {})

    # ── Posting ────────────────────────────────────────────────────────────────
    def create_tweet(self, text: str, image_url: str = None) -> dict:
        """Post a tweet (with optional image via media upload)."""
        body = {"text": text[:280]}

        if image_url:
            media_id = self._upload_image(image_url)
            body["media"] = {"media_ids": [media_id]}

        r = requests.post(f"{TW_API_BASE}/tweets",
                          headers=self._headers, json=body)
        r.raise_for_status()
        return r.json().get("data", {})   # {"id": "...", "text": "..."}

    def _upload_image(self, image_url: str) -> str:
        """Upload image to Twitter Media Upload API and return media_id_string."""
        img_data  = requests.get(image_url).content
        # Step 1: INIT
        init_r = requests.post("https://upload.twitter.com/1.1/media/upload.json",
            headers={"Authorization": f"Bearer {self.access_token}"},
            data={"command": "INIT", "media_type": "image/jpeg",
                  "total_bytes": len(img_data), "media_category": "tweet_image"})
        init_r.raise_for_status()
        media_id = init_r.json()["media_id_string"]

        # Step 2: APPEND
        requests.post("https://upload.twitter.com/1.1/media/upload.json",
            headers={"Authorization": f"Bearer {self.access_token}"},
            data={"command": "APPEND", "media_id": media_id, "segment_index": 0},
            files={"media": img_data})

        # Step 3: FINALIZE
        fin_r = requests.post("https://upload.twitter.com/1.1/media/upload.json",
            headers={"Authorization": f"Bearer {self.access_token}"},
            data={"command": "FINALIZE", "media_id": media_id})
        fin_r.raise_for_status()
        return media_id

    # ── Analytics ──────────────────────────────────────────────────────────────
    def get_tweet_metrics(self, tweet_id: str) -> dict:
        r = requests.get(f"{TW_API_BASE}/tweets/{tweet_id}", headers=self._headers,
                         params={"tweet.fields": "public_metrics,non_public_metrics,organic_metrics"})
        r.raise_for_status()
        d = r.json().get("data", {})
        return {**d.get("public_metrics", {}), **d.get("organic_metrics", {})}

    def get_user_metrics(self) -> dict:
        if not self.user_id: return {}
        r = requests.get(f"{TW_API_BASE}/users/{self.user_id}", headers=self._headers,
                         params={"user.fields": "public_metrics"})
        r.raise_for_status()
        return r.json().get("data", {}).get("public_metrics", {})
