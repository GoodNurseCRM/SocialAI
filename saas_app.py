"""
AdFlow AI — Multi-tenant SaaS Marketing Agent
Entry point: streamlit run saas_app.py --server.port 8502
"""
import streamlit as st
import os, json, uuid, base64
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="AdFlow AI — AI-Powered Ad Growth",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import saas.db as db
from saas.config import TIERS, PLATFORMS

def _base_url() -> str:
    """Return the app base URL — production or localhost."""
    return os.environ.get("APP_BASE_URL", "http://localhost:8502").rstrip("/")

def _oauth_button(label: str, url: str, bg: str) -> None:
    """Render an OAuth button that opens the auth URL in a new tab.

    Streamlit's app iframe sandbox lacks `allow-top-navigation`, so we cannot
    redirect the parent window. It does include `allow-popups-to-escape-sandbox`,
    so a `target="_blank"` link opens a fresh top-level tab where Facebook's
    OAuth screen can render.
    """
    from html import escape
    safe = escape(url)
    st.components.v1.html(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:4px 0;background:transparent;">
<a href="{safe}" target="_blank" rel="noopener"
   style="display:block;background:{bg};color:#fff;padding:11px 0;
          border-radius:10px;font-weight:700;font-size:13px;
          text-decoration:none;text-align:center;cursor:pointer;
          font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  {label}
</a>
</body></html>""", height=50)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stMain"] .block-container { padding: 0 !important; }

/* ── Dark futuristic base ── */
[data-testid="stApp"] {
  background: #080C18 !important;
  color: #E2E8F0 !important;
}
[data-testid="stMain"] { background: transparent !important; }

/* ── Animated grid background ── */
.sa-bg {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background: #080C18;
  background-image:
    radial-gradient(ellipse 80% 50% at 20% 10%, rgba(124,58,237,0.18) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 90%, rgba(6,182,212,0.12) 0%, transparent 60%),
    linear-gradient(rgba(124,58,237,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(124,58,237,0.04) 1px, transparent 1px);
  background-size: 100% 100%, 100% 100%, 56px 56px, 56px 56px;
  animation: bgGridShift 25s linear infinite;
}
@keyframes bgGridShift {
  0%   { background-position: 0 0, 0 0, 0 0, 0 0; }
  100% { background-position: 0 0, 0 0, 56px 56px, 56px 56px; }
}

/* ── Topbar ── */
.sa-topbar { position: sticky; top: 0; z-index: 999; }
.sa-header {
  background: rgba(8,12,24,0.92);
  backdrop-filter: blur(24px);
  border-bottom: 1px solid rgba(124,58,237,0.25);
  padding: 12px 28px;
  display: flex; align-items: center; justify-content: space-between;
  position: relative; z-index: 100;
}

/* Logo */
.sa-logo-wrap { display: flex; align-items: center; gap: 12px; text-decoration: none; }
.sa-logo-svg { filter: drop-shadow(0 0 8px rgba(124,58,237,0.8)); }
.sa-logo-name {
  font-size: 20px; font-weight: 800; letter-spacing: -0.5px;
  background: linear-gradient(90deg, #A78BFA, #06B6D4, #A78BFA);
  background-size: 200% auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  animation: logoGrad 4s linear infinite;
}
.sa-logo-tagline { font-size: 10px; color: #64748B; letter-spacing: 0.5px; margin-top: 1px; }
@keyframes logoGrad {
  0%   { background-position: 0% center; }
  100% { background-position: 200% center; }
}

/* Header right side */
.sa-header-right { display: flex; align-items: center; gap: 16px; }
.sa-stat-pill {
  font-size: 11px; color: #94A3B8; padding: 4px 12px;
  border: 1px solid rgba(124,58,237,0.25); border-radius: 20px;
  background: rgba(124,58,237,0.08);
}
.sa-tier-pill {
  font-size: 10px; font-weight: 800; letter-spacing: 1px;
  color: #A78BFA; padding: 4px 12px; border-radius: 20px;
  background: rgba(124,58,237,0.15);
  border: 1px solid rgba(124,58,237,0.4);
  animation: tierPulse 3s ease-in-out infinite;
}
@keyframes tierPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(124,58,237,0.3); }
  50%       { box-shadow: 0 0 0 6px rgba(124,58,237,0); }
}

/* User menu dropdown */
.sa-user-menu {
  position: relative; cursor: pointer;
  display: flex; align-items: center; gap: 10px;
  padding: 7px 14px; border-radius: 12px;
  border: 1px solid rgba(124,58,237,0.2);
  background: rgba(124,58,237,0.08);
  transition: all 0.2s;
  user-select: none;
}
.sa-user-menu:hover { border-color: rgba(124,58,237,0.5); background: rgba(124,58,237,0.14); }
.sa-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, #7C3AED, #06B6D4);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 800; color: white;
  box-shadow: 0 0 12px rgba(124,58,237,0.5);
  flex-shrink: 0;
}
.sa-user-name-text { font-size: 13px; font-weight: 600; color: #E2E8F0; }
.sa-user-chevron { font-size: 10px; color: #64748B; transition: transform 0.2s; }
.sa-user-menu:hover .sa-user-chevron { transform: rotate(180deg); }

.sa-dropdown {
  display: none; position: absolute; right: 0; top: 100%;
  background: rgba(12,17,35,0.97); backdrop-filter: blur(24px);
  border: 1px solid rgba(124,58,237,0.3); border-radius: 14px;
  padding: 14px 6px 6px; min-width: 200px; z-index: 9999;
  box-shadow: 0 20px 60px rgba(0,0,0,0.6), 0 0 0 1px rgba(124,58,237,0.1);
  animation: dropIn 0.15s ease;
}
@keyframes dropIn {
  from { opacity: 0; transform: translateY(-6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.sa-user-menu:focus-within .sa-dropdown { display: block; }
.sa-dropdown.open { display: block !important; }
.sa-dd-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 10px;
  font-size: 13px; font-weight: 500; color: #CBD5E1;
  text-decoration: none !important;
  transition: all 0.15s;
}
.sa-dd-item:hover { background: rgba(124,58,237,0.15); color: #A78BFA; }
.sa-dd-divider { height: 1px; background: rgba(124,58,237,0.15); margin: 4px 0; }
.sa-dd-logout:hover { background: rgba(239,68,68,0.12); color: #FCA5A5; }

/* ── Nav bar ── */
.sa-nav {
  background: rgba(8,12,24,0.85); backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(124,58,237,0.15);
  padding: 0 28px; display: flex; gap: 0;
}
.sa-nav a {
  padding: 12px 16px; font-size: 12px; font-weight: 600;
  color: #64748B; text-decoration: none !important;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
  transition: all 0.2s; letter-spacing: 0.3px;
}
.sa-nav a:hover { color: #A78BFA; }
.sa-nav-active {
  color: #A78BFA !important; border-bottom-color: #7C3AED !important;
  text-shadow: 0 0 20px rgba(167,139,250,0.5);
}

/* ── Page content ── */
.sa-page { padding: 0; background: transparent; }

/* ── Glass cards ── */
.card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(124,58,237,0.2);
  border-radius: 14px; padding: 18px 20px;
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 24px rgba(0,0,0,0.3);
  margin-bottom: 14px;
  transition: all 0.25s;
}
.card:hover {
  border-color: rgba(124,58,237,0.45);
  box-shadow: 0 0 30px rgba(124,58,237,0.12), 0 4px 24px rgba(0,0,0,0.4);
  transform: translateY(-2px);
}
.card-title { font-size: 14px; font-weight: 700; color: #E2E8F0; margin-bottom: 4px; }
.card-sub   { font-size: 12px; color: #64748B; }

/* ── Platform tiles ── */
.plat-tile {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px; padding: 18px 14px;
  text-align: center; border-top: 3px solid rgba(255,255,255,0.1);
  transition: all 0.25s; cursor: pointer;
}
.plat-tile:hover {
  background: rgba(124,58,237,0.08);
  border-color: rgba(124,58,237,0.35);
  transform: translateY(-3px);
  box-shadow: 0 8px 30px rgba(124,58,237,0.2);
}
.plat-tile-connected {
  border-color: rgba(34,197,94,0.4) !important;
  background: rgba(34,197,94,0.05) !important;
}
.plat-tile-connected:hover { box-shadow: 0 8px 30px rgba(34,197,94,0.15) !important; }
.plat-tile-locked { opacity: 0.4; cursor: not-allowed; }
.plat-tile-locked:hover { transform: none; box-shadow: none; }
.plat-icon  { font-size: 30px; margin-bottom: 8px; animation: iconFloat 3s ease-in-out infinite; }
.plat-tile:nth-child(2) .plat-icon { animation-delay: 0.4s; }
.plat-tile:nth-child(3) .plat-icon { animation-delay: 0.8s; }
.plat-tile:nth-child(4) .plat-icon { animation-delay: 1.2s; }
.plat-tile:nth-child(5) .plat-icon { animation-delay: 1.6s; }
@keyframes iconFloat {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-5px); }
}
.plat-name   { font-size: 13px; font-weight: 700; color: #CBD5E1; }
.plat-status { font-size: 11px; margin-top: 4px; }

/* ── Metrics ── */
.metric-row { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.metric-box {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(124,58,237,0.18);
  border-radius: 12px; padding: 16px 18px;
  flex: 1; min-width: 110px; text-align: center;
  backdrop-filter: blur(12px);
  transition: all 0.25s;
  animation: metricIn 0.4s ease both;
}
.metric-box:hover {
  border-color: rgba(124,58,237,0.45);
  box-shadow: 0 0 25px rgba(124,58,237,0.15);
  transform: translateY(-2px);
}
.metric-val {
  font-size: 26px; font-weight: 800; line-height: 1;
  background: linear-gradient(135deg, #A78BFA, #06B6D4);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.metric-lbl { font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 5px; }
@keyframes metricIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Post cards ── */
.post-card {
  background: rgba(255,255,255,0.03);
  border-radius: 12px; padding: 14px 16px;
  border: 1px solid rgba(255,255,255,0.07);
  border-left: 3px solid #7C3AED;
  margin-bottom: 10px; backdrop-filter: blur(12px);
  transition: all 0.2s;
}
.post-card:hover { border-left-color: #A78BFA; background: rgba(124,58,237,0.06); }
.post-status-published { border-left-color: #22C55E !important; }
.post-status-scheduled { border-left-color: #F59E0B !important; }
.post-status-draft     { border-left-color: #475569 !important; }
.post-status-failed    { border-left-color: #EF4444 !important; }

/* ── Section title ── */
.sec-title {
  font-size: 13px; font-weight: 700; color: #64748B;
  margin: 16px 0 10px; padding-bottom: 6px;
  border-bottom: 1px solid rgba(124,58,237,0.15);
  text-transform: uppercase; letter-spacing: 1px;
}
.page-title {
  font-size: 24px; font-weight: 800; color: #E2E8F0;
  margin-bottom: 4px; letter-spacing: -0.5px;
}
.page-sub { font-size: 13px; color: #475569; margin-bottom: 20px; }

/* ── Pricing ── */
.pricing-card-highlight { border: 1px solid rgba(124,58,237,0.5) !important; }

/* ── Upgrade gate ── */
.upgrade-gate {
  background: rgba(124,58,237,0.08);
  border-radius: 14px; padding: 28px 24px; text-align: center;
  border: 1px dashed rgba(124,58,237,0.35);
}

/* ── Suggestions ── */
.sugg {
  background: rgba(255,255,255,0.03); border-radius: 12px; padding: 16px 20px;
  margin-bottom: 10px; border-left: 4px solid #475569;
  backdrop-filter: blur(12px);
}
.sugg-HIGH   { border-left-color: #EF4444; }
.sugg-MEDIUM { border-left-color: #F59E0B; }
.sugg-LOW    { border-left-color: #22C55E; }

/* ── Auth page ── */
.auth-wrap {
  max-width: 440px; margin: 0 auto; padding: 24px 32px 20px;
  background: rgba(8,12,24,0.85); border-radius: 22px;
  border: 1px solid rgba(124,58,237,0.35);
  backdrop-filter: blur(24px);
  box-shadow: 0 0 80px rgba(124,58,237,0.2), 0 24px 60px rgba(0,0,0,0.6),
              inset 0 1px 0 rgba(255,255,255,0.04);
  animation: islandIn 0.5s cubic-bezier(0.34,1.56,0.64,1) both;
}
.auth-logo  { font-size: 36px; text-align: center; margin-bottom: 4px; }
.auth-title { font-size: 20px; font-weight: 800; color: #E2E8F0; text-align: center; margin-bottom: 2px; }
.auth-sub   { font-size: 12px; color: #64748B; text-align: center; margin-bottom: 12px; }

/* ── Streamlit overrides for dark mode ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stNumberInput"] input {
  background: rgba(15,23,42,0.85) !important;
  border: 1px solid rgba(124,58,237,0.25) !important;
  color: #E2E8F0 !important;
  border-radius: 10px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: rgba(124,58,237,0.6) !important;
  box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important;
}
[data-baseweb="tab-list"] {
  background: rgba(255,255,255,0.03) !important;
  border-radius: 10px !important; gap: 4px !important; padding: 4px !important;
}
[data-baseweb="tab"] {
  background: transparent !important; border-radius: 8px !important;
  color: #64748B !important; font-size: 13px !important;
}
[aria-selected="true"][data-baseweb="tab"] {
  background: rgba(124,58,237,0.2) !important; color: #A78BFA !important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li { color: #94A3B8; }
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 { color: #E2E8F0; }
[data-testid="stExpander"] { background: rgba(255,255,255,0.03) !important; border: 1px solid rgba(124,58,237,0.2) !important; border-radius: 10px !important; }
[data-testid="stAlert"] { background: rgba(124,58,237,0.1) !important; border: 1px solid rgba(124,58,237,0.25) !important; color: #CBD5E1 !important; }
[data-testid="stInfo"] { background: rgba(6,182,212,0.08) !important; border-color: rgba(6,182,212,0.25) !important; }
[data-testid="stSuccess"] { background: rgba(34,197,94,0.08) !important; border-color: rgba(34,197,94,0.25) !important; }
[data-testid="stError"]   { background: rgba(239,68,68,0.08) !important;  border-color: rgba(239,68,68,0.25) !important; }
[data-testid="stWarning"] { background: rgba(245,158,11,0.08) !important; border-color: rgba(245,158,11,0.25) !important; }

/* label colours */
[data-testid="stWidgetLabel"] p { color: #94A3B8 !important; font-size: 12px !important; }
[data-testid="stCheckbox"] p, [data-testid="stRadio"] p { color: #94A3B8 !important; }

/* Buttons */
div[data-testid="stButton"] > button {
  border-radius: 10px !important; font-weight: 600 !important;
  transition: all 0.2s !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #7C3AED, #6D28D9) !important;
  border: none !important; color: white !important;
  box-shadow: 0 4px 15px rgba(124,58,237,0.35) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #8B5CF6, #7C3AED) !important;
  box-shadow: 0 6px 25px rgba(124,58,237,0.55) !important;
  transform: translateY(-1px) !important;
}
div[data-testid="stButton"] > button[kind="secondary"] {
  background: rgba(124,58,237,0.1) !important;
  border: 1px solid rgba(124,58,237,0.3) !important;
  color: #A78BFA !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
  background: rgba(124,58,237,0.2) !important;
  border-color: rgba(124,58,237,0.5) !important;
}
[data-testid="stSidebar"] { display: none !important; }

/* ── Chat interface ── */
.chat-wrap {
  max-width: 820px; margin: 0 auto;
}
.chat-msg {
  display: flex; gap: 12px; margin-bottom: 18px; animation: msgIn 0.25s ease;
}
@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.chat-msg-user  { flex-direction: row-reverse; }
.chat-bubble {
  max-width: 75%; padding: 12px 16px; border-radius: 16px;
  font-size: 14px; line-height: 1.55; color: #E2E8F0;
  backdrop-filter: blur(12px);
}
.chat-bubble-ai {
  background: rgba(124,58,237,0.12);
  border: 1px solid rgba(124,58,237,0.25);
  border-bottom-left-radius: 4px;
}
.chat-bubble-user {
  background: rgba(6,182,212,0.12);
  border: 1px solid rgba(6,182,212,0.25);
  border-bottom-right-radius: 4px;
  text-align: right;
}
.chat-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; flex-shrink: 0;
  background: rgba(124,58,237,0.2);
  border: 1px solid rgba(124,58,237,0.3);
}

/* ── Campaign plan ── */
.plan-header {
  background: linear-gradient(135deg, rgba(124,58,237,0.15), rgba(6,182,212,0.08));
  border: 1px solid rgba(124,58,237,0.3);
  border-radius: 18px; padding: 24px 28px; margin-bottom: 20px;
}
.plan-title {
  font-size: 22px; font-weight: 800; color: #E2E8F0;
  background: linear-gradient(90deg, #A78BFA, #06B6D4);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 6px;
}
.plan-meta { font-size: 13px; color: #64748B; display: flex; gap: 16px; flex-wrap: wrap; }
.plan-meta span { display: flex; align-items: center; gap: 6px; }

.channel-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(124,58,237,0.2);
  border-radius: 14px; padding: 18px;
  transition: all 0.25s;
}
.channel-card:hover {
  border-color: rgba(124,58,237,0.45);
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(124,58,237,0.12);
}
.channel-icon { font-size: 28px; margin-bottom: 8px; }
.channel-name { font-size: 14px; font-weight: 700; color: #E2E8F0; }
.channel-budget { font-size: 20px; font-weight: 800; color: #A78BFA; margin: 6px 0; }
.channel-stat { font-size: 11px; color: #64748B; }

.content-item {
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.06);
  border-left: 3px solid #7C3AED;
  border-radius: 10px; padding: 12px 14px; margin-bottom: 8px;
  transition: all 0.2s;
}
.content-item:hover { background: rgba(124,58,237,0.06); border-left-color: #A78BFA; }
.content-date { font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: 0.8px; }
.content-title { font-size: 13px; font-weight: 700; color: #CBD5E1; margin: 3px 0; }
.content-brief { font-size: 12px; color: #64748B; }
.content-platform-badge {
  display: inline-block; font-size: 10px; font-weight: 700;
  padding: 2px 8px; border-radius: 6px; margin-right: 6px;
  background: rgba(124,58,237,0.15); color: #A78BFA;
  border: 1px solid rgba(124,58,237,0.25);
}

/* ── Onboarding ── */
.onboard-hero {
  text-align: center; padding: 32px 20px 24px;
  max-width: 580px; margin: 0 auto;
}
.onboard-steps {
  display: flex; justify-content: center; gap: 8px;
  margin: 16px 0; flex-wrap: wrap;
}
.step-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: rgba(124,58,237,0.25);
  border: 1px solid rgba(124,58,237,0.3);
  transition: all 0.3s;
}
.step-dot-done { background: #7C3AED; }
.step-dot-active { background: #A78BFA; transform: scale(1.4); }

/* ── Approve bar ── */
.approve-bar {
  position: sticky; bottom: 0; left: 0; right: 0;
  background: rgba(8,12,24,0.95); backdrop-filter: blur(20px);
  border-top: 1px solid rgba(124,58,237,0.3);
  padding: 14px 28px; display: flex; gap: 12px; align-items: center;
  z-index: 500;
}

/* ── Admin dashboard ── */
.admin-banner {
  background: linear-gradient(135deg, rgba(124,58,237,0.2), rgba(6,182,212,0.12));
  border: 1px solid rgba(124,58,237,0.4); border-radius: 14px;
  padding: 16px 22px; margin-bottom: 20px;
  display: flex; align-items: center; gap: 14px;
}
.admin-badge {
  font-size: 10px; font-weight: 900; letter-spacing: 2px;
  color: #A78BFA; background: rgba(124,58,237,0.2);
  border: 1px solid rgba(124,58,237,0.4); border-radius: 6px;
  padding: 4px 10px;
}
.sub-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px; padding: 16px 18px;
  transition: all 0.25s; cursor: pointer;
  position: relative; overflow: hidden;
}
.sub-card:hover {
  border-color: rgba(124,58,237,0.4);
  background: rgba(124,58,237,0.06);
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(124,58,237,0.15);
}
.sub-card-top {
  display: flex; align-items: flex-start;
  justify-content: space-between; margin-bottom: 10px;
}
.sub-name  { font-size: 14px; font-weight: 800; color: #E2E8F0; }
.sub-email { font-size: 11px; color: #64748B; margin-top: 2px; }
.health-pill {
  font-size: 10px; font-weight: 800; padding: 3px 10px;
  border-radius: 20px; letter-spacing: 0.5px; white-space: nowrap;
}
.sub-stats {
  display: flex; gap: 12px; flex-wrap: wrap;
  font-size: 11px; color: #475569;
}
.sub-stat { display: flex; align-items: center; gap: 4px; }
.health-bar-bg {
  height: 3px; background: rgba(255,255,255,0.06);
  border-radius: 2px; margin-top: 10px;
}
.health-bar-fill {
  height: 3px; border-radius: 2px;
  transition: width 0.4s ease;
}

/* ── Impersonation banner ── */
.impersonate-bar {
  background: rgba(245,158,11,0.12);
  border-bottom: 2px solid rgba(245,158,11,0.4);
  padding: 8px 28px; display: flex; align-items: center;
  justify-content: space-between; font-size: 12px; color: #FCD34D;
  position: sticky; top: 0; z-index: 1000;
}

/* ── Model picker ── */
.model-card {
  background: rgba(255,255,255,0.03);
  border: 2px solid rgba(255,255,255,0.07);
  border-radius: 14px; padding: 14px 16px;
  cursor: pointer; transition: all 0.2s;
  position: relative;
}
.model-card:hover {
  border-color: rgba(124,58,237,0.4);
  background: rgba(124,58,237,0.06);
}
.model-card-selected {
  border-color: #7C3AED !important;
  background: rgba(124,58,237,0.12) !important;
  box-shadow: 0 0 0 1px rgba(124,58,237,0.3);
}
.model-provider { font-size: 10px; font-weight: 800; letter-spacing: 1px; color: #64748B; }
.model-name     { font-size: 14px; font-weight: 800; color: #E2E8F0; margin: 3px 0; }
.model-desc     { font-size: 11px; color: #64748B; line-height: 1.4; }
.model-cost     { font-size: 11px; font-weight: 700; margin-top: 8px; }
.tier-badge-model {
  position: absolute; top: 10px; right: 10px;
  font-size: 9px; font-weight: 800; letter-spacing: 1px;
  padding: 2px 7px; border-radius: 5px;
}
.recommended-badge {
  position: absolute; bottom: 10px; right: 10px;
  font-size: 9px; font-weight: 800; color: #A78BFA;
  background: rgba(124,58,237,0.15); border: 1px solid rgba(124,58,237,0.3);
  padding: 2px 7px; border-radius: 5px; letter-spacing: 0.5px;
}

/* ═══════════════════════════════════════════════════════
   3D UI LAYER — perspective, depth, floating elements
   ═══════════════════════════════════════════════════════ */

/* ── 3D preserve on all interactive cards ── */
.card, .metric-box, .channel-card, .sub-card, .plat-tile, .post-card {
  position: relative;
  transform-style: preserve-3d;
  will-change: transform;
  transition: transform 0.18s cubic-bezier(0.4,0,0.2,1),
              box-shadow 0.18s, border-color 0.18s !important;
}
.card:hover {
  transform: perspective(800px) rotateX(-3deg) rotateY(3deg) translateY(-6px) translateZ(8px) !important;
  box-shadow: 0 0 35px rgba(124,58,237,0.2), 0 28px 50px rgba(0,0,0,0.55), 0 8px 16px rgba(0,0,0,0.3) !important;
  border-color: rgba(124,58,237,0.55) !important;
}
.metric-box:hover {
  transform: perspective(600px) rotateX(-2deg) rotateY(3deg) translateY(-5px) translateZ(6px) !important;
  box-shadow: 0 0 28px rgba(124,58,237,0.22), 0 20px 44px rgba(0,0,0,0.5) !important;
  border-color: rgba(124,58,237,0.55) !important;
}
.channel-card:hover {
  transform: perspective(700px) rotateX(-4deg) rotateY(4deg) translateY(-7px) translateZ(10px) !important;
  box-shadow: 0 24px 56px rgba(124,58,237,0.22), 0 8px 18px rgba(0,0,0,0.45) !important;
}
.sub-card:hover {
  transform: perspective(900px) rotateX(-2deg) rotateY(2.5deg) translateY(-5px) translateZ(7px) !important;
  box-shadow: 0 22px 52px rgba(124,58,237,0.22), 0 8px 18px rgba(0,0,0,0.45) !important;
}
.plat-tile:hover {
  transform: perspective(600px) rotateX(-5deg) rotateY(5deg) translateY(-8px) translateZ(12px) !important;
  box-shadow: 0 24px 56px rgba(124,58,237,0.32), 0 8px 20px rgba(0,0,0,0.5) !important;
}

/* ── Spinning conic border ring on hover ── */
@property --ba { syntax: '<angle>'; initial-value: 0deg; inherits: false; }
@keyframes spin-border { to { --ba: 360deg; } }
.card::before, .metric-box::before {
  content: ''; position: absolute; inset: -1.5px; border-radius: inherit;
  background: conic-gradient(from var(--ba), transparent 55%, rgba(124,58,237,0.9) 70%,
    rgba(6,182,212,0.8) 82%, transparent 97%);
  opacity: 0; z-index: -1; pointer-events: none; transition: opacity 0.35s;
}
.card:hover::before { opacity: 1; animation: spin-border 2.4s linear infinite; }
.metric-box:hover::before { opacity: 1; animation: spin-border 3s linear infinite; }

/* ── Deep glow on primary buttons ── */
div[data-testid="stButton"] > button[kind="primary"]:hover {
  box-shadow: 0 0 16px rgba(124,58,237,0.55), 0 0 32px rgba(124,58,237,0.3),
              0 0 48px rgba(124,58,237,0.14), 0 6px 22px rgba(124,58,237,0.45) !important;
  transform: translateY(-2px) scale(1.01) !important;
}
div[data-testid="stButton"] > button:active { transform: translateY(1px) scale(0.98) !important; }

/* ── Topbar 3D depth ── */
.sa-header {
  box-shadow: 0 1px 0 rgba(124,58,237,0.22), 0 4px 22px rgba(0,0,0,0.45),
              0 0 50px rgba(124,58,237,0.06) !important;
}

/* ── Floating nav island ── */
.sa-nav {
  display: flex !important; justify-content: center !important;
  padding: 10px 28px 15px !important;
  background: transparent !important; border-bottom: none !important;
}
.sa-nav-island {
  display: flex; gap: 2px; align-items: center;
  background: rgba(5,7,18,0.93);
  backdrop-filter: blur(30px) saturate(180%);
  -webkit-backdrop-filter: blur(30px) saturate(180%);
  border: 1px solid rgba(124,58,237,0.42);
  border-radius: 100px; padding: 5px 9px;
  box-shadow: 0 0 0 1px rgba(124,58,237,0.1), 0 8px 36px rgba(0,0,0,0.65),
              0 0 60px rgba(124,58,237,0.1), inset 0 1px 0 rgba(255,255,255,0.04);
  animation: islandIn 0.45s cubic-bezier(0.34,1.56,0.64,1) both;
}
@keyframes islandIn {
  from { opacity: 0; transform: translateY(-10px) scale(0.93); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
.sa-nav-island a {
  padding: 7px 14px !important; font-size: 11px !important; font-weight: 600 !important;
  color: #475569 !important; text-decoration: none !important;
  border-radius: 50px !important; border-bottom: none !important;
  transition: all 0.2s cubic-bezier(0.4,0,0.2,1) !important;
  letter-spacing: 0.3px !important; white-space: nowrap !important;
  display: inline-flex !important; align-items: center !important;
}
.sa-nav-island a:hover { color: #C4B5FD !important; background: rgba(124,58,237,0.14) !important; transform: translateY(-1px) !important; }
.sa-nav-island .sa-nav-active {
  color: #F1F5F9 !important;
  background: linear-gradient(135deg, rgba(124,58,237,0.34), rgba(6,182,212,0.16)) !important;
  border: 1px solid rgba(124,58,237,0.48) !important;
  box-shadow: 0 0 16px rgba(124,58,237,0.3), inset 0 1px 0 rgba(255,255,255,0.1) !important;
  text-shadow: 0 0 12px rgba(167,139,250,0.5) !important;
}

/* ── Logo color-shift glow ── */
.sa-logo-svg {
  filter: drop-shadow(0 0 8px rgba(124,58,237,0.9)) drop-shadow(0 0 18px rgba(6,182,212,0.3)) !important;
  animation: logoGlow 6s ease-in-out infinite !important;
}
@keyframes logoGlow {
  0%,100% { filter: drop-shadow(0 0 8px rgba(124,58,237,0.9)) drop-shadow(0 0 18px rgba(6,182,212,0.3)); }
  50%      { filter: drop-shadow(0 0 14px rgba(6,182,212,0.95)) drop-shadow(0 0 26px rgba(124,58,237,0.4)); }
}

/* ── Avatar orbit ring ── */
.sa-avatar {
  box-shadow: 0 0 0 2px rgba(124,58,237,0.35), 0 0 0 4px rgba(124,58,237,0.1),
              0 0 18px rgba(124,58,237,0.55) !important;
}

/* ── Page-in animation ── */
.sa-page { animation: pageIn 0.38s cubic-bezier(0.4,0,0.2,1) both; }
@keyframes pageIn {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ═══════════════════════════════════════════════
   LEX — Floating AI Agent Widget
   ═══════════════════════════════════════════════ */
#lex-widget {
  position: fixed; bottom: 92px; right: 26px;
  z-index: 9998; font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
}
.lex-orb-wrap { position: relative; width: 66px; height: 66px; cursor: pointer; user-select: none; }
.lex-orb {
  width: 66px; height: 66px; border-radius: 50%;
  background: linear-gradient(135deg, #7C3AED 0%, #2563EB 55%, #06B6D4 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 28px; position: relative; z-index: 2;
  box-shadow: 0 8px 26px rgba(0,0,0,0.55), 0 0 40px rgba(124,58,237,0.45);
  transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
  animation: lexPulse 3s ease-in-out infinite;
}
@keyframes lexPulse {
  0%,100% { box-shadow: 0 8px 26px rgba(0,0,0,0.55), 0 0 30px rgba(124,58,237,0.4), 0 0 0 0 rgba(124,58,237,0.3); }
  50%      { box-shadow: 0 8px 26px rgba(0,0,0,0.55), 0 0 55px rgba(124,58,237,0.65), 0 0 0 18px rgba(124,58,237,0); }
}
.lex-orb:hover { transform: scale(1.12) translateY(-4px); box-shadow: 0 14px 34px rgba(0,0,0,0.6), 0 0 70px rgba(124,58,237,0.75) !important; }
/* Dual spinning rings */
.lex-ring {
  position: absolute; inset: -10px; border-radius: 50%;
  border: 2px solid transparent;
  background: conic-gradient(from 0deg, transparent 48%, rgba(124,58,237,0.95) 62%,
    rgba(6,182,212,0.9) 74%, transparent 88%) border-box;
  -webkit-mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: destination-out; mask-composite: exclude;
  animation: lexRing 2.4s linear infinite; z-index: 3;
}
.lex-ring2 {
  position: absolute; inset: -18px; border-radius: 50%;
  border: 1.5px solid transparent;
  background: conic-gradient(from 180deg, transparent 50%, rgba(6,182,212,0.55) 64%,
    rgba(124,58,237,0.5) 76%, transparent 90%) border-box;
  -webkit-mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: destination-out; mask-composite: exclude;
  animation: lexRing 4.2s linear infinite reverse; z-index: 0;
}
@keyframes lexRing { to { transform: rotate(360deg); } }
/* Notification dot */
.lex-dot {
  position: absolute; top: 4px; right: 4px; z-index: 10;
  width: 14px; height: 14px; border-radius: 50%;
  background: linear-gradient(135deg, #EF4444, #F59E0B);
  border: 2px solid #080C18;
  animation: dotPop 0.5s cubic-bezier(0.34,1.56,0.64,1) 1.5s both;
}
@keyframes dotPop { from { transform: scale(0); } to { transform: scale(1); } }
/* Panel */
.lex-panel {
  position: absolute; bottom: 82px; right: 0; width: 334px;
  background: rgba(5,7,18,0.98);
  border: 1px solid rgba(124,58,237,0.42);
  border-radius: 22px;
  box-shadow: 0 28px 70px rgba(0,0,0,0.85), 0 0 0 1px rgba(124,58,237,0.12),
              0 0 60px rgba(124,58,237,0.1);
  backdrop-filter: blur(28px); overflow: hidden;
  opacity: 0; pointer-events: none;
  transform: scale(0.78) translateY(22px); transform-origin: bottom right;
  transition: all 0.38s cubic-bezier(0.34,1.56,0.64,1);
}
.lex-panel.open { opacity: 1; pointer-events: all; transform: scale(1) translateY(0); }
.lex-head {
  background: linear-gradient(135deg, rgba(124,58,237,0.3), rgba(6,182,212,0.14));
  border-bottom: 1px solid rgba(124,58,237,0.2);
  padding: 14px 16px; display: flex; align-items: center; gap: 10px;
}
.lex-head-av {
  width: 40px; height: 40px; border-radius: 50%;
  background: linear-gradient(135deg, #7C3AED, #0EA5E9);
  display: flex; align-items: center; justify-content: center;
  font-size: 19px; flex-shrink: 0;
  box-shadow: 0 0 18px rgba(124,58,237,0.65);
  animation: lexPulse 3s ease-in-out infinite;
}
.lex-head-title { font-size: 14px; font-weight: 800; color: #E2E8F0; letter-spacing: -0.3px; }
.lex-head-ctx   { font-size: 10px; color: #818CF8; margin-top: 2px; letter-spacing: 0.4px; }
.lex-x {
  margin-left: auto; width: 26px; height: 26px; border-radius: 50%;
  background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
  color: #475569; font-size: 12px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all 0.2s;
}
.lex-x:hover { background: rgba(239,68,68,0.16); color: #FCA5A5; border-color: rgba(239,68,68,0.3); }
.lex-body {
  padding: 14px; height: 252px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 10px;
  scrollbar-width: thin; scrollbar-color: rgba(124,58,237,0.3) transparent;
}
.lx-ai  { display: flex; gap: 7px; align-items: flex-start; animation: msgIn 0.22s ease; }
.lx-usr { display: flex; flex-direction: row-reverse; gap: 7px; align-items: flex-start; animation: msgIn 0.22s ease; }
.lx-bai {
  background: rgba(124,58,237,0.11); border: 1px solid rgba(124,58,237,0.22);
  border-radius: 14px 14px 14px 3px; padding: 9px 12px;
  font-size: 12px; color: #CBD5E1; line-height: 1.56; max-width: 244px;
}
.lx-busr {
  background: rgba(6,182,212,0.1); border: 1px solid rgba(6,182,212,0.22);
  border-radius: 14px 14px 3px 14px; padding: 9px 12px;
  font-size: 12px; color: #CBD5E1; line-height: 1.56; max-width: 244px;
}
.lx-av {
  width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 11px;
}
.lex-tip {
  display: inline-block; cursor: pointer;
  background: rgba(124,58,237,0.1); border: 1px solid rgba(124,58,237,0.25);
  border-radius: 20px; padding: 4px 10px;
  font-size: 11px; color: #A78BFA; margin: 3px 2px;
  transition: all 0.18s; line-height: 1.45;
}
.lex-tip:hover { background: rgba(124,58,237,0.22); border-color: rgba(124,58,237,0.55); transform: translateY(-1px); }
.lex-cta {
  display: block; text-align: center; text-decoration: none !important;
  background: linear-gradient(135deg, rgba(124,58,237,0.22), rgba(6,182,212,0.1));
  border: 1px solid rgba(124,58,237,0.38); border-radius: 11px;
  padding: 8px 12px; font-size: 11px; font-weight: 700; color: #A78BFA;
  margin-top: 6px; transition: all 0.2s;
}
.lex-cta:hover { border-color: rgba(124,58,237,0.65); background: rgba(124,58,237,0.3); transform: translateY(-1px); }
.lex-footer {
  padding: 10px 12px; border-top: 1px solid rgba(124,58,237,0.14);
  display: flex; gap: 8px; align-items: center;
}
.lex-inp {
  flex: 1; background: rgba(255,255,255,0.04);
  border: 1px solid rgba(124,58,237,0.24); border-radius: 50px;
  padding: 7px 14px; font-size: 12px; color: #E2E8F0; outline: none;
  transition: all 0.2s;
}
.lex-inp:focus { border-color: rgba(124,58,237,0.58); box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.lex-inp::placeholder { color: #2D3748; }
.lex-snd {
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, #7C3AED, #0EA5E9); border: none;
  color: white; cursor: pointer; font-size: 13px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s; box-shadow: 0 4px 14px rgba(124,58,237,0.45);
}
.lex-snd:hover { transform: scale(1.12); box-shadow: 0 6px 22px rgba(124,58,237,0.65); }
.lex-snd:active { transform: scale(0.94); }
@keyframes lexDot { 0%,80%,100% { transform:scale(0.6);opacity:0.25; } 40% { transform:scale(1);opacity:1; } }
.lex-typing { display:flex; gap:4px; padding:8px 12px; }
.lex-typing span { width:6px;height:6px;border-radius:50%;background:#A78BFA;animation:lexDot 1.2s infinite; }
.lex-typing span:nth-child(2) { animation-delay:0.2s; }
.lex-typing span:nth-child(3) { animation-delay:0.4s; }
</style>
""", unsafe_allow_html=True)

