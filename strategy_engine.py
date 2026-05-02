"""
Daily Strategy Engine for Good Nurse Marketing Agent.
Runs every morning at 7am:
  1. Pulls Google Ads performance data
  2. Analyses past activity from SQLite
  3. Does live market research via Gemini web search
  4. Generates 3-5 specific suggestions with full plans, pros/cons, cost estimates
  5. Saves to SQLite suggestions table
  6. Auto-implements approved suggestions
"""

import os
import json
import logging
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Suggestion types and their auto-implement capabilities
SUGGESTION_TYPES = {
    "GOOGLE_ADS_BUDGET":     "Adjust Google Ads daily budget",
    "GOOGLE_ADS_KEYWORD":    "Add new keywords to Google Ads",
    "GOOGLE_ADS_PAUSE":      "Pause underperforming campaign or ad group",
    "GOOGLE_ADS_NEW_CAMPAIGN": "Create a new Google Ads campaign",
    "SOCIAL_MEDIA_POST":     "Create and schedule a social media post",
    "LEAD_SEARCH":           "Run a targeted lead search on social platforms",
    "NETWORK_OUTREACH":      "Launch networking drones with specific keyword",
    "COMMUNITY_ACTION":      "Take a community building action",
    "STRATEGY_SHIFT":        "Strategic repositioning recommendation",
}

RESEARCH_PROMPT = """You are the world's #1 healthcare digital marketing strategist with 20 years of experience
in NDIS, aged care, and disability services marketing in Australia.

Your client is Good Nurse — a registered NDIS provider based in Westmead, Sydney.
Services: In-home nursing, disability support, high-intensity daily activities, complex care (PEG feeding,
catheter care, bowel management), hospital-to-home transitions, aged care.
Website: goodnurse.com.au (Squarespace) | Phone: 1300 457 557
Key conversion asset: QR code in physical/digital materials that leads directly to a consultation booking form on goodnurse.com.au.
The booking form is the primary lead capture mechanism — optimising traffic TO this form is critical.

You have just completed your comprehensive morning research session. Here is all the data you have collected:

=== GOOGLE ADS PERFORMANCE (Last 7 Days) ===
{ads_data}

=== PAST MARKETING ACTIVITY (Last 14 Days) ===
{activity_data}

=== YOUR WEB RESEARCH FINDINGS ===
Search topics researched:
- Current NDIS market trends in Sydney
- Competitor NDIS providers in Westmead and Western Sydney
- Recent NDIS policy changes and funding updates
- Social media trends in disability and aged care
- Best performing ad strategies for healthcare providers in Australia
- QR code marketing and landing page conversion strategies
- Squarespace website optimisation for lead generation

{web_research}

IMPORTANT — When analysing goodnurse.com.au: The QR code → booking consultation form is the PRIMARY
conversion funnel. Any suggestion that increases traffic to the booking form or improves its conversion
rate is extremely high value. Consider suggestions around: QR code placement, Google Ads landing page
targeting the booking form, website copy improvements, load speed, mobile experience, and call-to-action clarity.

=== PREVIOUS SUGGESTIONS STATUS ===
{past_suggestions}

---

Based on ALL of this data, generate a DAILY MARKETING BRIEF with exactly this structure:

## EXECUTIVE SUMMARY
2-3 sentences on the overall marketing health and today's priority.

## PERFORMANCE ANALYSIS
What is working well and what needs attention (be specific with numbers where available).

## TODAY'S RECOMMENDATIONS

For EACH recommendation (generate 3 to 5), use EXACTLY this format:

### SUGGESTION [N]: [TITLE]
**Type:** [one of: GOOGLE_ADS_BUDGET | GOOGLE_ADS_KEYWORD | GOOGLE_ADS_PAUSE | GOOGLE_ADS_NEW_CAMPAIGN | SOCIAL_MEDIA_POST | LEAD_SEARCH | NETWORK_OUTREACH | COMMUNITY_ACTION | STRATEGY_SHIFT]
**Urgency:** [HIGH | MEDIUM | LOW]
**What:** [Specific action to take — be very precise]
**Why:** [Evidence-based reasoning from your research — reference specific data points]
**Pros:**
- [pro 1]
- [pro 2]
- [pro 3]
**Cons / Risks:**
- [con 1]
- [con 2]
**Cost Estimate:** [Specific AUD amount or range, or "No additional cost"]
**Expected Impact:** [Specific, measurable outcome — e.g. "20-30% increase in click-through rate within 2 weeks"]
**Implementation Steps:**
1. [step 1]
2. [step 2]
3. [step 3]
**Auto-Implementable:** [YES | NO — YES means the agent can do it autonomously once approved]
**Implementation Data:** [JSON object with parameters needed for auto-implementation, or null]

---

Be bold, specific, and data-driven. These suggestions should feel like they come from a senior marketing consultant
who deeply understands the NDIS sector, human psychology, and digital advertising.
"""


