"""
Run this ONCE to get your Google Ads OAuth refresh token.
Steps:
  1. Fill in your CLIENT_ID and CLIENT_SECRET below (from Google Cloud Console)
  2. Run: python get_google_ads_token.py
  3. A browser opens — log in with your Google Ads account
  4. Paste the code back here
  5. Your refresh token will print — copy it into .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")

if not CLIENT_ID or not CLIENT_SECRET:
    print("\n❌  Set GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET in your .env first.\n")
    exit(1)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Run: pip install google-auth-oauthlib")
    exit(1)

SCOPES = ["https://www.googleapis.com/auth/adwords"]

client_config = {
    "installed": {
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
        "token_uri":     "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    }
}

print("\nOpening browser for Google authorisation...")
print("Sign in with the Google account that owns your Google Ads account.\n")

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
credentials = flow.run_local_server(port=0)

print("\n" + "="*60)
print("SUCCESS! Add these to your .env file:")
print("="*60)
print(f"GOOGLE_ADS_REFRESH_TOKEN={credentials.refresh_token}")
print("="*60 + "\n")