# Inject animated background layer (runs once per page load)
st.markdown('<div class="sa-bg"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE  (restore from URL token on page reload / navigation)
# ══════════════════════════════════════════════════════════════════════════════
for k, v in {
    "user": None, "draft_content": {}, "gen_images": [],
    "selected_platform": None, "post_draft": "", "session_token": "",
    # Onboarding state
    "onboarding_history": [], "onboarding_done": False,
    # Chat state
    "chat_history": [],
    # Ad plan state
    "active_campaign_id": None, "plan_generating": False,
    # Admin / impersonation
    "viewing_as": None,   # dict of subscriber user when owner is viewing their account
    "admin_search": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Restore session from URL token if session_state lost (e.g. nav via <a href>)
# Falls back to OAuth `state` param so the new-tab callback (target="_blank")
# can re-authenticate using the session token we carried through Meta.
if st.session_state.user is None:
    _tok = st.query_params.get("s", "") or (
        st.query_params.get("state", "") if st.query_params.get("oauth_callback") else ""
    )
    if _tok:
        _restored = db.get_session(_tok)
        if _restored:
            st.session_state.user = _restored
            st.session_state.session_token = _tok
            st.query_params["s"] = _tok


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_tab():
    return st.query_params.get("tab", "dashboard")

def go_to(tab: str):
    st.query_params["tab"] = tab
    if st.session_state.session_token:
        st.query_params["s"] = st.session_state.session_token
    st.rerun()

def _do_login(user: dict):
    """Set session state and create persistent session token."""
    # Promote to owner role if email matches OWNER_EMAIL
    owner_email = os.environ.get("OWNER_EMAIL", "").lower().strip()
    if owner_email and user.get("email", "").lower().strip() == owner_email:
        if user.get("role") != "owner":
            db._seed_owner()
            user = db.get_user_by_email(user["email"]) or user
    token = db.create_session(user["id"])
    st.session_state.user = user
    st.session_state.session_token = token
    st.query_params.clear()
    st.query_params["s"] = token
    st.rerun()

def _do_logout():
    """Clear session state and invalidate token."""
    if st.session_state.session_token:
        db.delete_session(st.session_state.session_token)
    st.session_state.user = None
    st.session_state.session_token = ""
    st.query_params.clear()
    st.rerun()

def get_tier():
    if not st.session_state.user: return TIERS["free"]
    from saas.billing import get_user_tier
    return get_user_tier(st.session_state.user["id"])

def get_connections():
    if not st.session_state.user: return []
    return db.get_all_connections(st.session_state.user["id"])

def platform_icon(pid: str) -> str:
    return PLATFORMS.get(pid, type("P", (), {"icon": "🌐"})()).icon

def platform_color(pid: str) -> str:
    return PLATFORMS.get(pid, type("P", (), {"color": "#94A3B8"})()).color

def active_user() -> dict:
    """Return the user whose data is being viewed — subscriber when owner is impersonating."""
    return st.session_state.viewing_as or st.session_state.user

def is_owner_session() -> bool:
    """True if the logged-in user has the owner role."""
    u = st.session_state.user
    return bool(u and u.get("role") == "owner")

def is_impersonating() -> bool:
    return is_owner_session() and st.session_state.viewing_as is not None

def render_impersonation_banner():
    """Sticky amber banner shown when owner is viewing a subscriber account."""
    if not is_impersonating():
        return
    sub = st.session_state.viewing_as
    biz = sub.get("business_name") or sub.get("name", "Subscriber")
    st.markdown(f"""
    <div class="impersonate-bar">
      <div>👁 &nbsp;<strong>Owner View</strong> — You are viewing <strong>{biz}</strong>
        ({sub['email']}) as if you were this subscriber.</div>
    </div>
    """, unsafe_allow_html=True)
    col_exit = st.columns([5, 1])[1]
    with col_exit:
        if st.button("← Exit View", use_container_width=True):
            st.session_state.viewing_as = None
            go_to("admin")


def render_floating_agent():
    """Lex — context-aware floating AI robot agent (injected once per page)."""
    import streamlit.components.v1 as _components
    tok = st.session_state.get("session_token", "")
    s_param = f"&s={tok}" if tok else ""

    # HTML structure only — no <script> (Streamlit strips scripts from st.markdown)
    st.markdown(f"""
<div id="lex-widget">
  <div class="lex-orb-wrap" onclick="window.lexToggle&&window.lexToggle()">
    <div class="lex-ring2"></div>
    <div class="lex-ring"></div>
    <div class="lex-orb">🤖</div>
    <div class="lex-dot"></div>
  </div>
  <div class="lex-panel" id="lex-panel">
    <div class="lex-head">
      <div class="lex-head-av">🤖</div>
      <div>
        <div class="lex-head-title">Lex — AI Agent</div>
        <div class="lex-head-ctx" id="lex-ctx">Initialising...</div>
      </div>
      <button class="lex-x" onclick="window.lexToggle&&window.lexToggle()">✕</button>
    </div>
    <div class="lex-body" id="lex-body"></div>
    <div class="lex-footer">
      <input class="lex-inp" id="lex-inp" placeholder="Ask Lex anything..."
             onkeydown="if(event.key==='Enter')window.lexSend&&window.lexSend()" autocomplete="off" />
      <button class="lex-snd" onclick="window.lexSend&&window.lexSend()">➤</button>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # JavaScript injected via 0-height iframe so it actually executes.
    # All DOM access goes through window.parent since this runs inside an iframe.
    _components.html(f"""<script>
(function(){{
  const S = "{s_param}";
  const doc = window.parent.document;
  const win = window.parent;

  const PAGES = {{
    dashboard: {{ icon:"📊", name:"Dashboard",
      greeting:"I can see you're on the Dashboard! Here's what I'd focus on next:",
      tips:["Connect a social platform to start publishing","Your Ad Plan is ready — approve it to activate","Check Analytics to spot your top-performing content"],
      ctas:[["🎯 Build Ad Plan","adplan"],["✍️ Create a Post","compose"]] }},
    adplan: {{ icon:"🎯", name:"Ad Plan",
      greeting:"Working on your Ad Plan! Here's how to get the most out of it:",
      tips:["A 30-day plan gives you quick wins in week one","Allocate 60% budget to Instagram + Facebook first","Approve the plan to auto-schedule all content items"],
      ctas:[["🤖 Chat with AI Strategist","chat"]] }},
    chat: {{ icon:"🤖", name:"AI Chat",
      greeting:"The AI Chat is open! Here are some power prompts to try:",
      tips:["Write 5 Instagram captions for [your product]","Analyse my top 3 competitors in [industry]","Create a 2-week content calendar for [platform]"],
      ctas:[["✍️ Create Post from Idea","compose"],["🎯 Jump to Ad Plan","adplan"]] }},
    compose: {{ icon:"✍️", name:"Create Post",
      greeting:"Creating a post! Quick tips to maximise reach:",
      tips:["Best posting time: Tue-Thu 9am-11am local time","Add 3-5 niche hashtags for 3x more reach","Video posts get 48% more engagement than images"],
      ctas:[["🤖 Get AI Writing Help","chat"]] }},
    posts: {{ icon:"📋", name:"My Posts",
      greeting:"Reviewing your posts! Here's what to check:",
      tips:["Drafts over 3 days old: publish or delete them","Repurpose top posts across other platforms","Schedule 3+ posts/week for consistent algorithm growth"],
      ctas:[["✍️ Create New Post","compose"]] }},
    analytics: {{ icon:"📈", name:"Analytics",
      greeting:"Looking at Analytics! Key insight principles:",
      tips:["Compare week-over-week to catch trend shifts early","Your top platform likely drives 70%+ of engagement","Posting frequency is the #1 predictor of growth"],
      ctas:[["🎯 Plan More Content","adplan"]] }},
    platforms: {{ icon:"🔗", name:"Platforms",
      greeting:"Managing Platforms! Connection priority guide:",
      tips:["Instagram first — highest organic ROI for most businesses","Facebook + Instagram share one Meta API connection","LinkedIn is best for B2B and professional services"],
      ctas:[["📊 Back to Dashboard","dashboard"]] }},
    settings: {{ icon:"⚙️", name:"Settings",
      greeting:"In Settings! A few things worth checking:",
      tips:["Claude Sonnet 4.6 is the best value AI model","Add your ANTHROPIC_API_KEY to unlock full AI features","Set OWNER_EMAIL in .env to get the admin dashboard"],
      ctas:[["📊 Back to Dashboard","dashboard"]] }},
    onboarding: {{ icon:"🚀", name:"Onboarding",
      greeting:"Welcome! I'm Lex, your AI marketing agent. Let me help you get started:",
      tips:["The more detail you give, the better your ad plan will be","Tell me about your target audience and monthly budget","You can update your business profile any time in Settings"],
      ctas:[] }},
    admin: {{ icon:"👑", name:"Owner Dashboard",
      greeting:"Owner Dashboard — here's how to read the health signals:",
      tips:["Health < 20 = subscriber at risk, consider outreach","Click 'View Account' to impersonate and diagnose issues","Sort by 'Dormant' to find churn risks early"],
      ctas:[] }}
  }};

  const SMART = {{
    post:["Best post lengths: Instagram 138-150 chars, LinkedIn 1,300 chars, Twitter 71-100 chars.",
          "Video content gets 3x more engagement than static images on every platform.",
          "Hashtag sweet spots: 3-5 on LinkedIn, 5-10 on Instagram, 1-2 on Twitter/X."],
    plan:["A strong 30-day plan: Week 1-2 awareness, Week 3 engagement, Week 4 conversion.",
          "Allocate ~60% of social budget to paid ads, 40% to organic content creation.",
          "Start with 2-3 platforms max — spreading too thin reduces impact by 40%."],
    budget:["Facebook/Instagram CPM averages $7-12. LinkedIn CPM averages $35-55.",
            "For a $500/month budget, Facebook Ads typically outperforms Google Ads for B2C.",
            "Retargeting audiences convert 10x better than cold traffic — always set up your pixel first."],
    help:["I'm Lex — I know your current page and give context-specific tips.",
          "For deeper analysis with your full business profile, use the AI Chat tab.",
          "Ask me about posting strategy, ad budgets, content ideas, or platform best practices."],
    default:["Great question! For the most detailed answer, the AI Chat has your full business context. <a href='?tab=chat{s_param}' target='_top' style='color:#A78BFA;font-weight:700;text-decoration:none;'>Open AI Chat</a>",
             "That's worth exploring in depth — try asking in the AI Chat where I have all your business context. <a href='?tab=chat{s_param}' target='_top' style='color:#A78BFA;font-weight:700;text-decoration:none;'>Go to Chat</a>",
             "Good question! I can give a quick tip here, or the AI Chat gives a full personalised answer. <a href='?tab=chat{s_param}' target='_top' style='color:#A78BFA;font-weight:700;text-decoration:none;'>Open Chat</a>"]
  }};

  function getTab() {{
    return new URLSearchParams(win.location.search).get('tab') || 'dashboard';
  }}
  function buildLink(tab) {{
    return '?tab=' + tab + S;
  }}
  function rand(arr) {{ return arr[Math.floor(Math.random()*arr.length)]; }}

  let open = false, loaded = false;

  function lexToggle() {{
    open = !open;
    const panel = doc.getElementById('lex-panel');
    if (!panel) return;
    if (open) {{
      panel.classList.add('open');
      const dot = doc.getElementById('lex-dot');
      if (dot) dot.style.display = 'none';
      if (!loaded) {{ lexLoad(); loaded = true; }}
      setTimeout(()=>{{ const inp=doc.getElementById('lex-inp'); if(inp) inp.focus(); }}, 350);
    }} else {{
      panel.classList.remove('open');
    }}
  }}
  win.lexToggle = lexToggle;

  function lexLoad() {{
    const tab = getTab();
    const ctx = PAGES[tab] || PAGES.dashboard;
    const ctxEl = doc.getElementById('lex-ctx');
    if (ctxEl) ctxEl.textContent = ctx.icon + ' ' + ctx.name;
    const body = doc.getElementById('lex-body');
    if (!body) return;
    body.innerHTML = '';
    addAI(ctx.greeting);
    const tipsWrap = doc.createElement('div');
    tipsWrap.style.cssText = 'display:flex;flex-direction:column;gap:3px;padding:2px 0;';
    tipsWrap.innerHTML = '<div style="font-size:10px;color:#475569;margin-bottom:2px;">Tips for this page:</div>' +
      ctx.tips.map(t=>'<span class="lex-tip">'+t+'</span>').join('');
    body.appendChild(tipsWrap);
    (ctx.ctas||[]).forEach(function(pair){{
      const label=pair[0], ctaTab=pair[1];
      const a = doc.createElement('a');
      a.className='lex-cta'; a.textContent=label;
      a.href=buildLink(ctaTab); a.target='_top';
      body.appendChild(a);
    }});
    body.scrollTop = body.scrollHeight;
  }}

  function addAI(html) {{
    const body = doc.getElementById('lex-body');
    if (!body) return;
    const d = doc.createElement('div'); d.className='lx-ai';
    d.innerHTML='<div class="lx-av" style="background:linear-gradient(135deg,#7C3AED,#0EA5E9);">🤖</div><div class="lx-bai">'+html+'</div>';
    body.appendChild(d); body.scrollTop=body.scrollHeight;
  }}
  function addUser(text) {{
    const body = doc.getElementById('lex-body');
    if (!body) return;
    const d = doc.createElement('div'); d.className='lx-usr';
    d.innerHTML='<div class="lx-av" style="background:rgba(6,182,212,0.2);border:1px solid rgba(6,182,212,0.3);">👤</div><div class="lx-busr">'+text+'</div>';
    body.appendChild(d); body.scrollTop=body.scrollHeight;
  }}
  function showTyping() {{
    const body = doc.getElementById('lex-body');
    if (!body) return;
    const d = doc.createElement('div'); d.className='lx-ai'; d.id='lex-typing-el';
    d.innerHTML='<div class="lx-av" style="background:linear-gradient(135deg,#7C3AED,#0EA5E9);">🤖</div><div class="lx-bai"><div class="lex-typing"><span></span><span></span><span></span></div></div>';
    body.appendChild(d); body.scrollTop=body.scrollHeight;
  }}
  function removeTyping() {{
    const el = doc.getElementById('lex-typing-el'); if (el) el.remove();
  }}

  function getReply(q) {{
    const lq = q.toLowerCase();
    if (/post|caption|content|copy|write|instagram|linkedin|twitter|facebook/.test(lq)) return rand(SMART.post);
    if (/plan|campaign|strategy|goal|kpi|objective/.test(lq)) return rand(SMART.plan);
    if (/budget|cost|price|spend|money|cpm|cpc|roi/.test(lq)) return rand(SMART.budget);
    if (/help|who|what can|how do/.test(lq)) return rand(SMART.help);
    return rand(SMART.default);
  }}

  function lexSend() {{
    const inp = doc.getElementById('lex-inp');
    if (!inp) return;
    const txt = inp.value.trim(); if (!txt) return;
    inp.value=''; addUser(txt); showTyping();
    setTimeout(function(){{ removeTyping(); addAI(getReply(txt)); }}, 850+Math.random()*500);
  }}
  win.lexSend = lexSend;

  // Attach click events via JS (Streamlit strips inline onclick attributes)
  function attachLexEvents() {{
    const orb = doc.querySelector('.lex-orb-wrap');
    const closeBtn = doc.querySelector('.lex-x');
    const sendBtn  = doc.querySelector('.lex-snd');
    const inp      = doc.getElementById('lex-inp');
    if (orb && !orb._lexBound) {{
      orb.addEventListener('click', lexToggle);
      orb._lexBound = true;
    }}
    if (closeBtn && !closeBtn._lexBound) {{
      closeBtn.addEventListener('click', lexToggle);
      closeBtn._lexBound = true;
    }}
    if (sendBtn && !sendBtn._lexBound) {{
      sendBtn.addEventListener('click', lexSend);
      sendBtn._lexBound = true;
    }}
    if (inp && !inp._lexBound) {{
      inp.addEventListener('keydown', function(e){{ if(e.key==='Enter') lexSend(); }});
      inp._lexBound = true;
    }}
  }}
  // Keep trying until elements are in DOM
  const bindTimer = setInterval(function(){{
    if (doc.querySelector('.lex-orb-wrap')) {{ attachLexEvents(); clearInterval(bindTimer); }}
  }}, 100);

  // Profile dropdown — click to open, click outside to close
  const menuTimer = setInterval(function(){{
    const menu = doc.querySelector('.sa-user-menu');
    if (menu && !menu._ddBound) {{
      menu._ddBound = true;
      menu.addEventListener('click', function(e){{
        e.stopPropagation();
        const dd = menu.querySelector('.sa-dropdown');
        if (dd) dd.classList.toggle('open');
      }});
      doc.addEventListener('click', function(){{
        doc.querySelectorAll('.sa-dropdown.open').forEach(function(dd){{ dd.classList.remove('open'); }});
      }});
      clearInterval(menuTimer);
    }}
  }}, 100);

  // Watch for tab changes and update context label
  let lastHref = win.location.href;
  setInterval(function(){{
    if (win.location.href !== lastHref) {{
      lastHref = win.location.href; loaded = false;
      const tab = getTab(); const ctx = PAGES[tab] || PAGES.dashboard;
      const ctxEl = doc.getElementById('lex-ctx');
      if (ctxEl) ctxEl.textContent = ctx.icon + ' ' + ctx.name;
      if (open) {{ lexLoad(); loaded = true; }}
    }}
  }}, 400);

  // 3D mouse-tilt on metric/channel cards
  doc.addEventListener('mousemove', function(e){{
    doc.querySelectorAll('.metric-box,.channel-card,.sub-card').forEach(function(el){{
      const r = el.getBoundingClientRect();
      if (e.clientX>=r.left && e.clientX<=r.right && e.clientY>=r.top && e.clientY<=r.bottom) {{
        const cx=r.left+r.width/2, cy=r.top+r.height/2;
        const dx=(e.clientX-cx)/(r.width/2), dy=(e.clientY-cy)/(r.height/2);
        el.style.transform='perspective(700px) rotateX('+(-dy*4)+'deg) rotateY('+(dx*4)+'deg) translateZ(8px)';
      }} else {{
        el.style.transform='';
      }}
    }});
  }});

}})();
</script>""", height=0)


# ══════════════════════════════════════════════════════════════════════════════
# AUTH PAGES
# ══════════════════════════════════════════════════════════════════════════════
def render_auth():
    mode = st.query_params.get("auth", "login")

    col = st.columns([1, 2, 1])[1]

    with col:
        st.markdown(f"""
        <div class="auth-wrap">
          <div class="auth-logo">⚡</div>
          <div class="auth-title">AdFlow AI</div>
          <div class="auth-sub">Your AI-powered ad growth platform</div>
        </div>
        """, unsafe_allow_html=True)

        if mode == "register":
            st.markdown("### Create your account")
            name  = st.text_input("Your name", placeholder="Jane Smith")
            biz   = st.text_input("Business name (optional)", placeholder="My Awesome Business")
            email = st.text_input("Email address", placeholder="jane@example.com")
            pw    = st.text_input("Password", type="password", placeholder="Minimum 8 characters")
            pw2   = st.text_input("Confirm password", type="password")

            if st.button("Create account — it's free", type="primary", use_container_width=True):
                if not all([name, email, pw]):
                    st.error("Please fill in all required fields.")
                elif pw != pw2:
                    st.error("Passwords don't match.")
                elif len(pw) < 8:
                    st.error("Password must be at least 8 characters.")
                elif db.get_user_by_email(email):
                    st.error("An account with this email already exists.")
                else:
                    try:
                        user = db.create_user(email, pw, name, biz)
                        _do_login(user)
                    except Exception as e:
                        st.error(f"Registration failed: {e}")

            st.markdown("Already have an account? [Sign in](?auth=login)")

        else:  # login
            st.markdown("### Sign in to your account")
            email = st.text_input("Email address", placeholder="jane@example.com")
            pw    = st.text_input("Password", type="password")

            if st.button("Sign in", type="primary", use_container_width=True):
                if not email or not pw:
                    st.error("Please enter your email and password.")
                else:
                    user = db.verify_password(email, pw)
                    if user:
                        _do_login(user)
                    else:
                        st.error("Incorrect email or password.")

            st.markdown("New to AdFlow AI? [Create a free account](?auth=register)")

            # Demo login shortcut (remove in production)
            st.markdown("---")
            if st.button("🎮  Try Demo Account", use_container_width=True):
                demo = db.get_user_by_email("demo@socialai.app")
                if not demo:
                    demo = db.create_user("demo@socialai.app", "demo1234", "Demo User", "Demo Business")
                _do_login(demo)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def render_topbar():
    user  = st.session_state.user
    tier  = get_tier()
    tab   = get_tab()
    conns = get_connections()
    tok   = st.session_state.get("session_token", "")
    s_param = f"&s={tok}" if tok else ""

    n_platforms = len(conns)
    tier_badge  = tier.name.upper()

    # Get user initials for avatar
    name_parts = user.get("name", "U").split()
    initials = (name_parts[0][0] + (name_parts[-1][0] if len(name_parts) > 1 else "")).upper()

    _viewing = st.session_state.get("viewing_as")
    _is_owner = is_owner_session()
    NAV = []
    if _is_owner and not _viewing:
        NAV.append(("admin", "⬡ Owner"))
    NAV += [
        ("dashboard", "Dashboard"),
        ("adplan",    "🎯 Ad Plan"),
        ("chat",      "🤖 AI Chat"),
        ("compose",   "Create Post"),
        ("posts",     "My Posts"),
        ("analytics", "Analytics"),
        ("platforms", "Platforms"),
        ("settings",  "Settings"),
    ]

    nav_links = ""
    for key, label in NAV:
        cls = "sa-nav-active" if tab == key else ""
        nav_links += f'<a href="?tab={key}{s_param}" class="{cls}" target="_self">{label}</a>'

    logo_svg = """<svg class="sa-logo-svg" width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="lg1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#A78BFA"/>
          <stop offset="100%" stop-color="#06B6D4"/>
        </linearGradient>
        <linearGradient id="lg2" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stop-color="#7C3AED"/>
          <stop offset="100%" stop-color="#06B6D4"/>
        </linearGradient>
      </defs>
      <!-- Rounded square background -->
      <rect x="2" y="2" width="32" height="32" rx="9" fill="url(#lg2)" opacity="0.18"/>
      <rect x="2" y="2" width="32" height="32" rx="9" fill="none" stroke="url(#lg1)" stroke-width="1.5" opacity="0.7"/>
      <!-- Flowing upward growth wave -->
      <path d="M7,26 Q11,24 13,20 Q15,16 18,15 Q21,14 23,11" stroke="url(#lg1)" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      <!-- Arrow head pointing up-right -->
      <path d="M20,9 L23,11 L21,14" stroke="url(#lg1)" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      <!-- AI spark dot -->
      <circle cx="18" cy="15" r="2.2" fill="url(#lg1)" opacity="0.9"/>
      <!-- Small pulse rings -->
      <circle cx="18" cy="15" r="4.5" stroke="url(#lg1)" stroke-width="0.8" fill="none" opacity="0.35"/>
    </svg>"""

    st.markdown(f"""
    <div class="sa-topbar">
      <div class="sa-header">
        <a href="?tab=dashboard{s_param}" class="sa-logo-wrap" target="_self">
          {logo_svg}
          <div>
            <div class="sa-logo-name">AdFlow AI</div>
            <div class="sa-logo-tagline">AI-POWERED AD GROWTH PLATFORM</div>
          </div>
        </a>
        <div class="sa-header-right">
          <div class="sa-stat-pill">⬡ {n_platforms} platform{"s" if n_platforms != 1 else ""}</div>
          <div class="sa-tier-pill">{tier_badge}</div>
          <div class="sa-user-menu">
            <div class="sa-avatar">{initials}</div>
            <div>
              <div class="sa-user-name-text">{user['name']}</div>
            </div>
            <div class="sa-user-chevron">▾</div>
            <div class="sa-dropdown">
              <a class="sa-dd-item" href="?tab=settings{s_param}" target="_self">👤 &nbsp;Profile</a>
              <a class="sa-dd-item" href="?tab=settings&section=subscription{s_param}" target="_self">💳 &nbsp;Subscription</a>
              <a class="sa-dd-item" href="?tab=settings{s_param}" target="_self">⚙️ &nbsp;Settings</a>
              <div class="sa-dd-divider"></div>
              <a class="sa-dd-item sa-dd-logout" href="?action=logout" target="_self">🚪 &nbsp;Sign out</a>
            </div>
          </div>
        </div>
      </div>
      <div class="sa-nav"><div class="sa-nav-island">{nav_links}</div></div>
    </div>
    """, unsafe_allow_html=True)


# ── DASHBOARD ──────────────────────────────────────────────────────────────────
def render_dashboard():
    user  = st.session_state.user
    uid   = user["id"]
    conns = get_connections()
    tier  = get_tier()

    st.markdown('<div class="page-title">👋 Welcome back!</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">{user["name"]} · {user.get("business_name","") or "Your Business"}</div>', unsafe_allow_html=True)

    # ── Quick stats ──
    try:
        from saas.analytics import get_top_posts
        summary = db.get_analytics_summary(uid, days=30)
        posts_30d = len(db.get_posts(uid, status="published", limit=200))
        scheduled = len(db.get_posts(uid, status="scheduled"))
    except Exception:
        summary = {}; posts_30d = 0; scheduled = 0

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-box">
            <div class="metric-val">{len(conns)}</div>
            <div class="metric-lbl">Platforms Connected</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{posts_30d}</div>
            <div class="metric-lbl">Posts This Month</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{scheduled}</div>
            <div class="metric-lbl">Scheduled</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{int(summary.get("total_reach", 0)):,}</div>
            <div class="metric-lbl">Total Reach (30d)</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{int(summary.get("total_likes", 0) + summary.get("total_comments", 0) + summary.get("total_shares", 0)):,}</div>
            <div class="metric-lbl">Engagements (30d)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Platform status ──
    st.markdown('<div class="sec-title">🔗 Your Platforms</div>', unsafe_allow_html=True)
    connected_ids = {c["platform"]: c for c in conns}
    tier_platforms = tier.platforms

    cols = st.columns(5, gap="medium")
    for i, (pid, pdef) in enumerate(PLATFORMS.items()):
        with cols[i % 5]:
            is_connected = pid in connected_ids
            is_locked    = pid not in tier_platforms

            status_color = "#22C55E" if is_connected else ("#94A3B8" if not is_locked else "#EF4444")
            status_text  = ("✅ Connected" if is_connected
                            else ("🔒 Upgrade" if is_locked else "➕ Connect"))
            tile_class   = ("plat-tile plat-tile-connected" if is_connected
                            else ("plat-tile plat-tile-locked" if is_locked else "plat-tile"))

            st.markdown(f"""
            <div class="{tile_class}" style="border-top-color:{pdef.color}">
                <div class="plat-icon">{pdef.icon}</div>
                <div class="plat-name">{pdef.name}</div>
                <div class="plat-status" style="color:{status_color};">{status_text}</div>
            </div>
            """, unsafe_allow_html=True)
            if not is_connected and not is_locked:
                if st.button(f"Connect", key=f"conn_{pid}", use_container_width=True, type="primary"):
                    st.query_params["tab"] = "platforms"
                    st.query_params["connect"] = pid
                    st.rerun()

    # ── Quick action tiles ──
    st.markdown("")
    st.markdown('<div class="sec-title">⚡ Quick Actions</div>', unsafe_allow_html=True)

    qa1, qa2, qa3, qa4 = st.columns(4, gap="medium")
    with qa1:
        st.markdown('<div class="card"><div class="card-title">✍️ Create Post</div><div class="card-sub">Draft, generate images, schedule</div></div>', unsafe_allow_html=True)
        if st.button("Create Post →", key="qa_compose", use_container_width=True, type="primary"):
            go_to("compose")
    with qa2:
        st.markdown('<div class="card"><div class="card-title">📊 View Analytics</div><div class="card-sub">Performance across all platforms</div></div>', unsafe_allow_html=True)
        if st.button("View Analytics →", key="qa_analytics", use_container_width=True, type="primary"):
            go_to("analytics")
    with qa3:
        st.markdown('<div class="card"><div class="card-title">🧠 AI Strategy</div><div class="card-sub">Get AI-powered recommendations</div></div>', unsafe_allow_html=True)
        if st.button("Get Strategy →", key="qa_strategy", use_container_width=True, type="primary"):
            go_to("strategy")
    with qa4:
        st.markdown('<div class="card"><div class="card-title">🔗 Add Platform</div><div class="card-sub">Connect more social channels</div></div>', unsafe_allow_html=True)
        if st.button("Add Platform →", key="qa_platforms", use_container_width=True, type="primary"):
            go_to("platforms")

    # ── Recent posts ──
    st.markdown('<div class="sec-title">📋 Recent Posts</div>', unsafe_allow_html=True)
    recent = db.get_posts(uid, limit=5)
    if recent:
        for post in recent:
            icon   = platform_icon(post["platform"])
            status = post["status"]
            sc     = {"published":"#22C55E","scheduled":"#F59E0B","draft":"#94A3B8","failed":"#EF4444"}.get(status,"#94A3B8")
            st.markdown(f"""
            <div class="post-card post-status-{status}">
                <div style="display:flex;justify-content:space-between;align-items:start;">
                    <div>
                        <span style="font-weight:700;color:#E2E8F0;">{icon} {post['platform'].title()}</span>
                        <span style="font-size:11px;color:{sc};margin-left:10px;font-weight:700;">{status.upper()}</span>
                    </div>
                    <span style="font-size:11px;color:#94A3B8;">{(post.get('published_at') or post.get('scheduled_at') or post['created_at'])[:10]}</span>
                </div>
                <div style="font-size:13px;color:#94A3B8;margin-top:6px;line-height:1.5;">{post['content'][:180]}{"…" if len(post['content'])>180 else ""}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No posts yet. Create your first post to get started!")


# ── PLATFORMS PAGE ─────────────────────────────────────────────────────────────
def render_platforms():
    uid  = st.session_state.user["id"]
    tier = get_tier()
    conns = get_connections()
    connected_map = {c["platform"]: c for c in conns}
    is_admin = is_owner_session()

    # Handle OAuth callbacks before any rendering
    code = st.query_params.get("code")
    cb   = st.query_params.get("oauth_callback")
    if code and cb:
        _handle_oauth_callback(uid, cb, code)
        return

    connected_count  = len(connected_map)
    total_available  = sum(1 for pid in PLATFORMS if pid in tier.platforms)

    st.markdown('<div class="page-title">🔗 Connect Your Platforms</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="page-sub">{connected_count} of {total_available} platforms connected — '
        f'one-click OAuth, we handle the rest automatically.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("""<style>
    .plat-card {
      background:rgba(15,23,42,0.75); border:1px solid rgba(124,58,237,0.2);
      border-radius:18px; padding:24px 18px 18px; text-align:center; transition:all 0.25s;
    }
    .plat-card:hover { border-color:rgba(124,58,237,0.5); box-shadow:0 8px 32px rgba(124,58,237,0.15); transform:translateY(-3px); }
    .plat-card-connected { border-color:rgba(34,197,94,0.4) !important; background:rgba(34,197,94,0.05) !important; }
    .plat-card-locked { opacity:0.55; }
    .plat-icon-big { font-size:40px; margin-bottom:10px; }
    .plat-name-big { font-size:16px; font-weight:800; color:#E2E8F0; margin-bottom:8px; }
    .plat-badge {
      display:inline-block; padding:3px 12px; border-radius:20px;
      font-size:11px; font-weight:700; margin-bottom:14px;
    }
    .pbadge-ok   { background:rgba(34,197,94,0.12); color:#22C55E; border:1px solid rgba(34,197,94,0.3); }
    .pbadge-off  { background:rgba(148,163,184,0.08); color:#94A3B8; border:1px solid rgba(148,163,184,0.2); }
    .pbadge-lock { background:rgba(124,58,237,0.1); color:#a78bfa; border:1px solid rgba(124,58,237,0.25); }
    .plat-acct   { font-size:12px; color:#64748B; margin-bottom:10px; }
    .plat-oauth-btn {
      display:block; color:white; padding:10px 0; border-radius:10px;
      font-weight:700; font-size:13px; text-decoration:none;
      text-align:center; margin-top:6px; transition:opacity 0.2s;
    }
    .plat-oauth-btn:hover { opacity:0.85; }
    </style>""", unsafe_allow_html=True)

    platforms_order = [
        ["instagram", "facebook"],
        ["linkedin", "tiktok", "twitter"],
    ]

    for group in platforms_order:
        cols = st.columns(len(group), gap="medium")
        for col_i, pid in enumerate(group):
            pdef = PLATFORMS.get(pid)
            if not pdef:
                continue
            is_connected = pid in connected_map
            is_locked    = pid not in tier.platforms
            conn = connected_map.get(pid, {})
            acct = conn.get("username") or conn.get("page_name") or ""

            badge_cls = "pbadge-ok" if is_connected else ("pbadge-lock" if is_locked else "pbadge-off")
            badge_txt = "✅ Connected" if is_connected else ("🔒 Upgrade" if is_locked else "Not connected")
            card_cls  = "plat-card-connected" if is_connected else ("plat-card-locked" if is_locked else "")

            with cols[col_i]:
                st.markdown(f"""
                <div class="plat-card {card_cls}">
                  <div class="plat-icon-big">{pdef.icon}</div>
                  <div class="plat-name-big">{pdef.name}</div>
                  <span class="plat-badge {badge_cls}">{badge_txt}</span>
                  {f'<div class="plat-acct">@{acct}</div>' if acct else ''}
                </div>
                """, unsafe_allow_html=True)

                if is_connected:
                    if conn.get("connected_at"):
                        st.caption(f"Since {conn['connected_at'][:10]}")
                    if st.button(f"Disconnect", key=f"disc_{pid}",
                                 type="secondary", use_container_width=True):
                        db.disconnect_platform(uid, pid)
                        st.rerun()

                elif is_locked:
                    needed = next((t.name for t in TIERS.values() if pid in t.platforms), "Agency")
                    st.caption(f"Available on {needed} plan")
                    if st.button("Upgrade Plan", key=f"upg_{pid}",
                                 type="primary", use_container_width=True):
                        go_to("settings")

                else:
                    _render_platform_connect(uid, pid, pdef, is_admin)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if connected_count > 0:
        st.markdown("""
        <div style="background:rgba(34,197,94,0.05);border:1px solid rgba(34,197,94,0.2);
                    border-radius:12px;padding:16px 20px;margin-top:16px;">
          <div style="font-size:13px;font-weight:700;color:#22C55E;margin-bottom:4px;">🚀 You're connected!</div>
          <div style="font-size:12px;color:#94A3B8;">
            Head to <strong>Create Post</strong> to publish content, or <strong>Ad Plan</strong>
            to build your marketing strategy.
          </div>
        </div>
        """, unsafe_allow_html=True)


def _handle_oauth_callback(uid, cb, code):
    with st.spinner("Connecting your account…"):
        try:
            if cb == "meta":
                _process_meta_callback(uid, code)
            elif cb == "linkedin":
                _process_linkedin_callback(uid, code)
            elif cb == "tiktok":
                _process_tiktok_callback(uid, code)
            elif cb == "twitter":
                _process_twitter_callback(uid, code)
            else:
                st.error(f"Unknown OAuth provider: {cb}")
        except Exception as e:
            st.error(f"Connection failed: {e}")
            if st.button("← Back to Platforms"):
                st.query_params.clear()
                st.query_params["tab"] = "platforms"
                st.rerun()


def _process_meta_callback(uid, code):
    redirect_uri = f"{_base_url()}/?tab=platforms&oauth_callback=meta"
    from saas.platforms.meta import MetaAPI
    tokens       = MetaAPI.exchange_code(code, redirect_uri)
    access_token = tokens["access_token"]
    api          = MetaAPI(access_token=access_token)
    pages        = api.get_pages()
    if not pages:
        st.error("No Facebook Pages found. Make sure you manage a Facebook Page, then try again.")
        if st.button("← Back"):
            st.query_params.clear(); st.query_params["tab"] = "platforms"; st.rerun()
        return
    page        = pages[0]
    page_token  = page["access_token"]
    ig          = api.get_instagram_account(page["id"], page_token)
    extra       = {"pages": pages, "page_token": page_token}
    if ig:
        extra["ig_user_id"]  = ig["id"]
        extra["ig_username"] = ig.get("username")
    db.upsert_platform_connection(
        uid, "facebook",
        access_token=access_token, page_id=page["id"],
        page_name=page["name"], username=page["name"],
        extra_data=json.dumps(extra),
    )
    if ig:
        db.upsert_platform_connection(
            uid, "instagram",
            access_token=access_token,
            page_id=ig["id"], page_name=ig.get("username"),
            username=ig.get("username"),
            extra_data=json.dumps({**extra, "page_id": page["id"]}),
        )
    st.query_params.clear(); st.query_params["tab"] = "platforms"
    msg = f"✅ Facebook connected as **{page['name']}**"
    if ig:
        msg += f"  \n✅ Instagram connected as **@{ig.get('username','')}**"
    st.success(msg)
    st.rerun()


def _process_linkedin_callback(uid, code):
    redirect_uri = f"{_base_url()}/?tab=platforms&oauth_callback=linkedin"
    from saas.platforms.linkedin_api import LinkedInAPI
    tokens  = LinkedInAPI.exchange_code(code, redirect_uri)
    api     = LinkedInAPI(access_token=tokens["access_token"])
    profile = api.get_profile()
    name    = f"{profile.get('localizedFirstName','')} {profile.get('localizedLastName','')}".strip()
    person_urn = f"urn:li:person:{profile['id']}"
    orgs    = api.get_organizations()
    org_urn = None
    if orgs:
        org     = orgs[0].get("organizationalTarget~", {})
        org_urn = f"urn:li:organization:{org.get('id','')}"
    db.upsert_platform_connection(
        uid, "linkedin",
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        username=name, page_name=name,
        extra_data=json.dumps({"person_urn": person_urn, "org_urn": org_urn}),
    )
    st.query_params.clear(); st.query_params["tab"] = "platforms"
    st.success(f"✅ LinkedIn connected as **{name}**")
    st.rerun()


def _process_tiktok_callback(uid, code):
    redirect_uri   = f"{_base_url()}/?tab=platforms&oauth_callback=tiktok"
    from saas.platforms.tiktok_api import TikTokAPI
    verifier_saved = st.session_state.get("tiktok_pkce", "")
    tokens = TikTokAPI.exchange_code(code, redirect_uri, verifier_saved)
    api    = TikTokAPI(access_token=tokens["access_token"], open_id=tokens.get("open_id"))
    info   = api.get_user_info()
    db.upsert_platform_connection(
        uid, "tiktok",
        access_token=tokens["access_token"], refresh_token=tokens.get("refresh_token"),
        username=info.get("display_name"), page_name=info.get("display_name"),
        extra_data=json.dumps({"open_id": tokens.get("open_id")}),
    )
    st.query_params.clear(); st.query_params["tab"] = "platforms"
    st.success(f"✅ TikTok connected as **{info.get('display_name','')}**")
    st.rerun()


def _process_twitter_callback(uid, code):
    redirect_uri = f"{_base_url()}/?tab=platforms&oauth_callback=twitter"
    from saas.platforms.twitter_api import TwitterAPI
    verifier = st.session_state.get("twitter_pkce", "")
    tokens   = TwitterAPI.exchange_code(code, redirect_uri, verifier)
    api      = TwitterAPI(access_token=tokens["access_token"])
    me       = api.get_me()
    db.upsert_platform_connection(
        uid, "twitter",
        access_token=tokens["access_token"], refresh_token=tokens.get("refresh_token"),
        username=me.get("username"), page_name=me.get("name"),
        extra_data=json.dumps({"twitter_user_id": me.get("id")}),
    )
    st.query_params.clear(); st.query_params["tab"] = "platforms"
    st.success(f"✅ Twitter / X connected as **@{me.get('username','')}**")
    st.rerun()


def _render_platform_connect(uid, pid, pdef, is_admin):
    """Render the OAuth connect button (or admin setup guide) for a platform."""
    # Pass session token as OAuth state so the new-tab callback can re-auth
    state_tok = st.session_state.get("session_token") or ""
    if pid in ("facebook", "instagram"):
        app_id  = os.environ.get("META_APP_ID", "")
        app_sec = os.environ.get("META_APP_SECRET", "")
        if not app_id or not app_sec:
            if is_admin:
                with st.expander("⚙️ Setup required"):
                    _meta_uri = f"{_base_url()}/?tab=platforms&oauth_callback=meta"
                    st.markdown(f"""**Enable Meta (Facebook + Instagram):**
1. Go to [developers.facebook.com](https://developers.facebook.com) → Create App → Business
2. Add **Facebook Login** + **Instagram Basic Display**
3. Set redirect URI: `{_meta_uri}`
4. Add `META_APP_ID` and `META_APP_SECRET` to `.env`""")
            else:
                st.caption("Contact admin to enable this platform")
            return
        if pid == "instagram":
            st.caption("Connects automatically with Facebook")
        redirect_uri = f"{_base_url()}/?tab=platforms&oauth_callback=meta"
        from saas.platforms.meta import MetaAPI
        auth_url = MetaAPI.get_auth_url(redirect_uri, pdef.oauth_scope, state=state_tok)
        lbl = "Connect Facebook + Instagram" if pid == "facebook" else "Connect via Facebook"
        _oauth_button(f"{pdef.icon} {lbl}", auth_url, "#1877F2")

    elif pid == "linkedin":
        if not os.environ.get("LINKEDIN_CLIENT_ID"):
            if is_admin:
                with st.expander("⚙️ Setup required"):
                    _li_uri = f"{_base_url()}/?tab=platforms&oauth_callback=linkedin"
                    st.markdown(f"""**Enable LinkedIn:**
1. Go to [linkedin.com/developers](https://www.linkedin.com/developers/apps) → Create App
2. Add **Share on LinkedIn** + **Sign In with LinkedIn**
3. Set redirect URI: `{_li_uri}`
4. Add `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` to `.env`""")
            else:
                st.caption("Contact admin to enable this platform")
            return
        redirect_uri = f"{_base_url()}/?tab=platforms&oauth_callback=linkedin"
        from saas.platforms.linkedin_api import LinkedInAPI
        auth_url = LinkedInAPI.get_auth_url(redirect_uri, pdef.oauth_scope, state=state_tok)
        _oauth_button("💼 Connect LinkedIn", auth_url, "#0A66C2")

    elif pid == "tiktok":
        if not os.environ.get("TIKTOK_CLIENT_KEY"):
            if is_admin:
                with st.expander("⚙️ Setup required"):
                    _tt_uri = f"{_base_url()}/?tab=platforms&oauth_callback=tiktok"
                    st.markdown(f"""**Enable TikTok:**
1. Go to [developers.tiktok.com](https://developers.tiktok.com) → Create App
2. Add **Login Kit** + **Content Posting API**
3. Set redirect URI: `{_tt_uri}`
4. Add `TIKTOK_CLIENT_KEY` and `TIKTOK_CLIENT_SECRET` to `.env`""")
            else:
                st.caption("Contact admin to enable this platform")
            return
        import secrets as _sec, hashlib as _hl
        redirect_uri = f"{_base_url()}/?tab=platforms&oauth_callback=tiktok"
        verifier = _sec.token_urlsafe(43)
        st.session_state["tiktok_pkce"] = verifier
        from saas.platforms.tiktok_api import TikTokAPI
        auth_url = TikTokAPI.get_auth_url(redirect_uri, pdef.oauth_scope, state=state_tok)
        _oauth_button("🎵 Connect TikTok", auth_url, "#000000")

    elif pid == "twitter":
        if not os.environ.get("TWITTER_CLIENT_ID"):
            if is_admin:
                with st.expander("⚙️ Setup required"):
                    _tw_uri = f"{_base_url()}/?tab=platforms&oauth_callback=twitter"
                    st.markdown(f"""**Enable Twitter / X:**
1. Go to [developer.twitter.com](https://developer.twitter.com) → Create Project + App
2. Enable **OAuth 2.0** with PKCE
3. Set redirect URI: `{_tw_uri}`
4. Add `TWITTER_CLIENT_ID` and `TWITTER_CLIENT_SECRET` to `.env`""")
            else:
                st.caption("Contact admin to enable this platform")
            return
        redirect_uri = f"{_base_url()}/?tab=platforms&oauth_callback=twitter"
        from saas.platforms.twitter_api import TwitterAPI
        verifier, challenge = TwitterAPI.generate_pkce()
        st.session_state["twitter_pkce"] = verifier
        auth_url = TwitterAPI.get_auth_url(redirect_uri, pdef.oauth_scope, state_tok, challenge)
        _oauth_button("🐦 Connect Twitter / X", auth_url, "#1DA1F2")


# ── COMPOSE POST ───────────────────────────────────────────────────────────────
def render_compose():
    uid   = st.session_state.user["id"]
    user  = st.session_state.user
    tier  = get_tier()
    conns = get_connections()
    connected = [c["platform"] for c in conns]

    st.markdown('<div class="page-title">✍️ Create Post</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Write, AI-generate, add images — then publish or schedule.</div>', unsafe_allow_html=True)

    if not connected:
        st.warning("Connect at least one social platform first.")
        if st.button("Connect a platform →", type="primary"):
            go_to("platforms")
        return

    # Check post limit
    from saas.billing import can_create_post
    can, msg = can_create_post(uid)
    if not can:
        st.markdown(f"""
        <div class="upgrade-gate">
            <div style="font-size:28px">🚀</div>
            <div style="font-weight:700;font-size:16px;color:#7C3AED;margin:8px 0">{msg}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Upgrade Plan", type="primary"):
            go_to("settings")
        return

    # ── Step 1: Platform + Topic ──
    c1, c2 = st.columns([1.2, 2], gap="large")

    with c1:
        st.markdown('<div class="sec-title">1. Choose platform</div>', unsafe_allow_html=True)
        platform = st.selectbox("Platform", connected,
            format_func=lambda p: f"{platform_icon(p)} {p.title()}", label_visibility="collapsed")

        st.markdown('<div class="sec-title">2. Post topic</div>', unsafe_allow_html=True)
        topic = st.text_area("What is this post about?",
            placeholder="e.g. We just launched our new product, a sale announcement, team spotlight, industry tip…",
            height=100, label_visibility="collapsed")

        tone = st.selectbox("Tone", ["Professional", "Casual", "Friendly", "Exciting", "Educational"])
        include_hashtags = st.checkbox("Include hashtags", value=True)

        ai_gen_clicked = st.button("🤖 Generate AI Post Drafts", type="primary", use_container_width=True, key="ai_gen")

    with c2:
        st.markdown('<div class="sec-title">3. Post content</div>', unsafe_allow_html=True)

        # AI generation
        if ai_gen_clicked and topic:
            with st.spinner(f"Writing {3} post variations for {platform.title()}..."):
                try:
                    from saas.ai_writer import generate_post
                    drafts = generate_post(
                        topic=topic, platform=platform,
                        business_name=user.get("business_name",""),
                        tone=tone.lower(),
                        include_hashtags=include_hashtags,
                        count=3,
                    )
                    st.session_state.draft_content[platform] = drafts
                    db.track_usage(uid, "ai_request")
                except Exception as e:
                    st.error(f"AI generation failed: {e}")

        drafts = st.session_state.draft_content.get(platform, [])
        if drafts:
            st.markdown("**Pick a draft or edit below:**")
            for i, draft in enumerate(drafts):
                if st.button(f"Use Draft {i+1}", key=f"use_draft_{i}"):
                    st.session_state.post_draft = draft
                    st.rerun()
                st.text_area(f"Draft {i+1}", value=draft, height=120, key=f"draft_view_{i}",
                             label_visibility="collapsed")

        post_text = st.text_area(
            "Your post",
            value=st.session_state.get("post_draft", ""),
            height=180,
            placeholder="Write your post here, or generate AI drafts above…",
            key="final_post_text",
        )
        char_count = len(post_text)
        limits = {"twitter": 280, "facebook": 63206, "instagram": 2200, "linkedin": 3000, "tiktok": 150}
        limit  = limits.get(platform, 3000)
        color  = "#EF4444" if char_count > limit else "#94A3B8"
        st.markdown(f'<div style="text-align:right;font-size:11px;color:{color};">{char_count}/{limit}</div>', unsafe_allow_html=True)

    # ── Step 4: Image ──
    st.markdown('<div class="sec-title">4. Image (optional)</div>', unsafe_allow_html=True)
    img_col1, img_col2 = st.columns(2, gap="large")

    image_url_final = None

    with img_col1:
        st.markdown("**Upload your own image**")
        uploaded = st.file_uploader("", type=["jpg","jpeg","png","webp"], label_visibility="collapsed")
        if uploaded:
            st.image(uploaded, caption="Your image", use_column_width=True)
            # Save to temp and create data URL
            img_bytes = uploaded.getbuffer()
            b64 = base64.b64encode(img_bytes).decode()
            image_url_final = f"data:{uploaded.type};base64,{b64}"

    with img_col2:
        from saas.billing import can_generate_image
        can_img, img_msg = can_generate_image(uid)

        if not can_img:
            st.markdown(f"""
            <div class="upgrade-gate" style="padding:20px;">
                <div style="font-size:22px">🎨</div>
                <div style="font-weight:700;color:#7C3AED;">{img_msg}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            from saas.billing import images_used_this_month
            used_imgs, img_limit = images_used_this_month(uid)
            limit_str = "Unlimited" if img_limit == -1 else f"{used_imgs}/{img_limit} used this month"
            st.markdown(f"**Generate with AI** &nbsp; <span style='font-size:12px;color:#94A3B8;'>🎨 {limit_str}</span>", unsafe_allow_html=True)
            img_prompt = st.text_input("Image description (or leave blank to auto-generate from post)",
                                        placeholder="e.g. A happy team celebrating in an office", key="img_prompt")
            if st.button("🎨 Generate AI Image", key="gen_img", use_container_width=True):
                if post_text or img_prompt:
                    from saas.image_gen import get_active_image_model
                    _mid, _prov = get_active_image_model()
                    _model_name = _mid.split("/")[-1].upper() if _mid else "AI"
                    with st.spinner(f"Generating with {_model_name}..."):
                        try:
                            from saas.ai_writer import generate_image_prompt
                            from saas.image_gen import generate_image, save_b64_image
                            prompt_to_use = img_prompt or generate_image_prompt(
                                post_text, platform, user.get("business_name",""))
                            result = generate_image(prompt_to_use, platform,
                                                    user.get("business_name",""))
                            os.makedirs("./temp_images", exist_ok=True)
                            path = f"./temp_images/{uid}_{uuid.uuid4().hex[:8]}.png"
                            save_b64_image(result["b64_json"], path)
                            st.session_state.gen_images = [path]
                            db.track_usage(uid, "image_generated")
                            st.success("Image generated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Image generation failed: {e}")
                else:
                    st.warning("Enter post text or image description first.")

            if st.session_state.gen_images:
                img_path = st.session_state.gen_images[0]
                if os.path.exists(img_path):
                    st.image(img_path, caption="AI Generated", use_column_width=True)
                    image_url_final = img_path

    # ── Step 5: Publish / Schedule ──
    st.markdown('<div class="sec-title">5. Publish</div>', unsafe_allow_html=True)

    p1, p2, p3 = st.columns([1, 1.5, 3], gap="medium")
    with p1:
        if st.button("🚀 Post Now", type="primary", use_container_width=True, key="post_now"):
            if not post_text:
                st.error("Please write or generate post content first.")
            else:
                _do_publish_now(uid, platform, post_text, image_url_final)

    with p2:
        from saas.billing import can_use_scheduling
        can_sched, sched_msg = can_use_scheduling(uid)
        if can_sched:
            sched_time = st.date_input("Schedule date", min_value=datetime.today().date(), label_visibility="collapsed")
            sched_hour = st.selectbox("Time", [f"{h:02d}:00" for h in range(6, 24)], index=8, label_visibility="collapsed")
            if st.button("⏰ Schedule", use_container_width=True, key="schedule_btn"):
                if not post_text:
                    st.error("Please write post content first.")
                else:
                    _do_schedule(uid, platform, post_text, image_url_final, sched_time, sched_hour)
        else:
            st.markdown(f"""
            <div class="upgrade-gate" style="padding:14px;">
                <div style="font-size:11px;color:#7C3AED;font-weight:700;">⏰ Scheduling requires Starter+</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Upgrade →", key="upg_sched"):
                go_to("settings")

    with p3:
        if st.button("💾 Save as Draft", use_container_width=True, key="save_draft_btn"):
            if post_text:
                _do_save_draft(uid, platform, post_text, image_url_final)

def _do_publish_now(uid, platform, content, image_url):
    from saas.publisher import publish_post
    import time
    with st.spinner(f"Publishing to {platform.title()}..."):
        post = db.create_post(uid, platform, content,
                              image_url=image_url, status="scheduled",
                              scheduled_at=datetime.now(timezone.utc).isoformat())
        ok, result = publish_post(post)
        db.update_post(post["id"],
                       status="published" if ok else "failed",
                       platform_post_id=result if ok else None,
                       error_message=None if ok else result,
                       published_at=datetime.now(timezone.utc).isoformat() if ok else None)
        db.track_usage(uid, "post_created", platform)
    if ok:
        st.success(f"✅ Published to {platform.title()}!")
        st.session_state.post_draft = ""
        st.session_state.gen_images = []
    else:
        st.error(f"Failed: {result}")

def _do_schedule(uid, platform, content, image_url, date, hour_str):
    hour  = int(hour_str.split(":")[0])
    sched = datetime(date.year, date.month, date.day, hour, 0, 0,
                     tzinfo=timezone.utc)
    db.create_post(uid, platform, content, image_url=image_url,
                   status="scheduled", scheduled_at=sched.isoformat())
    db.track_usage(uid, "post_created", platform)
    st.success(f"✅ Scheduled for {date.strftime('%d %b %Y')} at {hour_str}!")
    st.session_state.post_draft = ""

def _do_save_draft(uid, platform, content, image_url):
    db.create_post(uid, platform, content, image_url=image_url, status="draft")
    st.success("Draft saved.")


# ── MY POSTS ───────────────────────────────────────────────────────────────────
def render_posts():
    uid   = st.session_state.user["id"]
    conns = get_connections()

    st.markdown('<div class="page-title">📋 My Posts</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">All your posts across every connected platform.</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns([2, 2, 1], gap="medium")
    with f1:
        platforms = ["All"] + [c["platform"] for c in conns]
        platform_filter = st.selectbox("Platform", platforms,
            format_func=lambda p: f"{platform_icon(p) + ' ' if p != 'All' else ''}{p.title()}")
    with f2:
        status_filter = st.selectbox("Status", ["All", "Published", "Scheduled", "Draft", "Failed"])
    with f3:
        if st.button("➕ New Post", type="primary", use_container_width=True):
            go_to("compose")

    posts = db.get_posts(
        uid,
        platform=None if platform_filter == "All" else platform_filter,
        status=None if status_filter == "All" else status_filter.lower(),
        limit=30,
    )

    if not posts:
        st.info("No posts found. Create your first post!")
        return

    for post in posts:
        icon   = platform_icon(post["platform"])
        status = post["status"]
        sc     = {"published":"#22C55E","scheduled":"#F59E0B","draft":"#94A3B8","failed":"#EF4444"}.get(status,"#94A3B8")
        date   = (post.get("published_at") or post.get("scheduled_at") or post["created_at"])[:16].replace("T"," ")

        col_content, col_actions = st.columns([5, 1])
        with col_content:
            img_html = f'<img src="{post["image_url"]}" style="width:60px;height:60px;object-fit:cover;border-radius:8px;margin-right:12px;float:left;" />' if post.get("image_url") and not post["image_url"].startswith("data:") else ""
            st.markdown(f"""
            <div class="post-card post-status-{status}">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <div>
                        <span style="font-weight:700;color:#1E293B;">{icon} {post['platform'].title()}</span>
                        <span style="font-size:11px;color:{sc};margin-left:10px;font-weight:700;">{status.upper()}</span>
                    </div>
                    <span style="font-size:11px;color:#94A3B8;">{date}</span>
                </div>
                {img_html}
                <div style="font-size:13px;color:#475569;line-height:1.5;">{post['content'][:200]}{"…" if len(post['content'])>200 else ""}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_actions:
            if status == "draft":
                if st.button("Publish", key=f"pub_{post['id']}", type="primary", use_container_width=True):
                    _do_publish_now(uid, post["platform"], post["content"], post.get("image_url"))
            if status != "deleted":
                if st.button("Delete", key=f"del_{post['id']}", use_container_width=True):
                    db.update_post(post["id"], status="deleted")
                    st.rerun()


# ── ANALYTICS ──────────────────────────────────────────────────────────────────
def render_analytics():
    uid  = st.session_state.user["id"]
    tier = get_tier()

    st.markdown('<div class="page-title">📊 Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Performance across all your connected platforms.</div>', unsafe_allow_html=True)

    from saas.billing import can_use_analytics
    can, msg = can_use_analytics(uid)
    if not can:
        st.markdown(f"""
        <div class="upgrade-gate">
            <div style="font-size:40px;margin-bottom:8px">📊</div>
            <div style="font-weight:700;font-size:18px;color:#7C3AED;">{msg}</div>
            <div style="font-size:13px;color:#6B7280;margin:8px 0 20px;">Upgrade to see detailed analytics for all your posts.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Upgrade to Starter Plan →", type="primary"):
            go_to("settings")
        return

    days = st.selectbox("Period", [7, 14, 30, 90], index=2, format_func=lambda d: f"Last {d} days")

    if st.button("🔄 Refresh Analytics", type="primary"):
        with st.spinner("Pulling metrics from all platforms..."):
            from saas.analytics import refresh_all_analytics
            refresh_all_analytics(uid)
        st.success("Analytics updated!")
        st.rerun()

    # Overall summary
    summary = db.get_analytics_summary(uid, days=days)
    conns   = get_connections()

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-box">
            <div class="metric-val">{int(summary.get('total_posts',0))}</div>
            <div class="metric-lbl">Posts Published</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{int(summary.get('total_reach',0)):,}</div>
            <div class="metric-lbl">Total Reach</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{int(summary.get('total_impressions',0)):,}</div>
            <div class="metric-lbl">Impressions</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{int(summary.get('total_likes',0)):,}</div>
            <div class="metric-lbl">Likes</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{int(summary.get('total_comments',0)):,}</div>
            <div class="metric-lbl">Comments</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{int(summary.get('total_shares',0)):,}</div>
            <div class="metric-lbl">Shares</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Per-platform breakdown
    platform_data = db.get_posts_per_platform(uid, days=days)
    if platform_data:
        st.markdown('<div class="sec-title">📈 By Platform</div>', unsafe_allow_html=True)
        cols = st.columns(len(platform_data), gap="medium")
        for i, pd_ in enumerate(platform_data):
            with cols[i]:
                icon = platform_icon(pd_["platform"])
                st.markdown(f"""
                <div class="metric-box">
                    <div style="font-size:24px">{icon}</div>
                    <div class="metric-val">{pd_['count']}</div>
                    <div class="metric-lbl">{pd_['platform'].title()} Posts</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:4px;">{pd_['engagement']:,} engagements</div>
                </div>
                """, unsafe_allow_html=True)

    # Top posts
    st.markdown('<div class="sec-title">🏆 Top Performing Posts</div>', unsafe_allow_html=True)
    from saas.analytics import get_top_posts
    top_posts = get_top_posts(uid, limit=5)
    if top_posts:
        for post in top_posts:
            icon = platform_icon(post["platform"])
            st.markdown(f"""
            <div class="post-card post-status-published">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:700;color:#1E293B;">{icon} {post['platform'].title()}</span>
                    <span style="font-size:12px;color:#7C3AED;font-weight:700;">
                        ❤️ {post.get('likes',0)} &nbsp; 💬 {post.get('comments',0)} &nbsp; 🔁 {post.get('shares',0)}
                    </span>
                </div>
                <div style="font-size:13px;color:#475569;margin-top:6px;">{post['content'][:180]}…</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No published posts with analytics yet. Publish some posts and refresh!")

    # Best times
    st.markdown('<div class="sec-title">⏰ Best Times to Post</div>', unsafe_allow_html=True)
    from saas.analytics import get_best_post_times
    best_times = get_best_post_times(uid)[:5]
    if best_times:
        for bt in best_times:
            hour  = bt["hour"]
            ampm  = f"{'AM' if hour < 12 else 'PM'}"
            h12   = hour % 12 or 12
            bar   = "█" * min(int(bt["avg_engagement"] / max(best_times[0]["avg_engagement"], 1) * 20), 20)
            st.markdown(f"`{h12:2d}:00 {ampm}` {bar} avg {bt['avg_engagement']:.1f} engagements")
    else:
        st.info("Not enough data yet. Keep posting and this will fill in!")


# ── AI STRATEGY ────────────────────────────────────────────────────────────────
def render_strategy():
    uid  = st.session_state.user["id"]
    user = st.session_state.user
    tier = get_tier()

    st.markdown('<div class="page-title">🧠 AI Strategy</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">AI-powered research + personalised recommendations to grow your audience.</div>', unsafe_allow_html=True)

    from saas.billing import can_use_strategy
    can, msg = can_use_strategy(uid)
    if not can:
        st.markdown(f"""
        <div class="upgrade-gate">
            <div style="font-size:40px;margin-bottom:8px">🧠</div>
            <div style="font-weight:700;font-size:18px;color:#7C3AED;">{msg}</div>
            <div style="font-size:13px;color:#6B7280;margin:8px 0 20px;">
                AI strategy briefs use live web research and your performance data to generate
                weekly action plans, content ideas, and platform-specific recommendations.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Upgrade to Growth Plan →", type="primary"):
            go_to("settings")
        return

    conns    = get_connections()
    plats    = [c["platform"] for c in conns]
    biz_name = user.get("business_name", "My Business")

    if st.button("🔬 Generate Strategy Brief", type="primary", use_container_width=False):
        with st.spinner("Researching market trends and analysing your performance (1-2 min)..."):
            try:
                summary    = db.get_analytics_summary(uid, days=30)
                top_posts  = __import__("saas.analytics", fromlist=["get_top_posts"]).get_top_posts(uid, limit=10)
                from saas.ai_writer import generate_strategy_brief
                brief = generate_strategy_brief(
                    user_id=uid, business_name=biz_name,
                    business_type=user.get("business_type", "business"),
                    platforms=plats, recent_posts=top_posts, analytics_summary=dict(summary),
                )
                db.save_suggestion(uid, title="Weekly Strategy Brief", description=brief,
                                   suggestion_type="STRATEGY", urgency="MEDIUM", status="pending")
                st.success("Brief generated!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")

    # Show suggestions
    suggestions = db.get_suggestions(uid, status="all")
    if not suggestions:
        st.markdown("""
        <div class="card" style="text-align:center;padding:48px 24px;">
            <div style="font-size:52px;margin-bottom:14px">🧠</div>
            <div class="card-title" style="font-size:18px">No strategy briefs yet</div>
            <div class="card-sub">Click "Generate Strategy Brief" to get your first AI-powered action plan.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    for s in suggestions:
        urg = s.get("urgency", "MEDIUM")
        icon = {"pending":"⏳","approved":"✅","rejected":"❌"}.get(s["status"],"○")
        with st.expander(f"{icon} {s['title']} · {s.get('created_at','')[:10]}", expanded=(s["status"]=="pending")):
            if s.get("description"):
                st.markdown(s["description"])
            if s["status"] == "pending":
                a1, a2 = st.columns([1, 1])
                with a1:
                    if st.button("✅ Mark Done", key=f"done_{s['id']}", type="primary"):
                        db.update_suggestion(s["id"], "approved", "Marked as actioned")
                        st.rerun()
                with a2:
                    if st.button("❌ Dismiss", key=f"dis_{s['id']}"):
                        db.update_suggestion(s["id"], "rejected", "Dismissed")
                        st.rerun()


# ── SETTINGS + PRICING ─────────────────────────────────────────────────────────
def render_settings():
    uid  = st.session_state.user["id"]
    user = st.session_state.user
    tier = get_tier()
    sub  = db.get_subscription(uid)

    is_admin = is_owner_session()

    # All users see Subscription + Profile + AI Model picker
    # API Keys and legacy AI Models config are admin-only
    tab_labels = ["💳 Subscription", "👤 Profile", "🤖 AI Model"]
    if is_admin:
        tab_labels += ["🔑 API Keys", "🛠️ Admin — AI Models"]
    tabs = st.tabs(tab_labels)

    # ── Subscription ──
    with tabs[0]:
        st.markdown("### Your Current Plan")
        st.markdown(f"""
        <div class="card">
            <div style="font-size:22px;font-weight:800;color:#7C3AED;">{tier.name}</div>
            <div style="font-size:13px;color:#64748B;margin-top:4px;">{tier.description}</div>
            <div style="margin-top:12px;font-size:13px;color:#334155;">
                {'🔒 Status: ' + sub.get('status','').title()}<br>
                {'📅 Renews: ' + (sub.get('current_period_end','')[:10] if sub.get('current_period_end') else 'N/A')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if tier.id != "free" and sub.get("stripe_customer_id"):
            if st.button("Manage Billing (Stripe Portal)"):
                try:
                    from saas.billing import create_portal_session
                    url = create_portal_session(uid)
                    st.markdown(f'<a href="{url}" target="_blank">Open Billing Portal →</a>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Could not open portal: {e}")

        # Pricing table
        st.markdown("### Available Plans")
        billing_period = st.radio("Billing", ["Monthly", "Yearly (save ~17%)"], horizontal=True)
        yearly = billing_period.startswith("Yearly")

        p_cols = st.columns(4, gap="medium")
        for i, (tid, t) in enumerate(TIERS.items()):
            with p_cols[i]:
                is_current = tier.id == tid
                price      = t.price_yearly / 12 if yearly else t.price_monthly
                highlight  = "pricing-card-highlight" if t.highlight else ""
                popular    = '<div class="pricing-popular">Most Popular</div>' if t.highlight else ""

                if t.image_gen_limit == 0:
                    img_feat = ("AI images", False)
                elif t.image_gen_limit == -1:
                    img_feat = ("Unlimited AI images/month", True)
                else:
                    img_feat = (f"{t.image_gen_limit} AI images/month", True)

                rows = [
                    (f"{t.platform_limit if t.platform_limit > 0 else '∞'} platform(s)", True),
                    img_feat,
                    ("Post scheduling", t.post_scheduling),
                    ("Analytics", t.analytics),
                    ("AI strategy briefs", t.ai_strategy_briefs),
                    ("Google Ads manager", t.google_ads),
                    (f"{t.posts_per_month if t.posts_per_month > 0 else '∞'} posts/month", True),
                    (f"{t.team_members} team member(s)", True),
                ]
                feat_html = "".join(
                    f'<div style="padding:2px 0;">{"✅" if ok else "❌"} {feat}</div>'
                    for feat, ok in rows
                )
                yearly_badge = f'<div style="font-size:12px;color:#94A3B8;">Billed yearly</div>' if yearly and price > 0 else ''
                popular_html = f'<div style="background:#7C3AED;color:white;font-size:11px;font-weight:700;padding:4px 14px;border-radius:20px;display:inline-block;margin-bottom:12px;">Most Popular</div>' if t.highlight else ''
                border = "border:3px solid #7C3AED;" if t.highlight else "border:1px solid #E2E8F0;"

                per_mo = '<span style="font-size:14px;font-weight:400;color:#94A3B8;">/mo</span>'
                price_html = "Free" if price == 0 else f"${price:.0f}{per_mo}"
                card_html = (
                    f'<div style="background:white;border-radius:16px;padding:28px 24px;'
                    f'box-shadow:0 4px 20px rgba(0,0,0,0.08);text-align:center;{border}">'
                    f'{popular_html}'
                    f'<div style="font-size:20px;font-weight:800;color:#1E293B;">{t.name}</div>'
                    f'<div style="font-size:40px;font-weight:800;color:#7C3AED;line-height:1.1;">{price_html}</div>'
                    f'{yearly_badge}'
                    f'<div style="font-size:13px;color:#475569;text-align:left;margin:16px 0;line-height:1.9;">{feat_html}</div>'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

                if is_current:
                    st.markdown("**✅ Current plan**")
                elif tid == "free":
                    st.markdown("_(Free forever)_")
                else:
                    btn_label = "Upgrade" if t.price_monthly > tier.price_monthly else "Downgrade"
                    if st.button(f"{btn_label} to {t.name}", key=f"sub_{tid}", type="primary" if t.highlight else "secondary", use_container_width=True):
                        try:
                            from saas.billing import create_checkout_session
                            checkout_url = create_checkout_session(
                                uid, user["email"], user["name"], tid,
                                "yearly" if yearly else "monthly",
                            )
                            st.markdown(f'<a href="{checkout_url}" target="_blank">**Continue to payment →**</a>', unsafe_allow_html=True)
                        except Exception as e:
                            st.warning(f"Stripe not configured: {e}\n\nAdd your Stripe keys to `.env` to enable payments.")

    # ── Profile ──
    with tabs[1]:
        st.markdown("### Profile Settings")
        new_name = st.text_input("Your name", value=user.get("name",""))
        new_biz  = st.text_input("Business name", value=user.get("business_name",""))
        if st.button("Save Changes", type="primary"):
            db.update_user(uid, name=new_name, business_name=new_biz)
            st.session_state.user["name"] = new_name
            st.session_state.user["business_name"] = new_biz
            st.success("Profile updated!")

        st.markdown("---")
        if st.button("Sign Out"):
            _do_logout()

    # ── AI Model picker (all users) ──
    with tabs[2]:
        st.markdown("### 🤖 Choose Your AI Model")
        st.markdown("Select the AI model that powers your content writing, ad plans, and chat assistant.")
        render_model_picker(uid, context="settings")

    # ── API Keys (admin only) ──
    if is_admin:
      with tabs[3]:
        st.markdown("### API Keys & Credentials")
        st.info("These are your operator keys — stored in `.env` on your server. Customers never see this tab.")

        keys_info = [
            ("GEMINI_API_KEY",        "Google Gemini AI",            "Get from aistudio.google.com → Get API key",         True),
            ("OPENAI_API_KEY",        "OpenAI (DALL-E / GPT)",       "Get from platform.openai.com/api-keys",              False),
            ("FAL_API_KEY",           "fal.ai (FLUX images)",        "Get from fal.ai/dashboard — best image quality",     False),
            ("ANTHROPIC_API_KEY",     "Anthropic (Claude models)",   "Get from console.anthropic.com/settings/keys",       False),
            ("META_APP_ID",           "Facebook/Instagram App ID",   "Get from developers.facebook.com",                  False),
            ("META_APP_SECRET",       "Facebook/Instagram Secret",   "Get from developers.facebook.com",                  False),
            ("LINKEDIN_CLIENT_ID",    "LinkedIn Client ID",          "Get from linkedin.com/developers",                  False),
            ("LINKEDIN_CLIENT_SECRET","LinkedIn Client Secret",      "Get from linkedin.com/developers",                  False),
            ("TIKTOK_CLIENT_KEY",     "TikTok Client Key",           "Get from developers.tiktok.com",                    False),
            ("TIKTOK_CLIENT_SECRET",  "TikTok Client Secret",        "Get from developers.tiktok.com",                    False),
            ("TWITTER_CLIENT_ID",     "Twitter Client ID",           "Get from developer.twitter.com",                   False),
            ("TWITTER_CLIENT_SECRET", "Twitter Client Secret",       "Get from developer.twitter.com",                   False),
            ("STRIPE_SECRET_KEY",     "Stripe Secret Key",           "Get from dashboard.stripe.com/apikeys",             False),
            ("STRIPE_WEBHOOK_SECRET", "Stripe Webhook Secret",       "Get from dashboard.stripe.com/webhooks",            False),
        ]

        for env_key, label, instruction, required in keys_info:
            current = os.environ.get(env_key, "")
            status = "✅ Set" if current else ("⚠️ Required" if required else "❌ Not set")
            with st.expander(f"{status} — **{label}** (`{env_key}`)"):
                st.caption(instruction)
                new_val = st.text_input(f"Value", value="•••••••••" if current else "",
                                        type="password", key=f"key_{env_key}",
                                        placeholder="Paste your key here")
                if st.button(f"Save {label}", key=f"save_{env_key}"):
                    _update_env_key(env_key, new_val)
                    os.environ[env_key] = new_val   # apply immediately this session
                    st.success(f"Saved! Restart the app to apply fully.")

    # ── Admin: AI Models ──
    if is_admin and len(tabs) == 5:
        with tabs[4]:
            _render_admin_models()


def _render_admin_models():
    """Admin-only panel: configure which AI model each subscription tier uses."""
    from saas.model_registry import TEXT_MODELS, IMAGE_MODELS, fetch_all_live_models
    TIERS_ORDER = ["free", "starter", "growth", "agency"]
    TIER_LABELS = {"free": "Free Trial", "starter": "Starter ($29)", "growth": "Growth ($79)", "agency": "Agency ($199)"}

    st.markdown("### 🛠️ AI Model Configuration")
    st.info("Only you can see this panel. Choose which AI model each subscription tier uses for text and image generation.")

    # ── Refresh from providers ──
    col_r, col_info = st.columns([1, 3])
    with col_r:
        if st.button("🔄 Refresh from Providers", type="primary"):
            with st.spinner("Fetching latest models from Google & OpenAI..."):
                result = fetch_all_live_models()
            st.success(f"Done! Found {result['new_text_count']} new text model(s) from your providers.")
            st.rerun()
    with col_info:
        st.caption("Checks Google AI and OpenAI APIs for newly released models using your configured API keys.")

    st.markdown("---")

    # ── Text models ──
    st.markdown("#### ✍️ Text Generation (AI Post Writing)")
    text_model_options = {f"{m['name']} — {m['cost_note']} ({m['quality']}) [{m['provider']}]": m
                          for m in TEXT_MODELS}
    text_option_keys = list(text_model_options.keys())

    t_cols = st.columns(4)
    for i, tier in enumerate(TIERS_ORDER):
        with t_cols[i]:
            st.markdown(f"**{TIER_LABELS[tier]}**")
            config = db.get_model_config("text", tier)
            current_id = config["model_id"] if config else "gemini-2.0-flash"
            current_label = next(
                (k for k, v in text_model_options.items() if v["id"] == current_id),
                text_option_keys[0]
            )
            chosen_label = st.selectbox(
                f"Text model", text_option_keys,
                index=text_option_keys.index(current_label) if current_label in text_option_keys else 0,
                key=f"text_model_{tier}", label_visibility="collapsed"
            )
            chosen = text_model_options[chosen_label]
            if st.button("Save", key=f"save_text_{tier}", use_container_width=True):
                db.set_model_config("text", tier, chosen["id"], chosen["provider"])
                st.success("✅ Saved")

    st.markdown("---")

    # ── Image model (single best for all tiers) ──
    st.markdown("#### 🎨 Image Generation — Best Model (used by all paying plans)")
    st.caption("Every paying customer gets the same top-quality model. Limits per plan are set below.")

    img_model_options = {
        f"{m['name']} — {m['cost_note']} ({m['quality']}) [{m['provider']}]": m
        for m in IMAGE_MODELS
    }
    img_option_keys = list(img_model_options.keys())

    config_best = db.get_model_config("image", "best")
    current_best_id = config_best["model_id"] if config_best else "fal-ai/flux-pro"
    current_best_label = next(
        (k for k, v in img_model_options.items() if v["id"] == current_best_id),
        img_option_keys[0]
    )

    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        chosen_img_label = st.selectbox(
            "Best image model", img_option_keys,
            index=img_option_keys.index(current_best_label) if current_best_label in img_option_keys else 0,
            key="img_model_best", label_visibility="collapsed"
        )
    with col_btn:
        if st.button("Save Model", key="save_img_best", type="primary", use_container_width=True):
            chosen_m = img_model_options[chosen_img_label]
            db.set_model_config("image", "best", chosen_m["id"], chosen_m["provider"])
            st.success(f"✅ All plans now use **{chosen_m['name']}**")

    st.markdown("---")

    # ── Image generation limits per tier ──
    st.markdown("#### 📊 AI Image Limits per Plan")
    st.caption("Set how many AI images each plan can generate per month. 0 = disabled. -1 = unlimited.")

    from saas.config import TIERS as _TIERS
    limit_cols = st.columns(4)
    for i, tier_key in enumerate(TIERS_ORDER):
        with limit_cols[i]:
            t = _TIERS[tier_key]
            st.markdown(f"**{TIER_LABELS[tier_key]}**")
            current_limit = t.image_gen_limit
            label_hint = "0 = off · -1 = unlimited"
            new_limit = st.number_input(
                f"Images/month", value=current_limit, min_value=-1, step=5,
                key=f"img_limit_{tier_key}", help=label_hint,
                label_visibility="collapsed"
            )
            if st.button("Save", key=f"save_limit_{tier_key}", use_container_width=True):
                # Patch the live TIERS object so it takes effect immediately
                _TIERS[tier_key].image_gen_limit = int(new_limit)
                _TIERS[tier_key].ai_images = (int(new_limit) != 0)
                st.success(f"✅ {TIER_LABELS[tier_key]}: {int(new_limit)} images/mo")
                st.caption("⚠️ Restart app to make permanent. Edit saas/config.py for persistence.")

    st.markdown("---")

    # ── Current config summary ──
    st.markdown("#### 📋 Current Configuration")
    all_configs = db.get_all_model_configs()
    rows_text  = [c for c in all_configs if c["model_type"] == "text"]
    rows_image = [c for c in all_configs if c["model_type"] == "image"]

    col_t, col_i = st.columns(2)
    with col_t:
        st.markdown("**Text models per tier:**")
        for r in rows_text:
            mid = r['model_id'] or '—'
            st.markdown(f"- **{TIER_LABELS.get(r['tier'], r['tier'])}**: `{mid}`")
    with col_i:
        st.markdown("**Image generation:**")
        best = next((r for r in rows_image if r['tier'] == 'best'), None)
        if best:
            st.markdown(f"- **Model (all plans)**: `{best['model_id']}`")
        from saas.config import TIERS as _T
        for tk in TIERS_ORDER:
            lim = _T[tk].image_gen_limit
            lim_str = "Disabled" if lim == 0 else ("Unlimited" if lim == -1 else f"{lim}/month")
            st.markdown(f"- **{TIER_LABELS[tk]}**: {lim_str}")

    # ── Required API keys status ──
    st.markdown("---")
    st.markdown("#### 🔑 Provider API Key Status")
    provider_keys = {
        "Google (Gemini/Imagen)": "GEMINI_API_KEY",
        "OpenAI (GPT/DALL-E)":   "OPENAI_API_KEY",
        "fal.ai (FLUX/Ideogram)": "FAL_API_KEY",
        "Anthropic (Claude)":    "ANTHROPIC_API_KEY",
    }
    k_cols = st.columns(len(provider_keys))
    for i, (name, env_key) in enumerate(provider_keys.items()):
        with k_cols[i]:
            val = os.environ.get(env_key, "")
            status = "✅ Set" if val else "❌ Missing"
            colour = "#22C55E" if val else "#EF4444"
            st.markdown(
                f'<div style="background:white;border-radius:10px;padding:14px;text-align:center;'
                f'border:2px solid {colour};margin-bottom:8px;">'
                f'<div style="font-size:18px;">{status}</div>'
                f'<div style="font-size:12px;color:#64748B;margin-top:4px;">{name}</div>'
                f'</div>',
                unsafe_allow_html=True
            )


def _update_env_key(key: str, value: str):
    """Write or update a key in the .env file."""
    env_path = ".env"
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path) as f:
            lines = f.readlines()
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}\n")
    with open(env_path, "w") as f:
        f.writelines(new_lines)


# ══════════════════════════════════════════════════════════════════════════════
# MODEL PICKER WIDGET (reusable)
# ══════════════════════════════════════════════════════════════════════════════
def render_model_picker(user_id: str, context: str = "settings"):
    """
    Interactive AI model selector.
    Shows all models grouped by provider with cost, speed, and capability info.
    Saves the selection to the subscriber's business_profile.
    """
    from saas.models import (ALL_MODELS, PROVIDER_ICONS, PROVIDER_COLORS,
                              TIER_BADGE, monthly_cost_estimate)

    current_model, current_provider = db.get_preferred_model(user_id)

    st.markdown("""
    <div style="font-size:13px;color:#94A3B8;margin-bottom:16px;">
      Choose the AI model that powers your ad plans, onboarding, and chat.
      You can change this any time — takes effect immediately.
    </div>
    """, unsafe_allow_html=True)

    # Group by provider
    providers = ["anthropic", "google", "openai"]
    provider_labels = {
        "anthropic": "Claude (Anthropic)",
        "google":    "Gemini (Google)",
        "openai":    "GPT (OpenAI)",
    }

    for provider in providers:
        provider_models = [m for m in ALL_MODELS if m.provider == provider]
        if not provider_models:
            continue

        icon  = PROVIDER_ICONS.get(provider, "⬡")
        color = PROVIDER_COLORS.get(provider, "#7C3AED")
        label = provider_labels.get(provider, provider.title())

        # Check if API key is set
        key_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "google":    "GEMINI_API_KEY",
            "openai":    "OPENAI_API_KEY",
        }
        has_key = bool(os.environ.get(key_map.get(provider, ""), ""))
        key_status = "✅" if has_key else "⚠️ API key not set"

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin:18px 0 10px;">
          <span style="font-size:18px;">{icon}</span>
          <span style="font-size:14px;font-weight:800;color:#E2E8F0;">{label}</span>
          <span style="font-size:11px;color:{'#22C55E' if has_key else '#EF4444'};">{key_status}</span>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(len(provider_models), gap="small")
        for col_idx, m in enumerate(provider_models):
            is_selected = (m.id == current_model)
            tier_label, tier_color = TIER_BADGE.get(m.tier, ("", "#64748B"))
            monthly = monthly_cost_estimate(m.id, "medium")

            with cols[col_idx]:
                card_class = "model-card model-card-selected" if is_selected else "model-card"
                speed_icon = {"fast": "⚡", "medium": "🔄", "slow": "🧠"}.get(m.speed, "")

                st.markdown(f"""
                <div class="{card_class}">
                  <span class="tier-badge-model"
                    style="background:rgba{tuple(int(tier_color.lstrip('#')[i:i+2],16) for i in (0,2,4))}22;
                           color:{tier_color};border:1px solid {tier_color}44;">
                    {tier_label}
                  </span>
                  {"<span class='recommended-badge'>★ RECOMMENDED</span>" if m.is_recommended else ""}
                  <div class="model-provider" style="color:{color};">
                    {icon} {m.provider_label.upper()}
                  </div>
                  <div class="model-name">{m.name}</div>
                  <div class="model-desc">{m.description}</div>
                  <div class="model-cost" style="color:{color};">
                    ~${monthly:.2f}/mo typical &nbsp; {speed_icon} {m.speed.title()}
                  </div>
                  <div style="font-size:10px;color:#475569;margin-top:4px;">
                    ${m.cost_input_per_m:.2f} in / ${m.cost_output_per_m:.2f} out per 1M tokens
                  </div>
                  {"<div style='margin-top:8px;font-size:11px;color:#22C55E;font-weight:700;'>✓ Currently selected</div>" if is_selected else ""}
                </div>
                """, unsafe_allow_html=True)

                btn_label = "✓ Selected" if is_selected else "Select"
                btn_type  = "secondary" if is_selected else "primary"
                if not is_selected:
                    if st.button(btn_label, key=f"model_pick_{m.id}_{context}",
                                 type=btn_type, use_container_width=True,
                                 disabled=(not has_key)):
                        db.set_preferred_model(user_id, m.id, m.provider)
                        st.success(f"✅ Switched to {m.name}")
                        st.rerun()
                else:
                    st.button("✓ Selected", key=f"model_sel_{m.id}_{context}",
                              use_container_width=True, disabled=True)

    # Cost comparison table
    st.markdown("")
    with st.expander("📊 Full cost comparison table"):
        cost_rows = []
        for m in ALL_MODELS:
            cost_rows.append({
                "Model": m.name,
                "Provider": m.provider_label,
                "Tier": m.tier.title(),
                "Input (per 1M)": f"${m.cost_input_per_m:.2f}",
                "Output (per 1M)": f"${m.cost_output_per_m:.2f}",
                "Light (~$)": f"{monthly_cost_estimate(m.id,'light'):.3f}",
                "Medium (~$)": f"{monthly_cost_estimate(m.id,'medium'):.2f}",
                "Heavy (~$)": f"{monthly_cost_estimate(m.id,'heavy'):.2f}",
                "Speed": m.speed.title(),
            })
        try:
            import pandas as pd
            df = pd.DataFrame(cost_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception:
            for row in cost_rows:
                st.markdown(f"**{row['Model']}** — {row['Input (per 1M)']} in / {row['Output (per 1M)']} out — Medium: ~${row['Medium (~$)']}")


# ══════════════════════════════════════════════════════════════════════════════
# OWNER ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def render_admin():
    from saas import admin as adm
    from saas.models import get_model, PROVIDER_ICONS

    if not is_owner_session():
        st.error("⛔ Access denied — owner accounts only.")
        return

    # ── Drill-in: single subscriber view ──
    drill_id = st.query_params.get("sub")
    if drill_id:
        _render_subscriber_detail(drill_id)
        return

    # ── Header ──
    st.markdown("""
    <div class="admin-banner">
      <div>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
          <span class="admin-badge">OWNER DASHBOARD</span>
        </div>
        <div style="font-size:22px;font-weight:800;color:#E2E8F0;">AdFlow AI Control Centre</div>
        <div style="font-size:13px;color:#64748B;">Full visibility of all subscribers, health, and platform performance.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Aggregate stats ──
    with st.spinner("Loading platform stats..."):
        stats = adm.owner_stats()

    health = stats.get("health_breakdown", {})
    tier_b = stats.get("tier_breakdown", {})

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-box"><div class="metric-val">{stats['total_subscribers']}</div><div class="metric-lbl">Total Subscribers</div></div>
      <div class="metric-box"><div class="metric-val">{stats['new_this_week']}</div><div class="metric-lbl">New This Week</div></div>
      <div class="metric-box"><div class="metric-val">{stats['total_posts']:,}</div><div class="metric-lbl">Posts All Time</div></div>
      <div class="metric-box"><div class="metric-val">{stats['posts_last_30d']:,}</div><div class="metric-lbl">Posts (30d)</div></div>
      <div class="metric-box"><div class="metric-val">{stats['total_campaigns']}</div><div class="metric-lbl">Campaigns Created</div></div>
      <div class="metric-box"><div class="metric-val">{stats['profiles_complete']}</div><div class="metric-lbl">Profiles Complete</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Health breakdown + Tier breakdown ──
    col_h, col_t, col_m = st.columns(3)

    with col_h:
        st.markdown('<div class="sec-title">🟢 Health Breakdown</div>', unsafe_allow_html=True)
        for status, color in [("Healthy","#22C55E"),("Growing","#F59E0B"),
                               ("Dormant","#EF4444"),("New","#64748B")]:
            cnt = health.get(status, 0)
            st.markdown(f"""
            <div class="card" style="padding:10px 14px;margin-bottom:6px;border-left:3px solid {color};">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:12px;color:#CBD5E1;">{status}</span>
                <span style="font-size:18px;font-weight:800;color:{color};">{cnt}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

    with col_t:
        st.markdown('<div class="sec-title">💳 Plan Tiers</div>', unsafe_allow_html=True)
        for tier_k, tier_label in [("agency","Agency"),("growth","Growth"),
                                   ("starter","Starter"),("free","Free")]:
            cnt  = tier_b.get(tier_k, 0)
            color = {"agency":"#A78BFA","growth":"#06B6D4","starter":"#F59E0B","free":"#64748B"}.get(tier_k,"#64748B")
            st.markdown(f"""
            <div class="card" style="padding:10px 14px;margin-bottom:6px;border-left:3px solid {color};">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:12px;color:#CBD5E1;">{tier_label}</span>
                <span style="font-size:18px;font-weight:800;color:{color};">{cnt}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

    with col_m:
        st.markdown('<div class="sec-title">🤖 Model Usage</div>', unsafe_allow_html=True)
        model_usage = adm.model_usage_summary()
        if model_usage:
            for mu in model_usage[:5]:
                m = get_model(mu.get("model", ""))
                icon = PROVIDER_ICONS.get(m.provider if m else "", "⬡")
                name = m.name if m else mu.get("model","Unknown")
                st.markdown(f"""
                <div class="card" style="padding:10px 14px;margin-bottom:6px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-size:12px;color:#CBD5E1;">{icon} {name}</span>
                    <span style="font-size:16px;font-weight:800;color:#A78BFA;">{mu['count']}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:12px;color:#475569;">No model data yet.</div>', unsafe_allow_html=True)

    # ── Subscriber grid ──
    st.markdown('<div class="sec-title">👤 All Subscribers</div>', unsafe_allow_html=True)

    # Search + filter bar
    col_srch, col_filt, col_sort = st.columns([3, 2, 2])
    with col_srch:
        search = st.text_input("Search", placeholder="Name, email, or business…",
                               key="admin_search_input", label_visibility="collapsed")
    with col_filt:
        health_filter = st.selectbox("Health", ["All","Healthy","Growing","Dormant","New"],
                                     key="admin_health_filter", label_visibility="collapsed")
    with col_sort:
        sort_by = st.selectbox("Sort by", ["Latest signup","Last active","Health score","Posts"],
                               key="admin_sort", label_visibility="collapsed")

    with st.spinner("Loading subscribers..."):
        subscribers = adm.get_all_subscribers()

    # Apply filters
    if search:
        q = search.lower()
        subscribers = [s for s in subscribers
                       if q in s["name"].lower()
                       or q in s["email"].lower()
                       or q in (s.get("business_name") or "").lower()]
    if health_filter != "All":
        subscribers = [s for s in subscribers if s["health"]["status"] == health_filter]

    # Apply sort
    if sort_by == "Last active":
        subscribers.sort(key=lambda s: s.get("last_login") or s.get("created_at",""), reverse=True)
    elif sort_by == "Health score":
        subscribers.sort(key=lambda s: s["health"]["score"], reverse=True)
    elif sort_by == "Posts":
        subscribers.sort(key=lambda s: s["posts_total"], reverse=True)

    if not subscribers:
        st.info("No subscribers found.")
        return

    st.caption(f"Showing {len(subscribers)} subscriber{'s' if len(subscribers)!=1 else ''}")

    # Render in 2-column grid
    cols_per_row = 2
    for row_start in range(0, len(subscribers), cols_per_row):
        row_subs = subscribers[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row, gap="medium")
        for col_idx, sub in enumerate(row_subs):
            with cols[col_idx]:
                _render_subscriber_card(sub)


def _render_subscriber_card(sub: dict):
    """Render a single subscriber card in the admin grid."""
    from saas.models import get_model, PROVIDER_ICONS

    uid      = sub["id"]
    name     = sub.get("name", "Unknown")
    email    = sub.get("email", "")
    biz_name = sub.get("business_name") or sub.get("profile", {}) and sub["profile"].get("business_name") or "—"
    tier     = sub.get("tier", "free")
    h        = sub["health"]
    last_login = (sub.get("last_login") or sub.get("created_at",""))[:10]
    pref_m   = sub.get("preferred_model", "claude-sonnet-4-6")
    m_obj    = get_model(pref_m)
    m_icon   = PROVIDER_ICONS.get(m_obj.provider if m_obj else "", "⬡")
    m_name   = m_obj.name if m_obj else pref_m

    tier_colors = {"agency":"#A78BFA","growth":"#06B6D4","starter":"#F59E0B","free":"#64748B"}
    tier_color  = tier_colors.get(tier, "#64748B")
    initials    = (name.split()[0][0] + (name.split()[-1][0] if len(name.split())>1 else "")).upper()

    st.markdown(f"""
    <div class="sub-card">
      <div class="sub-card-top">
        <div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#7C3AED,#06B6D4);
                        display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;
                        color:white;flex-shrink:0;">{initials}</div>
            <div>
              <div class="sub-name">{name}</div>
              <div class="sub-email">{email}</div>
            </div>
          </div>
          <div style="font-size:11px;color:#94A3B8;margin-left:40px;">{biz_name}</div>
        </div>
        <div style="text-align:right;">
          <div class="health-pill" style="background:{h['color']}22;color:{h['color']};
               border:1px solid {h['color']}44;margin-bottom:4px;">{h['status']}</div>
          <div style="font-size:10px;color:{tier_color};font-weight:700;">{tier.upper()}</div>
        </div>
      </div>
      <div class="sub-stats">
        <div class="sub-stat">📝 {sub['posts_total']} posts</div>
        <div class="sub-stat">🎯 {sub['campaigns_total']} plans</div>
        <div class="sub-stat">🔗 {sub['platforms_count']} platforms</div>
        <div class="sub-stat">🗓 {last_login}</div>
      </div>
      <div style="margin-top:8px;font-size:11px;color:#475569;">
        {m_icon} {m_name}
        {"&nbsp;·&nbsp;Profile complete ✓" if sub.get('has_profile') else "&nbsp;·&nbsp;No profile yet"}
      </div>
      <div class="health-bar-bg">
        <div class="health-bar-fill" style="width:{h['score']}%;background:{h['color']};"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_view, col_email = st.columns(2)
    with col_view:
        if st.button(f"👁 View Account", key=f"view_{uid}", use_container_width=True, type="primary"):
            st.session_state.viewing_as = db.get_user_by_id(uid)
            go_to("dashboard")
    with col_email:
        if st.button(f"🔍 Drill In", key=f"drill_{uid}", use_container_width=True):
            tok = st.session_state.get("session_token", "")
            st.query_params["tab"] = "admin"
            st.query_params["sub"] = uid
            if tok:
                st.query_params["s"] = tok
            st.rerun()


def _render_subscriber_detail(user_id: str):
    """Full analytics drill-in for a single subscriber."""
    from saas import admin as adm

    detail = adm.subscriber_detail(user_id)
    if not detail:
        st.error("Subscriber not found.")
        return

    user    = detail["user"]
    profile = detail.get("profile")
    h       = detail["health"]

    # Back button
    if st.button("← Back to all subscribers", key="admin_back"):
        st.query_params.pop("sub", None)
        st.rerun()

    biz_name = (profile.get("business_name") if profile else None) or user.get("business_name") or user["name"]

    st.markdown(f"""
    <div class="plan-header">
      <div class="plan-title">{biz_name}</div>
      <div class="plan-meta">
        <span>👤 {user['name']}</span>
        <span>📧 {user['email']}</span>
        <span>💳 {detail.get('tier', 'free').upper()}</span>
        <span style="color:{h['color']};">⬤ {h['status']} ({h['score']}/100)</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Stats row
    a = detail.get("analytics_30d", {})
    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-box"><div class="metric-val">{detail['posts_total']}</div><div class="metric-lbl">Total Posts</div></div>
      <div class="metric-box"><div class="metric-val">{detail['campaigns_total']}</div><div class="metric-lbl">Campaigns</div></div>
      <div class="metric-box"><div class="metric-val">{len(detail.get('platforms',[]))}</div><div class="metric-lbl">Platforms</div></div>
      <div class="metric-box"><div class="metric-val">{int(a.get('total_reach',0)):,}</div><div class="metric-lbl">Reach (30d)</div></div>
      <div class="metric-box"><div class="metric-val">{int(a.get('total_likes',0)+a.get('total_comments',0)+a.get('total_shares',0)):,}</div><div class="metric-lbl">Engagements (30d)</div></div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns(2)

    with col_l:
        # Business profile
        st.markdown('<div class="sec-title">🏢 Business Profile</div>', unsafe_allow_html=True)
        if profile and profile.get("onboarding_complete"):
            for label, key in [("Industry","industry"),("Location","location"),
                                ("Budget","monthly_budget"),("Tone","tone"),
                                ("USP","usp"),("Model","preferred_model")]:
                val = profile.get(key)
                if val:
                    if key == "monthly_budget":
                        val = f"${float(val):,.0f}/mo"
                    st.markdown(f"""
                    <div style="display:flex;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
                      <span style="font-size:11px;color:#64748B;width:80px;">{label}</span>
                      <span style="font-size:12px;color:#CBD5E1;">{val}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Onboarding not complete.")

        # Post status
        st.markdown('<div class="sec-title">📝 Post Status</div>', unsafe_allow_html=True)
        for status, cnt in detail.get("post_status", {}).items():
            color = {"published":"#22C55E","scheduled":"#F59E0B","draft":"#64748B","failed":"#EF4444"}.get(status,"#475569")
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:5px 0;
                        border-bottom:1px solid rgba(255,255,255,0.04);">
              <span style="font-size:12px;color:{color};">● {status.title()}</span>
              <span style="font-size:14px;font-weight:700;color:#E2E8F0;">{cnt}</span>
            </div>
            """, unsafe_allow_html=True)

    with col_r:
        # Campaigns
        st.markdown('<div class="sec-title">🎯 Recent Campaigns</div>', unsafe_allow_html=True)
        for camp in detail.get("recent_campaigns", [])[:4]:
            c_color = {"draft":"#F59E0B","approved":"#22C55E","active":"#06B6D4"}.get(camp["status"],"#64748B")
            st.markdown(f"""
            <div class="card" style="padding:10px 14px;margin-bottom:6px;border-left:3px solid {c_color};">
              <div style="font-size:12px;font-weight:700;color:#E2E8F0;">{camp['title'][:50]}</div>
              <div style="font-size:11px;color:#64748B;">{camp.get('campaign_type','30_day')} · {camp['created_at'][:10]}</div>
            </div>
            """, unsafe_allow_html=True)

        # Health reasons
        st.markdown('<div class="sec-title">🔍 Health Signals</div>', unsafe_allow_html=True)
        for reason in h.get("reasons", []):
            st.markdown(f'<div style="font-size:12px;color:#94A3B8;padding:4px 0;">• {reason}</div>',
                        unsafe_allow_html=True)

    # Owner action: Enter subscriber's view
    st.markdown("")
    if st.button(f"👁 Enter {biz_name}'s Dashboard", type="primary", use_container_width=False):
        st.session_state.viewing_as = db.get_user_by_id(user_id)
        go_to("dashboard")


# ══════════════════════════════════════════════════════════════════════════════
# ONBOARDING PAGE
# ══════════════════════════════════════════════════════════════════════════════
def render_onboarding():
    from saas import onboarding_agent
    import saas.db as _db

    user = st.session_state.user
    uid  = user["id"]

    st.markdown("""
    <div class="onboard-hero">
      <div style="font-size:48px;margin-bottom:8px;">🤖</div>
      <div style="font-size:26px;font-weight:800;color:#E2E8F0;margin-bottom:6px;">
        Meet Alex, your marketing consultant
      </div>
      <div style="font-size:14px;color:#64748B;max-width:420px;margin:0 auto;">
        I'll ask you a few quick questions about your business so I can build
        a personalised advertising plan tailored specifically to you.
      </div>
    </div>
    """, unsafe_allow_html=True)

    history = st.session_state.onboarding_history

    # Boot the conversation with the agent's opener if fresh
    if not history:
        with st.spinner("Starting conversation..."):
            opener = onboarding_agent.start_conversation()
        history = [{"role": "assistant", "content": opener}]
        st.session_state.onboarding_history = history

    # Render chat history
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    for msg in history:
        is_user = msg["role"] == "user"
        bubble_cls = "chat-bubble-user" if is_user else "chat-bubble-ai"
        row_cls    = "chat-msg-user"    if is_user else "chat-msg"
        avatar     = "👤" if is_user else "🤖"
        # Strip the JSON block from display
        display_text = msg["content"]
        import re as _re
        display_text = _re.sub(r'```json_profile.*?```', '', display_text, flags=_re.DOTALL).strip()
        if display_text:
            st.markdown(f"""
            <div class="{row_cls} chat-msg">
              <div class="chat-avatar">{avatar}</div>
              <div class="chat-bubble {bubble_cls}">{display_text}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Check if profile was already extracted
    for msg in history:
        if msg["role"] == "assistant":
            profile = onboarding_agent._extract_profile(msg["content"])
            if profile and profile.get("ready_for_plan"):
                _save_profile_and_redirect(uid, profile, history)
                return

    # Input box
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        user_input = st.text_input(
            "Your answer",
            placeholder="Type your answer here...",
            key="onboard_input",
            label_visibility="collapsed"
        )
    with col_btn:
        send = st.button("Send →", type="primary", use_container_width=True)

    if send and user_input.strip():
        user_msg = user_input.strip()
        history.append({"role": "user", "content": user_msg})

        # Build messages list for Claude (exclude the opener if it was just bootstrap)
        messages_for_api = [m for m in history if not (
            m["role"] == "user" and
            m["content"] == "Hi, I just signed up and I'm ready to set up my business profile."
        )]

        with st.spinner("Alex is thinking..."):
            reply, profile = onboarding_agent.chat(
                messages_for_api[:-1],  # history before latest user msg
                user_msg
            )

        history.append({"role": "assistant", "content": reply})
        st.session_state.onboarding_history = history

        if profile and profile.get("ready_for_plan"):
            _save_profile_and_redirect(uid, profile, history)
            return

        st.rerun()

    # Skip option (for returning users or users who want to proceed manually)
    st.markdown("")
    col_skip = st.columns([3, 1, 3])[1]
    with col_skip:
        if st.button("Skip for now", use_container_width=True):
            # Force extract from whatever we have
            if len(history) > 4:
                with st.spinner("Saving what we know..."):
                    profile = onboarding_agent.build_profile_from_answers(history)
                if profile:
                    _save_profile_and_redirect(uid, profile, history)
                    return
            go_to("dashboard")


def _save_profile_and_redirect(uid: str, profile: dict, history: list):
    import json as _json
    import saas.db as _db

    services = profile.get("services", [])
    target   = profile.get("target_audience", {})
    goals    = profile.get("goals", {})
    competitors = profile.get("competitors", [])
    channels = profile.get("social_channels", [])

    _db.upsert_business_profile(
        uid,
        business_name=profile.get("business_name", ""),
        industry=profile.get("industry", ""),
        business_type=profile.get("business_type", ""),
        location=profile.get("location", ""),
        website=profile.get("website", ""),
        services=_json.dumps(services) if isinstance(services, (list, dict)) else str(services),
        target_audience=_json.dumps(target) if isinstance(target, (list, dict)) else str(target),
        goals=_json.dumps(goals) if isinstance(goals, (list, dict)) else str(goals),
        competitors=_json.dumps(competitors) if isinstance(competitors, (list, dict)) else str(competitors),
        social_channels=_json.dumps(channels) if isinstance(channels, (list, dict)) else str(channels),
        usp=profile.get("usp", ""),
        tone=profile.get("tone", "professional"),
        monthly_budget=float(profile.get("monthly_budget") or 500),
        onboarding_complete=1,
        raw_conversation=_json.dumps(history),
    )
    # Also update the user's business_name in users table
    _db.update_user(uid, business_name=profile.get("business_name", ""))
    st.session_state.onboarding_done = True
    st.session_state.onboarding_history = []

    st.success("✅ Business profile saved! Building your personalised ad plan now...")
    import time; time.sleep(1)
    go_to("adplan")


# ══════════════════════════════════════════════════════════════════════════════
# AD PLAN PAGE — Visual Campaign Board
# ══════════════════════════════════════════════════════════════════════════════
def render_adplan():
    import json as _json
    import saas.db as _db
    from saas import ad_plan_engine, market_intelligence

    user = st.session_state.user
    uid  = user["id"]

    profile = _db.get_business_profile(uid)

    # ── No profile yet: nudge to onboarding ──
    if not profile or not profile.get("onboarding_complete"):
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
          <div style="font-size:56px;margin-bottom:16px;">🎯</div>
          <div style="font-size:24px;font-weight:800;color:#E2E8F0;margin-bottom:8px;">
            Your Ad Plan Awaits
          </div>
          <div style="font-size:14px;color:#64748B;max-width:400px;margin:0 auto 24px;">
            First, let Alex learn about your business. It only takes 3-5 minutes and unlocks
            a fully personalised advertising plan built just for you.
          </div>
        </div>
        """, unsafe_allow_html=True)
        col = st.columns([1, 2, 1])[1]
        with col:
            if st.button("🚀 Set Up My Business Profile", type="primary", use_container_width=True):
                go_to("onboarding")
        return

    biz_name = profile.get("business_name") or user.get("business_name") or "Your Business"
    budget   = float(profile.get("monthly_budget") or 500)

    # ── Campaign selector / generator ──
    campaigns = _db.get_campaigns(uid)

    st.markdown(f'<div class="page-title">🎯 Advertising Plan — {biz_name}</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Your AI-generated campaign board. Review, tweak, and approve.</div>',
                unsafe_allow_html=True)

    # Header action row
    col_type, col_gen, col_sel = st.columns([2, 2, 3])
    with col_type:
        camp_type = st.selectbox(
            "Plan duration",
            ["30_day", "60_day", "90_day"],
            format_func=lambda x: {"30_day": "30 Days", "60_day": "60 Days", "90_day": "90 Days"}[x],
            label_visibility="collapsed"
        )
    with col_gen:
        gen_btn = st.button("⚡ Generate New Plan", type="primary", use_container_width=True)
    with col_sel:
        if campaigns:
            camp_labels = {c["id"]: f"{c['title']} ({c['status'].upper()}) — {c['created_at'][:10]}"
                           for c in campaigns}
            camp_labels["__new__"] = "→ Select a campaign…"
            selected_id = st.selectbox(
                "Saved plans",
                options=["__new__"] + list(camp_labels.keys())[:-1],
                format_func=lambda x: camp_labels.get(x, x),
                label_visibility="collapsed"
            )
            if selected_id != "__new__":
                st.session_state.active_campaign_id = selected_id

    # ── Generate plan ──
    if gen_btn:
        with st.spinner(f"🔍 Researching the {profile.get('industry', 'your')} market..."):
            research = market_intelligence.research_business(profile)

        days_map = {"30_day": "30-day", "60_day": "60-day", "90_day": "90-day"}
        with st.spinner(f"🤖 Building your {days_map[camp_type]} ad plan..."):
            plan = ad_plan_engine.generate_plan(profile, research, camp_type)

        if plan:
            campaign = _db.create_campaign(
                uid,
                title=plan.get("campaign_title", f"{biz_name} — Campaign"),
                description=plan.get("campaign_summary", ""),
                campaign_type=camp_type,
                start_date=plan.get("start_date"),
                end_date=plan.get("end_date"),
                total_budget=plan.get("total_budget", budget),
                channels=_json.dumps(plan.get("channels", [])),
                timeline=_json.dumps(plan.get("content_calendar", [])),
                goals=_json.dumps(plan.get("goals", {})),
                ai_rationale=plan.get("ai_rationale", ""),
                market_research=research[:3000] if research else "",
                status="draft"
            )
            # Store individual content items
            items = []
            for item in plan.get("content_calendar", []):
                items.append({
                    "platform": item.get("platform", "facebook"),
                    "content_type": item.get("content_type", "post"),
                    "title": item.get("title", ""),
                    "content": item.get("content_brief", ""),
                    "image_prompt": item.get("image_concept", ""),
                    "scheduled_date": item.get("date", ""),
                    "budget": item.get("budget", 0),
                    "status": "pending"
                })
            if items:
                _db.create_campaign_items(campaign["id"], uid, items)
            st.session_state.active_campaign_id = campaign["id"]
            st.rerun()
        else:
            st.error("Plan generation failed — please check your API keys in Settings.")

    # ── Display active campaign ──
    active_id = st.session_state.get("active_campaign_id")
    if not active_id and campaigns:
        active_id = campaigns[0]["id"]
        st.session_state.active_campaign_id = active_id

    if not active_id:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;opacity:0.6;">
          <div style="font-size:48px;margin-bottom:12px;">📋</div>
          <div style="font-size:16px;color:#64748B;">
            No campaign yet — click "Generate New Plan" to create your first one.
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    campaign = _db.get_campaign(active_id)
    if not campaign:
        return

    # Parse stored JSON fields
    try:
        channels  = _json.loads(campaign.get("channels") or "[]")
        cal_items = _json.loads(campaign.get("timeline") or "[]")
        goals     = _json.loads(campaign.get("goals")    or "{}")
    except Exception:
        channels = []; cal_items = []; goals = {}

    # ── Plan header ──
    status_color = {"draft": "#F59E0B", "approved": "#22C55E",
                    "active": "#06B6D4", "completed": "#A78BFA"}.get(campaign["status"], "#64748B")
    st.markdown(f"""
    <div class="plan-header">
      <div class="plan-title">{campaign['title']}</div>
      <div class="plan-meta">
        <span>📅 {campaign.get('start_date','')[:10]} → {campaign.get('end_date','')[:10]}</span>
        <span>💰 ${float(campaign.get('total_budget') or 0):,.0f} total budget</span>
        <span style="color:{status_color};">⬤ {campaign['status'].upper()}</span>
      </div>
      <div style="margin-top:12px;font-size:13px;color:#94A3B8;font-style:italic;">
        {campaign.get('description','')[:200]}
      </div>
    </div>
    """, unsafe_allow_html=True)

    if campaign.get("ai_rationale"):
        st.markdown(f"""
        <div class="card" style="border-left:3px solid #A78BFA;">
          <div style="font-size:11px;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">
            🧠 Why This Plan Works
          </div>
          <div style="font-size:13px;color:#CBD5E1;">{campaign['ai_rationale']}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Goals & KPIs ──
    st.markdown('<div class="sec-title">🎯 Goals & Expected Outcomes</div>', unsafe_allow_html=True)
    g_cols = st.columns(4)
    kpi_data = [
        ("Primary Goal", goals.get("primary", "Generate leads"), "🏆"),
        ("Expected Reach", f"{int(goals.get('expected_reach', 0)):,}", "👁️"),
        ("Expected Leads", str(goals.get("expected_leads", 0)), "🎯"),
        ("Engagement Rate", goals.get("expected_engagement_rate", "3-5%"), "💬"),
    ]
    for i, (label, val, icon) in enumerate(kpi_data):
        with g_cols[i]:
            st.markdown(f"""
            <div class="metric-box">
              <div style="font-size:22px;margin-bottom:6px;">{icon}</div>
              <div class="metric-val" style="font-size:16px;">{val}</div>
              <div class="metric-lbl">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Channel breakdown ──
    st.markdown('<div class="sec-title">📡 Channel Strategy</div>', unsafe_allow_html=True)

    if channels:
        # Plotly budget allocation pie chart
        try:
            import plotly.graph_objects as go
            import plotly.express as px

            PLATFORM_COLORS = {
                "facebook": "#1877F2", "instagram": "#E1306C",
                "linkedin": "#0A66C2", "tiktok": "#000000",
                "twitter": "#1DA1F2", "google_ads": "#EA4335",
            }

            ch_names   = [c.get("platform", "other").title().replace("_", " ") for c in channels]
            ch_budgets = [float(c.get("budget_amount", 0)) for c in channels]
            ch_colors  = [PLATFORM_COLORS.get(c.get("platform", ""), "#7C3AED") for c in channels]

            fig = go.Figure(data=[go.Pie(
                labels=ch_names,
                values=ch_budgets,
                marker=dict(colors=ch_colors, line=dict(color="#080C18", width=3)),
                textinfo="label+percent",
                textfont=dict(color="#E2E8F0", size=12),
                hole=0.45,
            )])
            fig.update_layout(
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=20, l=20, r=20),
                height=260,
                font=dict(color="#E2E8F0"),
            )
            ch_col_chart, ch_col_cards = st.columns([2, 3])
            with ch_col_chart:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            with ch_col_cards:
                for ch in channels:
                    plat  = ch.get("platform", "")
                    icon  = {"facebook": "📘", "instagram": "📸", "linkedin": "💼",
                             "tiktok": "🎵", "twitter": "🐦", "google_ads": "🔍"}.get(plat, "🌐")
                    st.markdown(f"""
                    <div class="channel-card" style="margin-bottom:10px;">
                      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                        <span style="font-size:22px;">{icon}</span>
                        <span class="channel-name">{plat.replace('_',' ').title()}</span>
                        <span style="font-size:11px;color:#64748B;margin-left:auto;">
                          {ch.get('posts_per_week',0)} posts/week
                        </span>
                      </div>
                      <div class="channel-budget">${float(ch.get('budget_amount',0)):,.0f}/mo</div>
                      <div class="channel-stat">{ch.get('why_this_platform','')[:100]}</div>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception:
            # Plotly not available — show plain cards
            n_cols = min(len(channels), 3)
            ch_cols = st.columns(n_cols)
            for i, ch in enumerate(channels):
                plat = ch.get("platform", "")
                icon = {"facebook": "📘", "instagram": "📸", "linkedin": "💼",
                        "tiktok": "🎵", "twitter": "🐦", "google_ads": "🔍"}.get(plat, "🌐")
                with ch_cols[i % n_cols]:
                    st.markdown(f"""
                    <div class="channel-card">
                      <div class="channel-icon">{icon}</div>
                      <div class="channel-name">{plat.replace('_',' ').title()}</div>
                      <div class="channel-budget">${float(ch.get('budget_amount',0)):,.0f}</div>
                      <div class="channel-stat">{ch.get('budget_percent',0)}% of budget · {ch.get('posts_per_week',0)} posts/wk</div>
                    </div>
                    """, unsafe_allow_html=True)

    # ── Content calendar ──
    st.markdown('<div class="sec-title">📅 Content Calendar</div>', unsafe_allow_html=True)

    if cal_items:
        db_items = _db.get_campaign_items(active_id)
        if not db_items:
            db_items = cal_items  # use generated data if DB items not yet written

        # Group by platform for tab display
        platforms_in_plan = sorted(set(
            item.get("platform", "facebook") for item in (db_items or cal_items)
        ))
        plat_tabs = st.tabs([p.replace("_", " ").title() for p in platforms_in_plan] + ["All"])

        for tab_idx, tab_plat in enumerate(platforms_in_plan + ["all"]):
            with plat_tabs[tab_idx]:
                filtered = [
                    item for item in (db_items or cal_items)
                    if tab_plat == "all" or item.get("platform") == tab_plat
                ]
                for item in filtered[:15]:  # cap at 15 per tab for performance
                    date_str = (item.get("scheduled_date") or item.get("date") or "")[:10]
                    ctype    = item.get("content_type", "post")
                    title    = item.get("title") or item.get("content_type", "Post")
                    brief    = item.get("content") or item.get("content_brief", "")
                    plat     = item.get("platform", "")
                    icon     = {"facebook": "📘", "instagram": "📸", "linkedin": "💼",
                                "tiktok": "🎵", "twitter": "🐦", "google_ads": "🔍"}.get(plat, "🌐")
                    type_color = {"ad": "#EF4444", "story": "#F59E0B", "video": "#8B5CF6",
                                  "google_ad": "#EA4335"}.get(ctype, "#7C3AED")
                    st.markdown(f"""
                    <div class="content-item">
                      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                        <span style="font-size:10px;color:#475569;">{date_str}</span>
                        <span class="content-platform-badge" style="border-color:{type_color};color:{type_color};">
                          {icon} {ctype.upper()}
                        </span>
                      </div>
                      <div class="content-title">{title}</div>
                      <div class="content-brief">{brief[:150]}</div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("No content calendar items in this plan.")

    # ── Quick wins ──
    quick_wins_raw = campaign.get("ai_rationale", "")
    st.markdown('<div class="sec-title">⚡ Quick Wins — Do These First</div>', unsafe_allow_html=True)
    quick_wins_placeholder = [
        ("Optimise your social media profiles", "HIGH", "Complete bio, contact info, and a clear call to action on every platform"),
        ("Post your first piece of content today", "HIGH", "Consistency signals are more important than perfection on day one"),
        ("Set up tracking — Google Analytics + Meta Pixel", "MEDIUM", "Without tracking, you can't optimise. Install both before spending on ads"),
    ]
    for action, impact, desc in quick_wins_placeholder:
        impact_color = {"HIGH": "#EF4444", "MEDIUM": "#F59E0B", "LOW": "#22C55E"}.get(impact, "#64748B")
        st.markdown(f"""
        <div class="card" style="border-left:3px solid {impact_color};">
          <div style="display:flex;gap:10px;align-items:flex-start;">
            <div style="background:{impact_color}22;color:{impact_color};font-size:10px;
                        font-weight:800;padding:3px 8px;border-radius:6px;white-space:nowrap;
                        margin-top:2px;">{impact}</div>
            <div>
              <div style="font-size:13px;font-weight:700;color:#E2E8F0;margin-bottom:3px;">{action}</div>
              <div style="font-size:12px;color:#64748B;">{desc}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Approve / Feedback section ──
    st.markdown('<div class="sec-title">✅ Review & Approve</div>', unsafe_allow_html=True)
    if campaign["status"] == "approved":
        st.success("🎉 This campaign is approved and ready to execute!")
        if st.button("▶️ Execute This Campaign", type="primary"):
            st.info("Campaign execution — connect your platform APIs in Settings to enable automated posting.")
    else:
        st.markdown("""
        <div class="card">
          <div style="font-size:13px;color:#94A3B8;margin-bottom:12px;">
            Happy with this plan? Approve it to lock it in, or request changes below.
          </div>
        </div>
        """, unsafe_allow_html=True)

        col_approve, col_regen = st.columns(2)
        with col_approve:
            if st.button("✅ Approve This Plan", type="primary", use_container_width=True):
                _db.update_campaign(active_id, status="approved",
                                    approved_at=datetime.now(timezone.utc).isoformat())
                st.success("🎉 Plan approved!")
                st.rerun()

        with col_regen:
            with st.expander("💬 Request Changes"):
                feedback = st.text_area(
                    "What would you like to change?",
                    placeholder="e.g. 'Add more LinkedIn posts', 'Focus more on Instagram Reels', "
                                "'Increase Google Ads budget to 40%', 'Make the tone more casual'",
                    height=100,
                    key="plan_feedback"
                )
                if st.button("🔄 Regenerate with Changes", type="primary", use_container_width=True):
                    if feedback.strip():
                        with st.spinner("Revising your plan..."):
                            try:
                                import json as _j
                                original_plan_dict = {
                                    "campaign_title": campaign.get("title"),
                                    "channels": _j.loads(campaign.get("channels") or "[]"),
                                    "content_calendar": _j.loads(campaign.get("timeline") or "[]"),
                                    "goals": _j.loads(campaign.get("goals") or "{}"),
                                    "ai_rationale": campaign.get("ai_rationale", ""),
                                }
                                revised = ad_plan_engine.regenerate_plan_with_feedback(
                                    original_plan_dict, feedback, profile
                                )
                                if revised:
                                    _db.update_campaign(
                                        active_id,
                                        title=revised.get("campaign_title", campaign["title"]),
                                        description=revised.get("campaign_summary", ""),
                                        channels=_j.dumps(revised.get("channels", [])),
                                        timeline=_j.dumps(revised.get("content_calendar", [])),
                                        goals=_j.dumps(revised.get("goals", {})),
                                        ai_rationale=revised.get("ai_rationale", ""),
                                        user_feedback=feedback,
                                        status="draft"
                                    )
                                    st.success("Plan updated! Refreshing...")
                                    st.rerun()
                                else:
                                    st.error("Revision failed — please try again.")
                            except Exception as e:
                                st.error(f"Error: {e}")
                    else:
                        st.warning("Please enter your feedback first.")


# ══════════════════════════════════════════════════════════════════════════════
# AI CHAT PAGE — Always-On Marketing Assistant
# ══════════════════════════════════════════════════════════════════════════════
def render_chat():
    import json as _json
    import saas.db as _db

    user = st.session_state.user
    uid  = user["id"]
    profile = _db.get_business_profile(uid)

    biz_name = "your business"
    if profile:
        biz_name = profile.get("business_name") or biz_name

    st.markdown(f'<div class="page-title">🤖 AI Marketing Assistant</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">Your dedicated marketing expert for {biz_name}. '
                f'Ask anything — strategy, content ideas, ad copy, or competitor analysis.</div>',
                unsafe_allow_html=True)

    ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    if not ANTHROPIC_KEY:
        st.warning("⚠️ Add your ANTHROPIC_API_KEY in Settings → API Keys to activate the AI chat.")
        return

    chat_history = st.session_state.chat_history

    # Build the system prompt with business context
    if profile:
        try:
            target = _json.loads(profile.get("target_audience") or "{}")
            services = _json.loads(profile.get("services") or "[]")
            goals = _json.loads(profile.get("goals") or "{}")
        except Exception:
            target = {}; services = []; goals = {}

        biz_context = f"""Business: {profile.get('business_name', 'Unknown')}
Industry: {profile.get('industry', 'Unknown')}
Location: {profile.get('location', 'Unknown')}
Services: {', '.join(str(s) for s in services[:5]) if services else 'Not specified'}
Target Audience: {target.get('description', 'Not specified')}
Primary Goal: {goals.get('primary', 'Generate leads')}
Monthly Budget: ${float(profile.get('monthly_budget') or 0):,.0f} AUD
Brand Tone: {profile.get('tone', 'professional')}
USP: {profile.get('usp', 'Not specified')}"""
    else:
        biz_context = "No business profile set up yet. Ask the user about their business first."

    system_prompt = f"""You are Alex, a world-class marketing strategist and advertising expert.
You are the dedicated marketing consultant for this specific business.

YOUR CLIENT'S BUSINESS PROFILE:
{biz_context}

YOUR ROLE:
- Answer marketing questions with expertise and specificity
- Generate post copy, ad headlines, and creative ideas on request
- Suggest the best advertising strategies for this specific business
- Analyse marketing situations and provide actionable advice
- Be aware of current (2025) platform algorithms, ad formats, and best practices
- Always tailor advice to this specific business, industry, and budget

YOUR STYLE:
- Confident, specific, and actionable — no vague advice
- Use data and benchmarks when relevant
- Format responses clearly with bullet points or numbered lists where appropriate
- Keep responses concise but complete"""

    # Display chat history
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    if not chat_history:
        # Welcome message
        st.markdown(f"""
        <div class="chat-msg">
          <div class="chat-avatar">🤖</div>
          <div class="chat-bubble chat-bubble-ai">
            <strong>Hey! I'm Alex, your marketing consultant.</strong><br><br>
            I'm fully briefed on {biz_name} and ready to help. You can ask me things like:<br><br>
            • "Write me 3 Facebook post ideas for this week"<br>
            • "What should my Google Ads strategy be?"<br>
            • "How do I get more leads on Instagram?"<br>
            • "Write an ad headline for [specific service]"<br>
            • "What's my best move with a ${float(profile.get('monthly_budget') or 500):,.0f}/month budget?"
          </div>
        </div>
        """, unsafe_allow_html=True)

    for msg in chat_history:
        is_user    = msg["role"] == "user"
        bubble_cls = "chat-bubble-user" if is_user else "chat-bubble-ai"
        row_cls    = "chat-msg-user chat-msg" if is_user else "chat-msg"
        avatar     = "👤" if is_user else "🤖"
        content    = msg["content"].replace("\n", "<br>")
        st.markdown(f"""
        <div class="{row_cls}">
          <div class="chat-avatar">{avatar}</div>
          <div class="chat-bubble {bubble_cls}">{content}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Suggested prompts (shown when no history)
    if not chat_history:
        st.markdown("")
        st.markdown("**Quick questions to get started:**")
        suggestions = [
            "Write 3 social media post ideas for this week",
            f"What's the best advertising strategy for {biz_name}?",
            "Write a Google Ad headline and description for my main service",
            "What content performs best on Facebook for my industry?",
        ]
        sugg_cols = st.columns(2)
        for i, sugg in enumerate(suggestions):
            with sugg_cols[i % 2]:
                if st.button(sugg, key=f"sugg_{i}", use_container_width=True):
                    st.session_state["chat_prefill"] = sugg
                    st.rerun()

    # Input
    prefill = st.session_state.pop("chat_prefill", "") if "chat_prefill" in st.session_state else ""
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        user_input = st.text_input(
            "Ask Alex anything about marketing…",
            value=prefill,
            placeholder="e.g. 'Write 3 Instagram captions for [topic]'",
            key="chat_input",
            label_visibility="collapsed"
        )
    with col_btn:
        send_btn = st.button("Send →", type="primary", use_container_width=True)

    if send_btn and user_input.strip():
        import anthropic as _ant
        client = _ant.Anthropic(api_key=ANTHROPIC_KEY)

        # Keep history manageable
        working_history = list(chat_history[-18:]) if len(chat_history) > 18 else list(chat_history)
        working_history.append({"role": "user", "content": user_input.strip()})

        with st.spinner("Alex is thinking..."):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=system_prompt,
                messages=working_history,
            )
            reply = response.content[0].text

        chat_history.append({"role": "user", "content": user_input.strip()})
        chat_history.append({"role": "assistant", "content": reply})
        st.session_state.chat_history = chat_history
        st.rerun()

    # Clear button
    if chat_history:
        col_clear = st.columns([5, 1])[1]
        with col_clear:
            if st.button("Clear", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ROUTING
# ══════════════════════════════════════════════════════════════════════════════
# Handle logout URL action
if st.query_params.get("action") == "logout":
    _do_logout()

if st.session_state.user is None:
    render_auth()
else:
    # Check if new user needs onboarding (skip for existing users with profiles)
    _uid = st.session_state.user["id"]
    _tab = get_tab()
    if _tab not in ("onboarding", "settings") and not st.session_state.onboarding_done:
        import saas.db as _check_db
        _profile = _check_db.get_business_profile(_uid)
        if _profile and _profile.get("onboarding_complete"):
            st.session_state.onboarding_done = True

    render_topbar()
    render_impersonation_banner()
    render_floating_agent()
    # Content wrapper
    st.markdown('<div class="sa-page">', unsafe_allow_html=True)

    tab = get_tab()
    if   tab == "admin":       render_admin()
    elif tab == "dashboard":   render_dashboard()
    elif tab == "onboarding":  render_onboarding()
    elif tab == "adplan":      render_adplan()
    elif tab == "chat":        render_chat()
    elif tab == "platforms":   render_platforms()
    elif tab == "compose":     render_compose()
    elif tab == "posts":       render_posts()
    elif tab == "analytics":   render_analytics()
    elif tab == "strategy":    render_strategy()
    elif tab == "settings":    render_settings()
    else:
        if is_owner_session() and not is_impersonating():
            render_admin()
        else:
            render_dashboard()

    st.markdown('</div>', unsafe_allow_html=True)