def _get_ads_summary() -> str:
    """Pull Google Ads performance data if configured."""
    try:
        import google_ads as gads
        if not gads.is_configured():
            return "Google Ads not yet connected."
        campaigns = gads.get_campaigns()
        if not campaigns:
            return "No active Google Ads campaigns found."
        lines = []
        for c in campaigns:
            lines.append(
                f"Campaign: {c['name']} | Status: {c['status']} | "
                f"Budget: ${c['budget_aud']:.2f}/day | Impressions: {c['impressions']:,} | "
                f"Clicks: {c['clicks']:,} | CTR: {c['ctr_pct']}% | "
                f"Spend: ${c['cost_aud']:.2f} | Avg CPC: ${c['avg_cpc_aud']:.2f} | "
                f"Conversions: {c['conversions']:.0f}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Could not retrieve Google Ads data: {e}"


def _get_activity_summary(db_path: str = "./sqlite_memory.db") -> str:
    """Pull past 14 days of marketing activity from SQLite."""
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM post_feedback
            GROUP BY status
        """)
        feedback_rows = cursor.fetchall()

        cursor.execute("""
            SELECT platform, COUNT(*) as count
            FROM networked_profiles
            WHERE timestamp >= datetime('now', '-14 days')
            GROUP BY platform
        """)
        network_rows = cursor.fetchall()

        cursor.execute("""
            SELECT drafted_text, status
            FROM post_feedback
            ORDER BY id DESC
            LIMIT 5
        """)
        recent_posts = cursor.fetchall()

        conn.close()

        lines = ["Post Feedback:"]
        for status, count in feedback_rows:
            lines.append(f"  {status.capitalize()}: {count} posts")

        lines.append("\nNetworking Activity (last 14 days):")
        for platform, count in network_rows:
            lines.append(f"  {platform.capitalize()}: {count} profiles/groups contacted")

        lines.append("\nRecent Post Examples:")
        for text, status in recent_posts:
            lines.append(f"  [{status.upper()}] {text[:100]}...")

        return "\n".join(lines) if feedback_rows or network_rows else "No activity recorded yet — this is the first run."

    except Exception as e:
        return f"Could not read activity data: {e}"


def _get_past_suggestions_summary(db_path: str = "./sqlite_memory.db") -> str:
    """Get status of previously generated suggestions."""
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT title, status, created_at
            FROM suggestions
            ORDER BY created_at DESC
            LIMIT 10
        """)
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "No previous suggestions. This is the first morning brief."
        lines = []
        for title, status, created_at in rows:
            lines.append(f"  [{status.upper()}] {title} ({created_at[:10]})")
        return "\n".join(lines)
    except Exception:
        return "No previous suggestions recorded."


def _analyse_website() -> str:
    """Fetch and analyse goodnurse.com.au for conversion and SEO insights."""
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {"User-Agent": "Mozilla/5.0 (compatible; GoodNurseAgent/1.0)"}
        pages = {
            "Homepage":       "https://www.goodnurse.com.au",
            "Contact/Booking": "https://www.goodnurse.com.au/contact",
        }
        notes = []
        for label, url in pages.items():
            try:
                r = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(r.text, "html.parser")

                title = soup.find("title")
                meta_desc = soup.find("meta", attrs={"name": "description"})
                h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
                h2s = [h.get_text(strip=True) for h in soup.find_all("h2")][:5]
                cta_buttons = [b.get_text(strip=True) for b in
                               soup.find_all(["a","button"], string=lambda s: s and
                               any(w in s.lower() for w in ["book","consult","contact","get","start","enquire","call"]))]

                notes.append(f"""
{label} ({url}):
  Title: {title.get_text(strip=True) if title else 'Not found'}
  Meta Description: {meta_desc.get('content','Not found') if meta_desc else 'Missing — SEO gap'}
  H1s: {h1s}
  H2s: {h2s}
  CTA Buttons/Links found: {cta_buttons[:8]}
""")
            except Exception as e:
                notes.append(f"{label}: Could not fetch — {e}")

        return "Website Analysis (goodnurse.com.au — Squarespace, QR code → booking form):\n" + "\n".join(notes)
    except Exception as e:
        return f"Website analysis unavailable: {e}"


