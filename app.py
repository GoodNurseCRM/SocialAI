import streamlit as st
import asyncio, uuid, os, re, sqlite3, json as _json
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="Good Nurse — Marketing Agent",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide Streamlit chrome completely */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { display: none !important; }

/* Remove default page padding & cap width */
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── Sticky top wrapper ── */
.gn-topbar {
    position: sticky;
    top: 0;
    z-index: 999;
}

/* ── Header ── */
.gn-header {
    background: linear-gradient(120deg, #0D47A1 0%, #1565C0 55%, #00838F 100%);
    padding: 20px 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.gn-logo-wrap { display: flex; align-items: center; gap: 14px; }
.gn-logo { font-size: 40px; line-height: 1; }
.gn-name { font-size: 24px; font-weight: 800; color: #fff; letter-spacing: -0.3px; line-height: 1.1; }
.gn-tagline { font-size: 11px; color: rgba(255,255,255,0.75); letter-spacing: 0.8px; text-transform: uppercase; margin-top: 2px; }
.gn-stats { display: flex; gap: 32px; }
.gn-stat { text-align: center; color: white; }
.gn-stat-num { font-size: 26px; font-weight: 800; line-height: 1; }
.gn-stat-lbl { font-size: 10px; opacity: 0.75; text-transform: uppercase; letter-spacing: 0.5px; }

/* ── Tab nav bar ── */
.gn-nav {
    background: #ffffff;
    border-bottom: 2px solid #E3E8F4;
    padding: 0 36px;
    display: flex;
    gap: 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    flex-wrap: wrap;
}
.gn-nav-item {
    padding: 14px 20px;
    font-size: 13px;
    font-weight: 600;
    color: #78909C;
    text-decoration: none !important;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    transition: color 0.15s;
    white-space: nowrap;
}
.gn-nav-item:hover {
    color: #1565C0;
    text-decoration: none !important;
}
.gn-nav-active {
    color: #1565C0 !important;
    border-bottom-color: #1565C0 !important;
}

/* ── Page content area — padding via Streamlit container ── */
section[data-testid="stMain"] .block-container {
    padding: 32px 40px 40px !important;
    background: #F0F4F8 !important;
}

/* ── Section headings ── */
.page-title {
    font-size: 22px;
    font-weight: 800;
    color: #1A1A2E;
    margin: 0 0 4px;
    line-height: 1.2;
}
.page-sub {
    font-size: 13px;
    color: #90A4AE;
    margin: 0 0 28px;
    line-height: 1.5;
}
.section-title {
    font-size: 15px;
    font-weight: 700;
    color: #37474F;
    margin: 24px 0 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #E3E8F4;
}

/* ── Tile cards ── */
.tile {
    background: #ffffff;
    border-radius: 16px;
    padding: 26px 24px 20px;
    box-shadow: 0 2px 14px rgba(0,0,0,0.07);
    border-top: 5px solid #90A4AE;
    min-height: 185px;
    display: flex;
    flex-direction: column;
    gap: 5px;
    margin-bottom: 6px;
}
.tile-strategy { border-top-color: #7C3AED; }
.tile-leads    { border-top-color: #00838F; }
.tile-ads      { border-top-color: #1565C0; }
.tile-content  { border-top-color: #E65100; }
.tile-network  { border-top-color: #2E7D32; }
.tile-chat     { border-top-color: #AD1457; }

.tile-icon  { font-size: 38px; line-height: 1; margin-bottom: 2px; }
.tile-title { font-size: 17px; font-weight: 800; color: #1A1A2E; }
.tile-desc  { font-size: 12px; color: #78909C; line-height: 1.55; flex: 1; }
.tile-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 20px;
    width: fit-content;
    margin-top: 8px;
}
.badge-alert   { background: #FFF3E0; color: #E65100; }
.badge-success { background: #E8F5E9; color: #2E7D32; }
.badge-neutral { background: #ECEFF1; color: #78909C; }

/* ── White content cards ── */
.card {
    background: #ffffff;
    border-radius: 14px;
    padding: 22px 24px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    margin-bottom: 16px;
}
.card-title { font-size: 15px; font-weight: 700; color: #1A1A2E; margin-bottom: 4px; }
.card-sub   { font-size: 12px; color: #90A4AE; margin-bottom: 14px; }

/* ── Approval cards ── */
.appr-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    border-left: 5px solid #42A5F5;
    margin-bottom: 14px;
}
.appr-label { font-size: 11px; font-weight: 700; text-transform: uppercase; color: #1976D2; letter-spacing: 0.6px; margin-bottom: 10px; }
.post-quote { background: #F8FAFB; border-left: 3px solid #90CAF9; padding: 10px 14px; border-radius: 0 8px 8px 0; font-size: 13px; color: #546E7A; font-style: italic; margin: 8px 0; }
.draft-box  { background: #F1F8E9; border-left: 3px solid #81C784; padding: 10px 14px; border-radius: 0 8px 8px 0; font-size: 13px; color: #33691E; margin: 8px 0; }

/* ── Suggestion cards ── */
.sugg {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    margin-bottom: 14px;
    border-left: 5px solid #90A4AE;
}
.sugg-HIGH   { border-left-color: #D32F2F; }
.sugg-MEDIUM { border-left-color: #F57C00; }
.sugg-LOW    { border-left-color: #388E3C; }
.sugg-title  { font-size: 16px; font-weight: 800; color: #1A1A2E; }
.sugg-meta   { font-size: 11px; color: #90A4AE; margin: 4px 0 10px; }
.tag { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; margin-right: 6px; }
.tag-high   { background: #FFEBEE; color: #C62828; }
.tag-med    { background: #FFF3E0; color: #E65100; }
.tag-low    { background: #E8F5E9; color: #2E7D32; }
.tag-auto   { background: #EDE7F6; color: #4527A0; }
.tag-type   { background: #E3F2FD; color: #1565C0; }

/* ── Metrics ── */
.metric-row { display: flex; gap: 14px; margin-bottom: 24px; flex-wrap: wrap; }
.metric-box {
    background: white; border-radius: 12px; padding: 16px 20px;
    flex: 1; min-width: 120px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center;
}
.metric-val   { font-size: 26px; font-weight: 800; color: #1565C0; }
.metric-label { font-size: 11px; color: #90A4AE; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }

/* ── Setup steps ── */
.step-card {
    background: white; border-radius: 12px; padding: 16px 20px;
    border-left: 5px solid #FFC107; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 12px;
}
.step-num { font-size: 20px; font-weight: 800; color: #F57C00; }

/* ── Streamlit button polish ── */
div[data-testid="stButton"] > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: #1565C0 !important;
    border: none !important;
    color: white !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #0D47A1 !important;
    box-shadow: 0 4px 14px rgba(21,101,192,0.3) !important;
    transform: translateY(-1px) !important;
}

/* ── Streamlit default padding inside content ── */
section[data-testid="stMain"] > div {
    padding-top: 0 !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
def _init():
    for k, v in {
        "brain": None, "messages": [], "pending": {},
        "session_status": {"LinkedIn": None, "Facebook": None, "Instagram": None},
        "ads_proposal": None, "ads_budgets": {"direct": 30.0, "referral": 20.0},
        "ads_campaigns": [],
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if st.session_state.brain is None:
        from brain import AgentBrain
        st.session_state.brain = AgentBrain()
_init()

PLATFORM_SESSIONS = {
    "LinkedIn":  {"url": "https://www.linkedin.com/feed/",  "profile": "./browser_profiles/linkedin"},
    "Facebook":  {"url": "https://www.facebook.com/",       "profile": "./browser_profiles/facebook"},
    "Instagram": {"url": "https://www.instagram.com/",      "profile": "./browser_profiles/ig_profile"},
}

# ── Navigation helpers ─────────────────────────────────────────────────────────
NAV_ITEMS = [
    ("home",     "🏠", "Home"),
    ("leads",    "🎯", "Find Leads"),
    ("content",  "✍️", "Content Studio"),
    ("ads",      "📢", "Google Ads"),
    ("strategy", "🧠", "Optimise Hub"),
    ("chat",     "💬", "AI Chat"),
]

def get_active_tab() -> str:
    return st.query_params.get("tab", "home")

def go_to(tab_key: str):
    st.query_params["tab"] = tab_key
    st.rerun()


# ── Async helpers ──────────────────────────────────────────────────────────────
def run_async(coro):
    try:    return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:    return loop.run_until_complete(coro)
        finally: loop.close()

async def _check_session(d, url):
    from playwright.async_api import async_playwright
    if not os.path.exists(d) or not os.listdir(d): return False
    async with async_playwright() as p:
        try:
            b = await p.chromium.launch_persistent_context(user_data_dir=d, headless=True, args=["--disable-blink-features=AutomationControlled"])
            pg = await b.new_page()
            await pg.goto(url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(3)
            ok = False
            if "linkedin"  in url: ok = await pg.locator("#global-nav").count() > 0
            elif "facebook" in url: ok = await pg.locator("div[role='navigation']").count() > 0
            elif "instagram"in url: ok = await pg.locator("nav").count() > 0
            await b.close(); return ok
        except:
            try: await b.close()
            except: pass
            return False

async def _scrape_all(kw):
    from linkedin import LinkedInAgent; from facebook import FacebookAgent; from instagram import InstagramAgent
    results = []
    for plt, coro in [
        ("linkedin",  LinkedInAgent().fetch_recent_posts(keyword=kw, max_posts=2)),
        ("facebook",  FacebookAgent().fetch_group_posts(max_posts=2)),
        ("instagram", InstagramAgent().fetch_hashtag_posts(hashtag=kw.replace(" ","").lower(), max_posts=2)),
    ]:
        try:
            posts = await coro
            if posts and not (isinstance(posts[0], dict) and "error" in posts[0]):
                for p in posts: results.append({"platform": plt, "text": p["text"], "url": p["url"]})
        except Exception as e: results.append({"platform": plt, "error": str(e)})
    return results

async def _post_comment(platform, url, text):
    from linkedin import LinkedInAgent; from facebook import FacebookAgent; from instagram import InstagramAgent
    cls = {"linkedin": LinkedInAgent, "facebook": FacebookAgent, "instagram": InstagramAgent}.get(platform)
    return await cls().post_comment(url, text) if cls else False

async def _network(kw):
    from linkedin import LinkedInAgent; from facebook import FacebookAgent
    m = st.session_state.brain.memory_store; b = st.session_state.brain
    fb = await FacebookAgent().discover_and_join_groups(memory_store=m, brain_agent=b, keyword=kw, daily_limit=2)
    li = await LinkedInAgent().discover_and_connect(memory_store=m, brain_agent=b, keyword=kw, daily_limit=2)
    return fb or [], li or []


# ── Action handlers ────────────────────────────────────────────────────────────
def approve(did):
    item = st.session_state.pending.get(did)
    if not item: return
    st.session_state.brain.memory_store.log_feedback(drafted_text=item["draft"], status="approved", original_post=item["original"])
    if item.get("platform"):
        with st.spinner(f"Posting to {item['platform'].capitalize()}..."):
            ok = run_async(_post_comment(item["platform"], item["url"], item["draft"]))
        st.success("Posted!" if ok else "Automation failed — check logs.")
    else:
        st.success("Saved!")
    del st.session_state.pending[did]

def reject(did):
    item = st.session_state.pending.get(did)
    if not item: return
    st.session_state.brain.memory_store.log_feedback(drafted_text=item["draft"], status="rejected", original_post=item["original"])
    del st.session_state.pending[did]

def handle_chat(user_input, media_path=None):
    brain = st.session_state.brain
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Thinking..."):
        reply = brain.chat(user_input, media_path=media_path)
    fl = re.search(r'\[TOOL: FIND_LEADS:?\s*(.*?)\]', reply, re.IGNORECASE)
    nw = re.search(r'\[TOOL: NETWORK:?\s*(.*?)\]',    reply, re.IGNORECASE)
    clean = re.sub(r'\[TOOL:.*?\]', '', reply, flags=re.IGNORECASE).strip()
    st.session_state.messages.append({"role": "agent", "content": clean})
    if fl: _do_find_leads(fl.group(1).strip() or "NDIS")
    if nw: _do_network(nw.group(1).strip() or "Support Coordinator")

def _do_find_leads(kw):
    with st.spinner(f"Scanning platforms for '{kw}'..."):
        results = run_async(_scrape_all(kw))
    found = 0
    for item in results:
        if "error" in item:
            st.session_state.messages.append({"role":"agent","content":f"⚠️ {item['platform'].capitalize()}: {item['error'][:100]}"})
            continue
        draft = st.session_state.brain.chat(f"Found on {item['platform']}:\n'{item['text']}'\nDraft short professional outreach for Good Nurse.")
        did = uuid.uuid4().hex[:8]
        st.session_state.pending[did] = {"platform":item["platform"],"url":item["url"],"draft":draft,"original":item["text"],"keyword":kw}
        found += 1
    st.session_state.messages.append({"role":"agent","content": f"Found {found} lead(s) for '{kw}'." if found else f"No posts found for '{kw}'."})

def _do_network(kw):
    with st.spinner(f"Launching drones for '{kw}'..."):
        fb, li = run_async(_network(kw))
    summary = "\n".join((fb or []) + (li or [])) or "No new activity."
    st.session_state.messages.append({"role":"agent","content": f"**Networking complete:**\n{summary}"})

def _do_draft(topic, platform="all platforms"):
    with st.spinner("Drafting..."):
        draft = st.session_state.brain.chat(f"Create a professional, engaging {platform} post for Good Nurse about: {topic}. Ready to copy-paste.")
    did = uuid.uuid4().hex[:8]
    st.session_state.pending[did] = {"platform":None,"url":"","draft":draft,"original":topic,"keyword":topic}

def _do_check_auth():
    for name, cfg in PLATFORM_SESSIONS.items():
        with st.spinner(f"Checking {name}..."):
            st.session_state.session_status[name] = run_async(_check_session(cfg["profile"], cfg["url"]))


# ── DB helpers ─────────────────────────────────────────────────────────────────
def _count_pending_suggestions():
    try:
        c = sqlite3.connect("./sqlite_memory.db").cursor()
        c.execute("SELECT COUNT(*) FROM suggestions WHERE status='pending'")
        return c.fetchone()[0]
    except: return 0

def _load_suggestions(status="pending"):
    try:
        conn = sqlite3.connect("./sqlite_memory.db"); cur = conn.cursor()
        q = "SELECT id,date,title,description,rationale,pros,cons,cost_estimate,expected_impact,implementation_steps,suggestion_type,urgency,auto_implementable,implementation_data,status,result_message,created_at FROM suggestions"
        if status.lower() != "all":
            cur.execute(q + " WHERE status=? ORDER BY created_at DESC LIMIT 30", (status.lower(),))
        else:
            cur.execute(q + " ORDER BY created_at DESC LIMIT 30")
        keys = ["id","date","title","description","rationale","pros","cons","cost_estimate","expected_impact","implementation_steps","suggestion_type","urgency","auto_implementable","implementation_data","status","result_message","created_at"]
        rows = [dict(zip(keys, r)) for r in cur.fetchall()]
        conn.close(); return rows
    except: return []

def _update_suggestion(sid, status, msg=""):
    try:
        conn = sqlite3.connect("./sqlite_memory.db")
        conn.execute("UPDATE suggestions SET status=?,result_message=? WHERE id=?", (status, msg, sid))
        conn.commit(); conn.close()
    except: pass

def _process_action_queue():
    try:
        conn = sqlite3.connect("./sqlite_memory.db"); c = conn.cursor()
        c.execute("SELECT id,action_type,params FROM action_queue WHERE status='pending'"); rows = c.fetchall(); conn.close()
        for rid, atype, ps in rows:
            params = _json.loads(ps) if ps else {}
            if   atype == "find_leads": _do_find_leads(params.get("keyword","NDIS"))
            elif atype == "network":    _do_network(params.get("keyword","Support Coordinator"))
            elif atype == "draft_post": _do_draft(params.get("topic","NDIS services"))
            conn2 = sqlite3.connect("./sqlite_memory.db"); conn2.execute("UPDATE action_queue SET status='done' WHERE id=?", (rid,)); conn2.commit(); conn2.close()
    except: pass
_process_action_queue()


# ── HEADER + NAV (single sticky block) ────────────────────────────────────────
n_sugg  = _count_pending_suggestions()
n_appro = len(st.session_state.pending)
active  = get_active_tab()

nav_links = ""
for key, icon, label in NAV_ITEMS:
    cls = "gn-nav-item gn-nav-active" if active == key else "gn-nav-item"
    nav_links += f'<a href="?tab={key}" class="{cls}" target="_self">{icon}&nbsp; {label}</a>'

st.markdown(f"""
<div class="gn-topbar">
  <div class="gn-header">
    <div class="gn-logo-wrap">
      <div class="gn-logo">🏥</div>
      <div>
        <div class="gn-name">Good Nurse</div>
        <div class="gn-tagline">AI Marketing Agent &nbsp;·&nbsp; NDIS &amp; Aged Care &nbsp;·&nbsp; Westmead, Sydney</div>
      </div>
    </div>
    <div class="gn-stats">
      <div class="gn-stat"><div class="gn-stat-num">{n_sugg}</div><div class="gn-stat-lbl">New Suggestions</div></div>
      <div class="gn-stat"><div class="gn-stat-num">{n_appro}</div><div class="gn-stat-lbl">Pending Approvals</div></div>
      <div class="gn-stat"><div class="gn-stat-num" style="color:#69F0AE">●</div><div class="gn-stat-lbl">Agent Active</div></div>
    </div>
  </div>
  <div class="gn-nav">{nav_links}</div>
</div>
""", unsafe_allow_html=True)

# ── Tile helper ────────────────────────────────────────────────────────────────
def render_tile(icon, title, desc, badge, badge_type, color_class, btn_label, btn_key, btn_type="primary"):
    """Renders a card tile + button. Returns True if button was clicked."""
    badge_cls = {"alert": "badge-alert", "success": "badge-success", "neutral": "badge-neutral"}.get(badge_type, "badge-neutral")
    st.markdown(f"""
    <div class="tile {color_class}">
        <div class="tile-icon">{icon}</div>
        <div class="tile-title">{title}</div>
        <div class="tile-desc">{desc}</div>
        <span class="tile-badge {badge_cls}">{badge}</span>
    </div>""", unsafe_allow_html=True)
    return st.button(btn_label, key=btn_key, use_container_width=True, type=btn_type)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════════════════════
if active == "home":
    st.markdown('<div class="page-title">Welcome back 👋</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Your autonomous marketing agent is active. Choose what you want to do today.</div>', unsafe_allow_html=True)

    import google_ads as gads
    ads_ok = gads.is_configured()
    sugg_badge = f"{n_sugg} new suggestions" if n_sugg else "Up to date"
    lead_badge = f"{n_appro} awaiting approval" if n_appro else "Ready to scan"
    ads_badge  = "Connected" if ads_ok else "Setup required"

    # ── Row 1 ──
    st.markdown('<div class="section-title">📊 Marketing Operations</div>', unsafe_allow_html=True)
    r1c1, r1c2, r1c3 = st.columns(3, gap="medium")
    with r1c1:
        if render_tile("🧠","Optimise Hub",
            "Daily AI-powered strategy briefs. Research-backed suggestions to grow your client base and referral network.",
            sugg_badge, "alert" if n_sugg else "success", "tile-strategy",
            "Open Optimise Hub →", "t_strategy"):
            go_to("strategy")
    with r1c2:
        if render_tile("🎯","Find New Leads",
            "Scan LinkedIn, Facebook & Instagram for NDIS participants, families, and referring professionals.",
            lead_badge, "alert" if n_appro else "neutral", "tile-leads",
            "Find Leads →", "t_leads"):
            go_to("leads")
    with r1c3:
        if render_tile("📢","Google Ads",
            "Manage your NDIS client acquisition and referral network campaigns. Track spend and performance.",
            ads_badge, "success" if ads_ok else "neutral", "tile-ads",
            "Manage Google Ads →", "t_ads"):
            go_to("ads")

    st.markdown("")   # spacer

    # ── Row 2 ──
    st.markdown('<div class="section-title">🛠 Content & Community</div>', unsafe_allow_html=True)
    r2c1, r2c2, r2c3 = st.columns(3, gap="medium")
    with r2c1:
        if render_tile("✍️","Content Studio",
            "Create professional posts for Facebook, Instagram, LinkedIn & TikTok. Upload your own photos.",
            "Ready", "neutral", "tile-content",
            "Create Content →", "t_content"):
            go_to("content")
    with r2c2:
        if render_tile("🤝","Auto-Network",
            "Autonomously join NDIS Facebook groups and send connection requests to support coordinators on LinkedIn.",
            "Ready to launch", "neutral", "tile-network",
            "Launch Networking →", "t_network"):
            go_to("leads")
    with r2c3:
        if render_tile("💬","AI Marketing Chat",
            "Talk directly to your marketing expert. Strategy, psychology, ad copy, community building — anything.",
            "Always on", "success", "tile-chat",
            "Chat with Agent →", "t_chat"):
            go_to("chat")

    # ── Quick tip ──
    st.markdown("")
    st.markdown("""
    <div style="background:#E3F2FD;border-radius:12px;padding:16px 20px;border-left:4px solid #1565C0;font-size:13px;color:#1565C0;">
        💡 <strong>Tip:</strong> Click any tile above to jump straight in — or use the <strong>AI Chat</strong> tab to talk to your marketing expert any time.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: FIND LEADS
# ══════════════════════════════════════════════════════════════════════════════
elif active == "leads":
    st.markdown('<div class="page-title">🎯 Find Leads</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Scan social media for NDIS participants, families, and referral professionals. Review every outreach message before it posts.</div>', unsafe_allow_html=True)

    # Search controls
    st.markdown('<div class="section-title">Search & Scan</div>', unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns([3, 1, 1], gap="medium")
    with sc1:
        kw = st.text_input("Keyword", value="NDIS Sydney",
            placeholder="e.g. NDIS Sydney, support coordinator, aged care Westmead",
            label_visibility="collapsed")
    with sc2:
        if st.button("🎯  Find Leads", use_container_width=True, type="primary"):
            _do_find_leads(kw); st.rerun()
    with sc3:
        if st.button("🤝  Network", use_container_width=True):
            _do_network(kw); st.rerun()

    # Platform status
    with st.expander("🔌  Platform Session Status", expanded=False):
        sc1, sc2, sc3, sc4 = st.columns([2,2,2,1])
        for col, name in zip([sc1, sc2, sc3], PLATFORM_SESSIONS):
            status = st.session_state.session_status[name]
            icon = "✅" if status is True else ("❌" if status is False else "⬜")
            with col:
                st.markdown(f"**{icon} {name}**")
        with sc4:
            if st.button("Check Auth", use_container_width=True):
                _do_check_auth(); st.rerun()
        if any(v is False for v in st.session_state.session_status.values()):
            st.warning("Some sessions expired. Run `python auth.py` to re-login.")

    # Approval queue
    if st.session_state.pending:
        st.markdown(f'<div class="section-title">📋 Approval Queue &nbsp;<span style="background:#FFF3E0;color:#E65100;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">{len(st.session_state.pending)} pending</span></div>', unsafe_allow_html=True)
        for did, item in list(st.session_state.pending.items()):
            lbl = f"🎯 {item['platform'].capitalize()} Lead Outreach" if item["platform"] else "✍️ Draft Post"
            st.markdown(f"""
            <div class="appr-card">
                <div class="appr-label">{lbl}</div>
            </div>""", unsafe_allow_html=True)
            if item["platform"] and item["original"]:
                st.markdown("**Post found on social media:**")
                st.markdown(f'<div class="post-quote">{item["original"][:300]}{"…" if len(item["original"])>300 else ""}</div>', unsafe_allow_html=True)
            st.markdown("**Proposed outreach comment:**")
            st.markdown(f'<div class="draft-box">{item["draft"]}</div>', unsafe_allow_html=True)
            if item.get("url"):
                st.caption(f"Source: {item['url']}")
            b1, b2, _ = st.columns([1.4, 1, 4])
            with b1:
                if st.button("✅  Approve & Post", key=f"ap_{did}", type="primary"):
                    approve(did); st.rerun()
            with b2:
                if st.button("❌  Reject", key=f"rj_{did}"):
                    reject(did); st.rerun()
            st.markdown("---")
    else:
        st.info("No pending approvals. Run a search above to find leads.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CONTENT STUDIO
# ══════════════════════════════════════════════════════════════════════════════
elif active == "content":
    st.markdown('<div class="page-title">✍️ Content Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Create professional posts for every platform. Upload your own photos and the agent will craft authentic content around them.</div>', unsafe_allow_html=True)

    cc1, cc2 = st.columns(2, gap="large")

    with cc1:
        st.markdown('<div class="section-title">📝 Draft a Post</div>', unsafe_allow_html=True)
        topic = st.text_input("What is the post about?",
            placeholder="e.g. NDIS respite care, complex nursing, team values, client success story")
        platform_choice = st.selectbox("Platform", ["Facebook", "Instagram", "LinkedIn", "TikTok caption", "All platforms"])
        if st.button("✍️  Generate Post", type="primary", use_container_width=True):
            if topic:
                _do_draft(topic, platform_choice)
                st.success("Draft created! Review it in the queue below.")
                st.rerun()
            else:
                st.warning("Please enter a topic first.")

    with cc2:
        st.markdown('<div class="section-title">📸 Post from Your Photo</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload a photo or video", type=["jpg","jpeg","png","mp4","mov"])
        photo_ctx = st.text_input("Describe the photo (optional)", placeholder="e.g. Our nurse Sarah with a client at home")
        if st.button("🎨  Create Post from Photo", use_container_width=True):
            if uploaded:
                mp = f"temp_{uploaded.name}"
                with open(mp,"wb") as f: f.write(uploaded.getbuffer())
                with st.spinner("Analysing photo and crafting post..."):
                    draft = st.session_state.brain.chat(
                        photo_ctx or "Create a warm, professional social media post for Good Nurse about this photo.", media_path=mp)
                if os.path.exists(mp): os.remove(mp)
                did = uuid.uuid4().hex[:8]
                st.session_state.pending[did] = {"platform":None,"url":"","draft":draft,"original":photo_ctx,"keyword":"photo post"}
                st.success("Post drafted! Review it below.")
                st.rerun()
            else:
                st.warning("Please upload a photo first.")

    # Content drafts queue
    content_items = {k:v for k,v in st.session_state.pending.items() if not v.get("platform")}
    if content_items:
        st.markdown(f'<div class="section-title">📋 Draft Queue &nbsp;<span style="background:#FFF3E0;color:#E65100;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">{len(content_items)} drafts</span></div>', unsafe_allow_html=True)
        for did, item in list(content_items.items()):
            st.markdown(f'<div class="draft-box">{item["draft"]}</div>', unsafe_allow_html=True)
            b1, b2, _ = st.columns([1, 1, 5])
            with b1:
                if st.button("✅  Save", key=f"cs_{did}", type="primary"):
                    approve(did); st.rerun()
            with b2:
                if st.button("❌  Discard", key=f"cd_{did}"):
                    reject(did); st.rerun()
            st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: GOOGLE ADS
# ══════════════════════════════════════════════════════════════════════════════
elif active == "ads":
    st.markdown('<div class="page-title">📢 Google Ads Manager</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Two campaign strategies running in parallel: direct NDIS client acquisition + professional referral network (social workers, OTs, support coordinators, GPs).</div>', unsafe_allow_html=True)

    import google_ads as gads

    if not gads.is_configured():
        st.warning("⚠️ Google Ads is not connected yet. Follow the 5 steps below to get started.")
        st.markdown("")

        steps = [
            ("1", "Google Ads Account", "Go to **ads.google.com** — your **Customer ID** is the 10-digit number at the top right (e.g. `123-456-7890`)."),
            ("2", "Google Cloud Credentials", "Go to **console.cloud.google.com** → New project → Enable **Google Ads API** → Credentials → Create OAuth 2.0 Client ID (Desktop app). Copy the **Client ID** and **Client Secret**."),
            ("3", "Developer Token", "In Google Ads: click the **Tools** icon → **API Center** → Apply for **Basic Access** (free) → copy your Developer Token."),
            ("4", "Get Refresh Token", "Add your Client ID & Client Secret to `.env`, then run in terminal:\n```\npython get_google_ads_token.py\n```\nA browser opens → log in → your refresh token prints."),
            ("5", "Add all keys to .env", "```\nGOOGLE_ADS_DEVELOPER_TOKEN=...\nGOOGLE_ADS_CLIENT_ID=...\nGOOGLE_ADS_CLIENT_SECRET=...\nGOOGLE_ADS_REFRESH_TOKEN=...\nGOOGLE_ADS_CUSTOMER_ID=1234567890\n```\nThen restart the app."),
        ]
        for num, title, desc in steps:
            st.markdown(f'<div class="step-card"><span class="step-num">Step {num}</span> &nbsp; <strong>{title}</strong></div>', unsafe_allow_html=True)
            st.markdown(desc)
            st.markdown("")

    else:
        # Performance refresh
        if st.button("🔄  Refresh Campaign Performance", type="primary"):
            with st.spinner("Fetching from Google Ads..."):
                try:    st.session_state.ads_campaigns = gads.get_campaigns()
                except Exception as e: st.error(f"Could not fetch: {e}")

        campaigns = st.session_state.get("ads_campaigns", [])

        if campaigns:
            t_imp = sum(c["impressions"] for c in campaigns)
            t_clk = sum(c["clicks"] for c in campaigns)
            t_cst = sum(c["cost_aud"] for c in campaigns)
            t_con = sum(c["conversions"] for c in campaigns)
            t_ctr = (t_clk/t_imp*100) if t_imp else 0
            st.markdown('<div class="section-title">📊 Last 7 Days Performance</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="metric-row">
                <div class="metric-box"><div class="metric-val">{t_imp:,}</div><div class="metric-label">Impressions</div></div>
                <div class="metric-box"><div class="metric-val">{t_clk:,}</div><div class="metric-label">Clicks</div></div>
                <div class="metric-box"><div class="metric-val">{t_ctr:.1f}%</div><div class="metric-label">Click-Through Rate</div></div>
                <div class="metric-box"><div class="metric-val">${t_cst:.2f}</div><div class="metric-label">Total Spend (AUD)</div></div>
                <div class="metric-box"><div class="metric-val">{t_con:.0f}</div><div class="metric-label">Conversions</div></div>
            </div>""", unsafe_allow_html=True)

            st.markdown('<div class="section-title">🗂 Active Campaigns</div>', unsafe_allow_html=True)
            for c in campaigns:
                ic = "🟢" if c["status"]=="ENABLED" else "🟡"
                ci, cs, ca = st.columns([3,4,2])
                with ci:
                    st.markdown(f"**{ic} {c['name']}**")
                    st.caption(f"Budget: ${c['budget_aud']:.2f}/day &nbsp;|&nbsp; ID: {c['id']}")
                with cs:
                    st.caption(f"Impressions: {c['impressions']:,} &nbsp;·&nbsp; Clicks: {c['clicks']:,} &nbsp;·&nbsp; CTR: {c['ctr_pct']}% &nbsp;·&nbsp; Spend: ${c['cost_aud']:.2f}")
                with ca:
                    if c["status"]=="ENABLED":
                        if st.button("⏸  Pause", key=f"p_{c['id']}"):
                            try: gads.set_campaign_status(str(c["id"]), False); st.success("Paused.")
                            except Exception as e: st.error(str(e))
                    else:
                        if st.button("▶  Enable", key=f"e_{c['id']}", type="primary"):
                            try: gads.set_campaign_status(str(c["id"]), True); st.success("Live!")
                            except Exception as e: st.error(str(e))
                st.divider()
        else:
            st.info("No campaigns yet — create your first campaigns below, or click Refresh to load existing ones.")

        # Create new
        st.markdown('<div class="section-title">➕ Create New Campaigns</div>', unsafe_allow_html=True)
        st.markdown("Both campaigns start **PAUSED** so you can review before going live.")
        st.markdown("")
        nc1, nc2 = st.columns(2, gap="large")
        with nc1:
            st.markdown("**Strategy 1 — Direct NDIS Clients**")
            st.caption("Participants and families searching Google for NDIS providers")
            b_d = st.number_input("Daily budget (AUD)", 5.0, 500.0, st.session_state.ads_budgets["direct"], 5.0, key="bd")
        with nc2:
            st.markdown("**Strategy 2 — Referral Network**")
            st.caption("Social workers, OTs, GPs and case managers who refer clients")
            b_r = st.number_input("Daily budget (AUD)", 5.0, 500.0, st.session_state.ads_budgets["referral"], 5.0, key="br")
        st.session_state.ads_budgets = {"direct": b_d, "referral": b_r}

        if st.button("📋  Generate Campaign Proposal", use_container_width=True):
            st.session_state.ads_proposal = gads.get_proposal_text(b_d, b_r)

        if st.session_state.ads_proposal:
            st.markdown("---")
            st.markdown(st.session_state.ads_proposal)
            total = b_d + b_r
            st.info(f"**Total:** ~${total:.0f}/day &nbsp;·&nbsp; ~${total*30:.0f}/month AUD &nbsp;·&nbsp; Both campaigns start PAUSED.")
            pa, pb = st.columns([1, 5])
            with pa:
                if st.button("✅  Create Campaigns", type="primary", use_container_width=True):
                    with st.spinner("Creating in Google Ads (~30s)…"):
                        try:
                            r = gads.create_campaigns(b_d, b_r)
                            if r.get("errors"): st.error("; ".join(r["errors"]))
                            if r.get("direct"):  st.success(f"✅ Direct campaign created — ID {r['direct']['campaign_id']}, PAUSED")
                            if r.get("referral"): st.success(f"✅ Referral campaign created — ID {r['referral']['campaign_id']}, PAUSED")
                            st.session_state.ads_proposal = None
                        except Exception as e: st.error(str(e))
            with pb:
                if st.button("Cancel"):
                    st.session_state.ads_proposal = None; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: OPTIMISE HUB
# ══════════════════════════════════════════════════════════════════════════════
elif active == "strategy":
    st.markdown('<div class="page-title">🧠 Optimise Hub</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Every morning at 7:00 AM the agent researches Google Ads performance, past activity, goodnurse.com.au and live NDIS market trends — then generates tailored suggestions with full plans, pros/cons and cost estimates.</div>', unsafe_allow_html=True)

    oc1, oc2, oc3 = st.columns([2, 2, 4])
    with oc1:
        if st.button("🔬  Run Morning Brief Now", type="primary", use_container_width=True):
            with st.spinner("Researching NDIS market, analysing goodnurse.com.au, reviewing Google Ads… (1–2 min)"):
                try:
                    from strategy_engine import run_morning_brief
                    run_morning_brief(brain=st.session_state.brain)
                    st.success("Done! Suggestions loaded below.")
                    st.rerun()
                except Exception as e: st.error(f"Failed: {e}")
    with oc2:
        filt = st.selectbox("Show", ["Pending", "All", "Approved", "Rejected"], key="sfilt", label_visibility="collapsed")

    suggestions = _load_suggestions(filt)
    urg_order = {"HIGH":0,"MEDIUM":1,"LOW":2}
    suggestions.sort(key=lambda s: urg_order.get(s.get("urgency","LOW"), 2))

    st.markdown("")

    if not suggestions:
        st.markdown("""
        <div class="card" style="text-align:center;padding:48px 24px;">
            <div style="font-size:52px;margin-bottom:14px">🧠</div>
            <div class="card-title" style="font-size:18px">No suggestions yet</div>
            <div class="card-sub">Click "Run Morning Brief Now" to generate your first AI strategy report.</div>
        </div>""", unsafe_allow_html=True)
    else:
        for s in suggestions:
            urg   = s.get("urgency","LOW")
            s_icon = {"pending":"⏳","approved":"✅","rejected":"❌","implemented":"🚀"}.get(s["status"],"○")
            tag_cls = {"HIGH":"tag-high","MEDIUM":"tag-med","LOW":"tag-low"}.get(urg,"tag-low")
            auto_tag = '<span class="tag tag-auto">🤖 Auto-implementable</span>' if s["auto_implementable"] else ""

            with st.expander(f"{s_icon}  {s['title']}  ·  {urg}  ·  {s['date']}", expanded=(s["status"]=="pending")):
                st.markdown(f"""
                <div class="sugg sugg-{urg}">
                    <div class="sugg-title">{s['title']}</div>
                    <div class="sugg-meta">
                        <span class="tag {tag_cls}">● {urg}</span>
                        <span class="tag tag-type">{s['suggestion_type']}</span>
                        {auto_tag}
                    </div>
                    <div style="font-size:13px;color:#37474F;line-height:1.6"><strong>What to do:</strong> {s['description']}</div>
                </div>""", unsafe_allow_html=True)

                st.markdown(f"**Why (research-backed):** {s['rationale']}")
                st.markdown("")

                pc1, pc2, pc3 = st.columns(3, gap="medium")
                with pc1:
                    st.markdown("**✅ Pros**")
                    for l in s["pros"].split("\n"):
                        if l.strip(): st.markdown(f"- {l.strip().lstrip('-').strip()}")
                with pc2:
                    st.markdown("**⚠️ Risks**")
                    for l in s["cons"].split("\n"):
                        if l.strip(): st.markdown(f"- {l.strip().lstrip('-').strip()}")
                with pc3:
                    st.markdown(f"**💰 Cost Estimate**")
                    st.markdown(f"**{s['cost_estimate']}**")
                    st.markdown("")
                    st.markdown(f"**📈 Expected Impact**")
                    st.markdown(s["expected_impact"])

                if s["implementation_steps"]:
                    st.markdown("**🛠 Implementation Steps:**")
                    st.markdown(s["implementation_steps"])

                if s.get("result_message"):
                    st.info(f"Result: {s['result_message']}")

                if s["status"] == "pending":
                    st.markdown("")
                    ab1, ab2, _ = st.columns([2, 1.2, 5])
                    lbl = "✅  Approve & Auto-Implement" if s["auto_implementable"] else "✅  Approve"
                    with ab1:
                        if st.button(lbl, key=f"as_{s['id']}", type="primary"):
                            if s["auto_implementable"]:
                                with st.spinner("Implementing…"):
                                    try:
                                        from strategy_engine import implement_suggestion
                                        ok, msg = implement_suggestion(s)
                                        _update_suggestion(s["id"], "implemented" if ok else "approved", msg)
                                        st.success(msg)
                                    except Exception as e:
                                        _update_suggestion(s["id"], "approved", str(e))
                                        st.warning(f"Auto-implement failed — approved for manual action: {e}")
                            else:
                                _update_suggestion(s["id"], "approved", "Approved — manual implementation.")
                                st.success("Approved!")
                            st.rerun()
                    with ab2:
                        if st.button("❌  Dismiss", key=f"ds_{s['id']}"):
                            _update_suggestion(s["id"], "rejected", "Dismissed."); st.rerun()

    # Full brief
    st.markdown("")
    st.markdown('<div class="section-title">📄 Latest Full Morning Brief</div>', unsafe_allow_html=True)
    try:
        conn = sqlite3.connect("./sqlite_memory.db"); cur = conn.cursor()
        cur.execute("SELECT brief_date, brief_text FROM daily_briefs ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone(); conn.close()
        if row:
            st.caption(f"Generated: {row[0]}")
            with st.expander("View full brief"):
                st.markdown(row[1])
        else:
            st.info("No brief generated yet.")
    except: st.info("No brief generated yet.")

    st.markdown("")
    st.markdown('<div class="section-title">⏰ Automatic Daily Scheduler</div>', unsafe_allow_html=True)
    st.markdown("Run this in a second terminal to enable automatic 7:00 AM briefs:")
    st.code("python run_scheduler.py", language="bash")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: AI CHAT
# ══════════════════════════════════════════════════════════════════════════════
elif active == "chat":
    st.markdown('<div class="page-title">💬 AI Marketing Chat</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Your world-class marketing expert. Ask about strategy, human psychology, campaign ideas, content creation — anything.</div>', unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown('<div class="section-title">Suggested Questions</div>', unsafe_allow_html=True)
        sq1, sq2, sq3 = st.columns(3, gap="medium")
        prompts = [
            ("💡", "What's the best way to get NDIS referrals from social workers in Western Sydney?"),
            ("📊", "Analyse our current marketing strategy and give me your top 3 improvements"),
            ("✍️", "Write a LinkedIn post that will attract support coordinators to refer clients to us"),
        ]
        for col, (icon, prompt) in zip([sq1, sq2, sq3], prompts):
            with col:
                st.markdown(f"""
                <div class="card" style="min-height:90px;cursor:pointer">
                    <div style="font-size:22px;margin-bottom:6px">{icon}</div>
                    <div style="font-size:12px;color:#546E7A;line-height:1.5">{prompt}</div>
                </div>""", unsafe_allow_html=True)
                if st.button("Ask this →", key=f"qp_{prompt[:15]}", use_container_width=True):
                    handle_chat(prompt); st.rerun()
    else:
        for msg in st.session_state.messages:
            role   = "user" if msg["role"]=="user" else "assistant"
            avatar = None if msg["role"]=="user" else "🏥"
            with st.chat_message(role, avatar=avatar):
                st.markdown(msg["content"])

    st.markdown("")
    uploaded_chat = st.file_uploader("Attach a photo or video (optional)", type=["jpg","jpeg","png","mp4","mov"],
        label_visibility="collapsed", key="chat_upload")
    user_input = st.chat_input("Ask your marketing expert anything…", key="main_chat")
    if user_input:
        mp = None
        if uploaded_chat:
            mp = f"temp_{uploaded_chat.name}"
            with open(mp,"wb") as f: f.write(uploaded_chat.getbuffer())
        handle_chat(user_input, media_path=mp)
        if mp and os.path.exists(mp): os.remove(mp)
        st.rerun()
