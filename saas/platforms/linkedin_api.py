"""
LinkedIn Marketing API — OAuth2, posting, and analytics.
"""
import os, requests
from urllib.parse import urlencode
from typing import Optional

LI_CLIENT_ID     = os.environ.get("LINKEDIN_CLIENT_ID", "")
LI_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
LI_API_BASE      = "https://api.linkedin.com/v2"
LI_AUTH_BASE     = "https://www.linkedin.com/oauth/v2"

class LinkedInAPI:

    def __init__(self, access_token: str = None, person_urn: str = None,
                 org_urn: str = None):
        self.access_token = access_token
        self.person_urn   = person_urn   # "urn:li:person:xxxxxxx"
        self.org_urn      = org_urn      # "urn:li:organization:xxxxxxx" (for company pages)

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type":  "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    # ── OAuth ──────────────────────────────────────────────────────────────────
    @staticmethod
    def get_auth_url(redirect_uri: str, scope: str, state: str = "") -> str:
        params = {
            "response_type": "code",
            "client_id":     LI_CLIENT_ID,
            "redirect_uri":  redirect_uri,
            "scope":         scope,
            "state":         state,
        }
        return f"{LI_AUTH_BASE}/authorization?{urlencode(params)}"

    @staticmethod
    def exchange_code(code: str, redirect_uri: str) -> dict:
        r = requests.post(f"{LI_AUTH_BASE}/accessToken", data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  redirect_uri,
            "client_id":     LI_CLIENT_ID,
            "client_secret": LI_CLIENT_SECRET,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        r.raise_for_status()
        return r.json()   # {"access_token": ..., "expires_in": ..., "refresh_token": ...}

    def get_profile(self) -> dict:
        r = requests.get(f"{LI_API_BASE}/me", headers=self._headers,
                         params={"projection": "(id,localizedFirstName,localizedLastName,profilePicture(displayImage~:playableStreams))"})
        r.raise_for_status()
        return r.json()

    def get_organizations(self) -> list:
        """Return organizations (company pages) where user is an admin."""
        r = requests.get(f"{LI_API_BASE}/organizationalEntityAcls",
                         headers=self._headers,
                         params={"q": "roleAssignee", "role": "ADMINISTRATOR",
                                 "state": "APPROVED",
                                 "projection": "(elements*(organizationalTarget~(id,localizedName,logoV2(original~:playableStreams))))"})
        r.raise_for_status()
        return r.json().get("elements", [])

    # ── Posting ────────────────────────────────────────────────────────────────
    def create_post(self, text: str, image_url: str = None,
                    author_urn: str = None) -> dict:
        """Create a LinkedIn post (personal or company page)."""
        author = author_urn or self.org_urn or self.person_urn
        if not author:
            raise ValueError("author_urn (person or org URN) required")

        body = {
            "author":         author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        if image_url:
            # Step 1: register upload
            reg_r = requests.post(f"{LI_API_BASE}/assets?action=registerUpload",
                headers=self._headers, json={
                    "registerUploadRequest": {
                        "recipes":          ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner":            author,
                        "serviceRelationships": [{
                            "relationshipType": "OWNER",
                            "identifier":       "urn:li:userGeneratedContent",
                        }],
                    }
                })
            reg_r.raise_for_status()
            reg = reg_r.json()
            upload_url  = reg["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            asset_urn   = reg["value"]["asset"]

            # Step 2: upload image bytes from URL
            img_data = requests.get(image_url).content
            requests.put(upload_url, data=img_data,
                         headers={"Authorization": f"Bearer {self.access_token}",
                                  "Content-Type": "image/jpeg"})

            # Step 3: attach image to post
            body["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
            body["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                "status":       "READY",
                "description":  {"text": text[:200]},
                "media":        asset_urn,
                "title":        {"text": ""},
            }]

        r = requests.post(f"{LI_API_BASE}/ugcPosts",
                          headers=self._headers, json=body)
        r.raise_for_status()
        post_urn = r.headers.get("X-RestLi-Id", "")
        return {"id": post_urn, "author": author}

    # ── Analytics ──────────────────────────────────────────────────────────────
    def get_post_stats(self, post_urn: str) -> dict:
        """Return engagement stats for a specific post."""
        encoded = requests.utils.quote(post_urn, safe="")
        r = requests.get(f"{LI_API_BASE}/socialMetadata/{encoded}",
                         headers=self._headers)
        r.raise_for_status()
        d = r.json()
        return {
            "likes":    d.get("totalSocialActivityCounts", {}).get("numLikes", 0),
            "comments": d.get("totalSocialActivityCounts", {}).get("numComments", 0),
            "shares":   d.get("totalSocialActivityCounts", {}).get("numShares", 0),
        }

    def get_org_follower_stats(self, org_id: str) -> dict:
        """Return follower count for an organization."""
        r = requests.get(f"{LI_API_BASE}/networkSizes/urn:li:organization:{org_id}",
                         headers=self._headers,
                         params={"edgeType": "CompanyFollowedByMember"})
        r.raise_for_status()
        return {"followers": r.json().get("firstDegreeSize", 0)}