def _web_research(brain) -> str:
    """Use Gemini with Google Search grounding to research NDIS market."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        search_tool = types.Tool(google_search=types.GoogleSearch())

        queries = [
            "NDIS provider marketing strategies Australia 2025",
            "NDIS Sydney Western Sydney disability support trends 2025",
            "best Google Ads strategies for healthcare NDIS providers Australia",
            "social media marketing NDIS disability support",
            "Squarespace landing page conversion optimisation healthcare",
            "QR code marketing strategy healthcare lead generation Australia",
        ]

        research_notes = []
        for query in queries:
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"Research this topic and summarise the 3 most actionable insights for a small NDIS provider in Sydney: {query}",
                    config=types.GenerateContentConfig(
                        tools=[search_tool],
                        max_output_tokens=400,
                    )
                )
                research_notes.append(f"Query: {query}\n{response.text}")
            except Exception as e:
                research_notes.append(f"Query: {query}\n[Search unavailable: {e}]")

        return "\n\n---\n\n".join(research_notes)

    except Exception as e:
        return f"Web research unavailable: {e}\nUsing AI knowledge base only."


def _parse_suggestions_from_brief(brief_text: str) -> list:
    """Parse the structured brief into individual suggestion dicts."""
    import re
    suggestions = []

    blocks = re.split(r'### SUGGESTION \d+:', brief_text)
    for block in blocks[1:]:  # skip the header block
        try:
            def extract(field, text):
                pattern = rf'\*\*{re.escape(field)}:\*\*\s*(.*?)(?=\n\*\*|\n###|\Z)'
                m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                return m.group(1).strip() if m else ""

            title_match = re.match(r'\s*(.*?)\n', block)
            title = title_match.group(1).strip() if title_match else "Untitled"

            stype    = extract("Type", block)
            urgency  = extract("Urgency", block)
            what     = extract("What", block)
            why      = extract("Why", block)
            pros     = extract("Pros", block)
            cons     = extract("Cons / Risks", block)
            cost     = extract("Cost Estimate", block)
            impact   = extract("Expected Impact", block)
            steps    = extract("Implementation Steps", block)
            auto     = extract("Auto-Implementable", block)
            impl_data = extract("Implementation Data", block)

            try:
                impl_json = json.loads(impl_data) if impl_data and impl_data.lower() != "null" else {}
            except Exception:
                impl_json = {}

            suggestions.append({
                "title":               title,
                "suggestion_type":     stype.strip(),
                "urgency":             urgency.strip().upper(),
                "description":         what.strip(),
                "rationale":           why.strip(),
                "pros":                pros.strip(),
                "cons":                cons.strip(),
                "cost_estimate":       cost.strip(),
                "expected_impact":     impact.strip(),
                "implementation_steps": steps.strip(),
                "auto_implementable":  auto.strip().upper() == "YES",
                "implementation_data": impl_json,
            })
        except Exception as e:
            logger.warning(f"Failed to parse suggestion block: {e}")

    return suggestions


def save_suggestions(suggestions: list, brief_text: str, db_path: str = "./sqlite_memory.db"):
    """Save parsed suggestions + full brief to SQLite."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Save full brief
    cursor.execute("""
        INSERT INTO daily_briefs (brief_date, brief_text, created_at)
        VALUES (?, ?, datetime('now'))
    """, (date.today().isoformat(), brief_text))

    # Save individual suggestions
    for s in suggestions:
        cursor.execute("""
            INSERT INTO suggestions
                (date, title, description, rationale, pros, cons, cost_estimate,
                 expected_impact, implementation_steps, suggestion_type, urgency,
                 auto_implementable, implementation_data, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'))
        """, (
            date.today().isoformat(),
            s["title"], s["description"], s["rationale"],
            s["pros"], s["cons"], s["cost_estimate"],
            s["expected_impact"], s["implementation_steps"],
            s["suggestion_type"], s["urgency"],
            1 if s["auto_implementable"] else 0,
            json.dumps(s["implementation_data"]),
        ))

    conn.commit()
    conn.close()
    logger.info(f"Saved {len(suggestions)} suggestions to database.")


