# Good Nurse — Super Marketing Agent Blueprint

**Project:** Autonomous AI Marketing Agent for Good Nurse (NDIS provider, Westmead, Sydney)
**Updated:** 2026-04-23

---

## Vision

A world-class autonomous marketing agent that operates like a top-tier marketing professional. It manages Google Business, Google Ads, social media platforms, lead generation, community building, content creation, and campaign execution — surfacing opportunities to the user, awaiting approval, then executing without further intervention.

---

## Current State (What's Already Built)

### Infrastructure
| Component | Technology | Status |
|-----------|-----------|--------|
| Chat Interface | Telegram Bot (python-telegram-bot) | ✅ Live |
| AI Brain | Google Gemini 2.5 Pro (fallback: 2.0 Flash) | ✅ Live |
| Browser Automation | Playwright (async, persistent sessions) | ✅ Live |
| Memory / Learning | SQLite (approved/rejected drafts + anti-spam) | ✅ Live |
| Session Auth | Playwright persistent profiles | ✅ Live |

### Platform Agents
| Platform | Scrape Posts | Post Comments | Auto-Network | Status |
|----------|-------------|---------------|--------------|--------|
| LinkedIn | ✅ | ✅ | ✅ (connect + personalized notes) | Live |
| Facebook | ✅ (groups) | ✅ | ✅ (join groups + answer induction) | Live |
| Instagram | ✅ (hashtags) | ✅ | ❌ | Partial |
| TikTok | ❌ | ❌ | ❌ | Not started |
| Twitter/X | ❌ | ❌ | ❌ | Not started |
| Google Business | ❌ | ❌ | ❌ | Not started |
| Google Ads | ❌ | ❌ | ❌ | Not started |

### Telegram Bot Commands
| Command | Function |
|---------|----------|
| `/start` | Welcome + capability overview |
| `/draft <topic>` | AI generates social post → user approves/rejects inline |
| `/find_leads <keyword>` | Scans LinkedIn + Facebook + Instagram → generates outreach comments → user approves → posts autonomously |
| `/network <keyword>` | Launches "drones" to join Facebook groups + send LinkedIn connections |
| `/check_auth` | Validates login sessions across all platforms |

---

## Full System Architecture (Target)

```
┌─────────────────────────────────────────────────────────────┐
│                    TELEGRAM COMMAND CENTER                  │
│          (User <-> Agent interface for approvals)           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    AI BRAIN (Gemini)                         │
│  - Strategy generation     - Content creation               │
│  - Lead scoring            - Campaign planning              │
│  - Tone/persona: World-class marketing expert               │
│  - Learns from approvals/rejections via SQLite memory       │
└───┬────────┬─────────┬──────────┬───────────┬──────────────┘
    │        │         │          │           │
    ▼        ▼         ▼          ▼           ▼
┌──────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌─────────────────┐
│Google│ │Google│ │Facebook│ │LinkedIn│ │  Content Engine  │
│Biz   │ │Ads   │ │+Insta  │ │+TikTok │ │  (Media/Posts)  │
│Agent │ │Agent │ │+X Agent│ │+X Agent│ └─────────────────┘
└──────┘ └──────┘ └────────┘ └────────┘
```

---

## Roadmap: Features to Build

### Phase 1 — Stabilise & Harden (Current MVP) [PRIORITY: HIGH]
- [ ] Replace fragile Playwright selectors with official Meta Graph API for Facebook/Instagram posting
- [ ] Add structured logging (Python `logging` module → rotating log files)
- [ ] Add retry + error recovery loops (exponential backoff for browser failures)
- [ ] Enforce per-platform rate limits (daily caps tracked in SQLite)
- [ ] Move all hardcoded config (Good Nurse URLs, group URLs, names) into `config.py` or `.env`
- [ ] Encrypt `.env` secrets; add `.gitignore` for `.env` and `browser_profiles/`
- [ ] Add automated SQLite backups

### Phase 2 — Google Business & Reviews Agent [PRIORITY: HIGH]
- [ ] Integrate **Google Business Profile API** (manage profile, posts, Q&A)
- [ ] Monitor and respond to **Google Reviews** automatically (AI drafts response → user approves)
- [ ] Track review sentiment trends in memory (flag negative reviews immediately)
- [ ] Daily review summary delivered via Telegram

### Phase 3 — Google Ads Agent [PRIORITY: HIGH]
- [ ] Integrate **Google Ads API**
- [ ] AI generates **campaign proposals** (audience, budget, keywords, ad copy) → presents to user via Telegram
- [ ] On approval: automatically creates campaign, ad groups, keywords, ads
- [ ] Monitor campaign performance (CTR, CPC, conversions) daily
- [ ] Auto-pause underperforming ads; suggest optimisations → user approves → auto-implement
- [ ] Weekly ads performance report via Telegram

### Phase 4 — Lead Generation Engine [PRIORITY: HIGH]
- [ ] Expand `find_leads` to scan Facebook groups, Reddit, TikTok, Instagram hashtags daily (scheduled)
- [ ] Score leads by relevance using AI (NDIS keywords, location, intent signals)
- [ ] Build **lead database** (SQLite table: name, platform, URL, score, status, contacted date)
- [ ] Generate personalised outreach for each lead (Telegram approval flow)
- [ ] Track outreach outcomes (responded, converted, ignored)

### Phase 5 — Community Building Agent [PRIORITY: MEDIUM]
- [ ] Create and manage dedicated **Facebook Group** for NDIS/disability care community
- [ ] Auto-post daily value content to group (tips, resources, inspiring stories)
- [ ] Welcome new members with personalised AI message → user approves template
- [ ] Identify active community members as potential leads
- [ ] Monitor group for support questions → respond or escalate

### Phase 6 — Content Creation Engine [PRIORITY: MEDIUM]
- [ ] **Media sourcing**: Search for free stock photos/videos matching post topic (Unsplash, Pexels APIs)
- [ ] **User media intake**: Telegram prompt asking user to upload photos → stored in `media/` folder
- [ ] AI image/video editing pipeline (crop, caption overlay, branding — Pillow / FFmpeg)
- [ ] Create platform-optimised content variants (TikTok vertical, Instagram square, Facebook landscape)
- [ ] Content calendar: AI plans 30-day posting schedule → user approves → auto-schedules

### Phase 7 — Daily Strategy Loop [PRIORITY: MEDIUM]
- [ ] Every morning: AI analyses prior day performance, market signals, competitor activity
- [ ] Generates **Daily Strategy Brief** → delivered to user via Telegram (approve/modify)
- [ ] Strategy updates inform all downstream agents (content tone, lead targeting, ad bidding)
- [ ] Weekly strategic report: wins, misses, recommendations

### Phase 8 — TikTok & Twitter/X Agent [PRIORITY: MEDIUM]
- [ ] TikTok: hashtag scraping, video comment outreach, profile discovery
- [ ] Twitter/X: tweet monitoring, reply outreach, thread discovery (Tweepy + X API v2)
- [ ] Integrate into unified `find_leads` and `network` pipelines

### Phase 9 — Analytics Dashboard [PRIORITY: LOW]
- [ ] Aggregate metrics from all platforms into SQLite `analytics` table
- [ ] Weekly Telegram report: leads found, posts made, connections, reviews, ad spend/ROI
- [ ] Optional: HTML dashboard export

---

## Approval Workflow (Core UX Pattern)

```
Agent detects opportunity / generates plan
          ↓
Telegram message to user:
  📋 PROPOSAL: [Title]
  [Details of what it will do, why, estimated impact]
  [✅ Approve] [✏️ Edit] [❌ Reject]
          ↓
User approves → Agent executes autonomously
User edits   → Agent revises → re-presents
User rejects → Agent logs rejection → learns from it
```