def implement_suggestion(suggestion: dict) -> tuple[bool, str]:
    """
    Auto-implement an approved suggestion.
    Returns (success, message).
    """
    stype = suggestion.get("suggestion_type", "")
    data  = suggestion.get("implementation_data") or {}
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            data = {}

    try:
        # ── Google Ads actions ─────────────────────────────────────────────
        if stype == "GOOGLE_ADS_BUDGET":
            import google_ads as gads
            campaign_id = data.get("campaign_id")
            new_budget  = data.get("new_daily_budget_aud")
            if campaign_id and new_budget:
                # Budget update via API
                client = gads._get_client()
                cid    = gads._customer_id()
                svc    = client.get_service("CampaignBudgetService")
                # Fetch budget resource name for this campaign
                ga_svc = client.get_service("GoogleAdsService")
                rows   = list(ga_svc.search(
                    customer_id=cid,
                    query=f"SELECT campaign_budget.resource_name FROM campaign WHERE campaign.id = {campaign_id}"
                ))
                if rows:
                    budget_rn = rows[0].campaign_budget.resource_name
                    op = client.get_type("CampaignBudgetOperation")
                    b  = op.update
                    b.resource_name   = budget_rn
                    b.amount_micros   = int(float(new_budget) * 1_000_000)
                    from proto import marshal
                    client.copy_from(op.update_mask, {"paths": ["amount_micros"]})
                    svc.mutate_campaign_budgets(customer_id=cid, operations=[op])
                    return True, f"Budget updated to ${new_budget}/day."
            return False, "Missing campaign_id or new_daily_budget_aud in implementation data."

        elif stype == "GOOGLE_ADS_PAUSE":
            import google_ads as gads
            campaign_id = data.get("campaign_id")
            if campaign_id:
                gads.set_campaign_status(str(campaign_id), enable=False)
                return True, f"Campaign {campaign_id} paused."
            return False, "Missing campaign_id."

        elif stype == "GOOGLE_ADS_NEW_CAMPAIGN":
            import google_ads as gads
            budget_d = data.get("daily_budget_direct", 30.0)
            budget_r = data.get("daily_budget_referral", 20.0)
            result   = gads.create_campaigns(budget_d, budget_r)
            if result.get("errors"):
                return False, "Errors: " + "; ".join(result["errors"])
            return True, f"New campaigns created: Direct ({result.get('direct',{}).get('campaign_id','?')}), Referral ({result.get('referral',{}).get('campaign_id','?')})"

        # ── Social / lead actions ──────────────────────────────────────────
        elif stype == "LEAD_SEARCH":
            keyword = data.get("keyword", "NDIS Sydney")
            # Store as a pending action — the UI will pick it up
            _queue_action("find_leads", {"keyword": keyword})
            return True, f"Lead search queued for keyword: '{keyword}'"

        elif stype == "NETWORK_OUTREACH":
            keyword = data.get("keyword", "Support Coordinator")
            _queue_action("network", {"keyword": keyword})
            return True, f"Networking drone queued for keyword: '{keyword}'"

        elif stype == "SOCIAL_MEDIA_POST":
            topic = data.get("topic", "NDIS services")
            _queue_action("draft_post", {"topic": topic})
            return True, f"Post draft queued for topic: '{topic}'"

        else:
            return False, f"Suggestion type '{stype}' cannot be auto-implemented. Manual action required."

    except Exception as e:
        logger.error(f"Implementation failed for {stype}: {e}")
        return False, f"Implementation error: {e}"


def _queue_action(action_type: str, params: dict, db_path: str = "./sqlite_memory.db"):
    """Queue an action for the Streamlit app to pick up and execute."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO action_queue (action_type, params, status, created_at)
        VALUES (?, ?, 'pending', datetime('now'))
    """, (action_type, json.dumps(params)))
    conn.commit()
    conn.close()


def run_morning_brief(brain=None) -> str:
    """
    Main entry point. Runs comprehensive research and generates morning brief.
    Returns the full brief text.
    """
    logger.info(f"Running morning brief at {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 1. Collect all data
    ads_data         = _get_ads_summary()
    activity_data    = _get_activity_summary()
    past_suggestions = _get_past_suggestions_summary()
    website_data     = _analyse_website()

    # 2. Web research
    logger.info("Running web research...")
    if brain:
        web_research = _web_research(brain)
    else:
        from brain import AgentBrain
        web_research = _web_research(AgentBrain())

    # 3. Generate brief with Gemini
    logger.info("Generating strategy brief...")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = RESEARCH_PROMPT.format(
        ads_data=ads_data,
        activity_data=activity_data,
        web_research=web_research + "\n\n" + website_data,
        past_suggestions=past_suggestions,
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro-preview-05-06",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=4000,
                temperature=0.7,
            )
        )
        brief_text = response.text
    except Exception as e:
        # Fallback to flash
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            brief_text = response.text
        except Exception as e2:
            brief_text = f"Brief generation failed: {e2}"
            logger.error(f"Brief generation failed: {e2}")
            return brief_text

    # 4. Parse and save
    suggestions = _parse_suggestions_from_brief(brief_text)
    save_suggestions(suggestions, brief_text)
    logger.info(f"Morning brief complete. {len(suggestions)} suggestions generated.")

    return brief_text