All major actions follow this pattern:
- New ad campaign
- Outreach comment / DM
- Joining a group
- Responding to a review
- Publishing a post

---

## Agent Persona

The AI brain operates with this identity baked into its system prompt:

> "You are the world's best marketing agent, specialising in healthcare and NDIS services. You have deep expertise in human psychology, consumer behaviour, social proof, community building, and digital advertising. You think in terms of full-funnel strategy — awareness, trust, leads, conversion, retention. Every action you take is backed by proven marketing science. You always propose before acting, explain your reasoning, and learn from what the user approves or rejects."

---

## File Structure (Current + Planned)

```
Social Media Agent/
├── bot.py                  ✅ Telegram bot entry point
├── brain.py                ✅ Gemini AI brain
├── auth.py                 ✅ Platform authentication
├── memory.py               ✅ SQLite memory + anti-spam
├── linkedin.py             ✅ LinkedIn agent
├── facebook.py             ✅ Facebook agent  
├── instagram.py            ✅ Instagram agent (partial)
├── config.py               ❌ Centralised config (planned)
├── google_business.py      ❌ Google Business agent (planned)
├── google_ads.py           ❌ Google Ads agent (planned)
├── tiktok.py               ❌ TikTok agent (planned)
├── twitter.py              ❌ Twitter/X agent (planned)
├── content_engine.py       ❌ Media sourcing + editing (planned)
├── lead_tracker.py         ❌ Lead database + scoring (planned)
├── community_manager.py    ❌ Group management (planned)
├── scheduler.py            ❌ Daily strategy loop (planned)
├── analytics.py            ❌ Metrics aggregation (planned)
├── browser_profiles/       ✅ Persistent Playwright sessions (681MB)
├── media/                  ❌ User-uploaded + sourced media (planned)
├── logs/                   ❌ Rotating log files (planned)
├── sqlite_memory.db        ✅ Memory database (20KB, live)
├── requirements.txt        ✅ Dependencies
├── .env                    ✅ API keys (keep secret, never commit)
├── .env.example            ✅ Key template
└── BLUEPRINT.md            ✅ This file
```

---

## API Keys Needed (Full Target State)

| Key | Purpose | Status |
|-----|---------|--------|
| `GEMINI_API_KEY` | AI brain | ✅ Active |
| `TELEGRAM_BOT_TOKEN` | Bot interface | ✅ Active |
| `TELEGRAM_CHAT_ID` | Manager notifications | ✅ Active |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads API | ❌ Needed |
| `GOOGLE_ADS_CLIENT_ID/SECRET` | Google Ads OAuth | ❌ Needed |
| `GOOGLE_BUSINESS_API_KEY` | Business Profile API | ❌ Needed |
| `META_ACCESS_TOKEN` | Facebook/Instagram Graph API | ❌ Needed |
| `FB_PAGE_ID` | Facebook page | ❌ Needed |
| `IG_ACCOUNT_ID` | Instagram business account | ❌ Needed |
| `X_API_KEY` / `X_BEARER_TOKEN` | Twitter/X | ❌ Needed |
| `TIKTOK_ACCESS_TOKEN` | TikTok for Business | ❌ Needed |
| `PEXELS_API_KEY` | Free stock photos | ❌ Needed |
| `UNSPLASH_ACCESS_KEY` | Free stock photos | ❌ Needed |

---

## Immediate Next Steps (Recommended Order)

1. **Fix stability first** — add structured logging and retry logic to existing agents (Phase 1)
2. **Google Business Reviews** — high-value, relatively easy API (Phase 2)
3. **Lead database** — upgrade SQLite schema to track leads end-to-end (Phase 4)
4. **Daily scheduler** — wire the `schedule` library already in requirements.txt (Phase 7)
5. **Google Ads** — biggest revenue impact (Phase 3)
6. **Content Engine** — media sourcing + user photo intake via Telegram (Phase 6)
