"""
Google Ads Agent for Good Nurse.
Handles campaign creation, performance monitoring, and AI-generated proposals.
Two targeting strategies:
  1. Direct — NDIS participants & families searching for providers
  2. Referral — Social workers, support coordinators, OTs who refer clients
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Campaign templates ─────────────────────────────────────────────────────────
# Pre-researched, NDIS-specific. Two full strategies.

DIRECT_AD_GROUPS = [
    {
        "name": "NDIS Provider Sydney",
        "cpc_bid_micros": 4_000_000,   # $4 AUD
        "keywords": [
            ("ndis provider sydney",                    "EXACT"),
            ("registered ndis provider sydney",         "EXACT"),
            ("ndis provider westmead",                  "PHRASE"),
            ("ndis support services sydney",            "PHRASE"),
            ("ndis registered provider",                "BROAD"),
        ],
        "headlines": [
            "Registered NDIS Provider Sydney",
            "Expert NDIS Support Services",
            "Good Nurse — Quality NDIS Care",
            "NDIS Provider in Westmead Sydney",
            "Trusted & Registered NDIS Support",
            "NDIS Services Tailored for You",
            "Book a Free NDIS Consultation",
        ],
        "descriptions": [
            "Registered NDIS provider in Westmead. Expert in-home nursing, disability support & complex care. Call 1300 457 557.",
            "Good Nurse delivers personalised NDIS support across Sydney. Complex care specialists. Free consultation available.",
            "Quality NDIS support from a team you can trust. Flexible plans, experienced staff. Contact us today.",
        ],
    },
    {
        "name": "Disability Support Services",
        "cpc_bid_micros": 3_500_000,
        "keywords": [
            ("disability support services sydney",      "EXACT"),
            ("disability support worker sydney",        "PHRASE"),
            ("ndis disability support sydney",          "PHRASE"),
            ("high intensity daily activities ndis",    "BROAD"),
            ("complex disability care sydney",          "BROAD"),
        ],
        "headlines": [
            "Disability Support in Sydney",
            "NDIS High Intensity Support",
            "Complex Disability Care Experts",
            "Experienced NDIS Support Workers",
            "Personalised Disability Support",
            "High-Intensity Daily Activities",
            "Good Nurse — Disability Experts",
        ],
        "descriptions": [
            "Specialising in high-intensity daily activities & complex disability support across Sydney. NDIS registered.",
            "Experienced NDIS support workers. Daily personal activities, complex nursing, bowel & catheter care. Call us.",
        ],
    },
    {
        "name": "Home Nursing Care",
        "cpc_bid_micros": 3_500_000,
        "keywords": [
            ("home nursing care sydney",                "EXACT"),
            ("in home nurse sydney",                    "EXACT"),
            ("home care nurse sydney",                  "PHRASE"),
            ("private nurse home visit sydney",         "PHRASE"),
            ("nursing care at home sydney",             "BROAD"),
        ],
        "headlines": [
            "In-Home Nursing Care Sydney",
            "Qualified Nurses Come to You",
            "Professional Home Nursing",
            "Nurses for Home Visits Sydney",
            "Post-Hospital Home Care",
            "Complex Nursing at Home",
            "Good Nurse Home Care Sydney",
        ],
        "descriptions": [
            "Qualified nurses providing in-home care across Sydney. Wound care, PEG feeding, complex nursing. Book today.",
            "Good Nurse brings professional nursing to your home. NDIS registered. Call 1300 457 557 for a free chat.",
        ],
    },
    {
        "name": "Aged Care At Home",
        "cpc_bid_micros": 3_000_000,
        "keywords": [
            ("in home aged care sydney",                "EXACT"),
            ("aged care at home sydney",                "PHRASE"),
            ("elderly care at home sydney",             "PHRASE"),
            ("home aged care services sydney",          "BROAD"),
        ],
        "headlines": [
            "In-Home Aged Care Sydney",
            "Caring for Elderly at Home",
            "Compassionate Aged Care",
            "Qualified Nurses for Seniors",
            "Stay Home with Good Nurse",
            "Personalised Elder Care Sydney",
            "Hospital to Home Transition",
        ],
        "descriptions": [
            "Compassionate aged care at home across Sydney. Qualified nursing staff, flexible scheduling. Call us now.",
            "Good Nurse — expert in-home aged care & hospital-to-home transitions. Trusted by Sydney families. 1300 457 557.",
        ],
    },
]

REFERRAL_AD_GROUPS = [
    {
        "name": "Support Coordinators",
        "cpc_bid_micros": 5_000_000,   # Higher bid — these referrers are worth more
        "keywords": [
            ("ndis support coordinator referral",       "PHRASE"),
            ("ndis provider for support coordinators",  "PHRASE"),
            ("refer clients ndis provider sydney",      "BROAD"),
            ("ndis support coordination sydney",        "BROAD"),
            ("support coordinator ndis provider",       "BROAD"),
        ],
        "headlines": [
            "NDIS Referral Partner Sydney",
            "Reliable Provider for Your Clients",
            "Good Nurse — Refer with Confidence",
            "Complex Care NDIS Provider",
            "Partner With Good Nurse Today",
            "Fast Intake for Your NDIS Clients",
            "Support Coordinators Trust Us",
        ],
        "descriptions": [
            "Good Nurse is the trusted NDIS provider for support coordinators across Sydney. Complex care experts. Refer today.",
            "Fast, reliable intake for your NDIS participants. We handle complex care, nursing & disability support. 1300 457 557.",
        ],
    },
    {
        "name": "Social Workers",
        "cpc_bid_micros": 5_000_000,
        "keywords": [
            ("social worker ndis provider referral",    "PHRASE"),
            ("refer patient ndis home care sydney",     "BROAD"),
            ("ndis provider for social workers sydney", "BROAD"),
            ("hospital discharge ndis care sydney",     "BROAD"),
            ("social work ndis referral sydney",        "PHRASE"),
        ],
        "headlines": [
            "Refer Your Clients to Good Nurse",
            "NDIS Home Care for Social Workers",
            "Hospital Discharge — We're Ready",
            "Trusted NDIS Partner Sydney",
            "Fast Client Intake Available",
            "Complex Care NDIS Specialists",
            "Good Nurse — Refer with Ease",
        ],
        "descriptions": [
            "Helping social workers place NDIS clients quickly. We specialise in complex care & hospital-to-home transitions.",
            "Good Nurse — fast, responsive NDIS provider for hospital social workers. Covering all of Sydney. Call us today.",
        ],
    },
    {
        "name": "Occupational Therapists",
        "cpc_bid_micros": 4_500_000,
        "keywords": [
            ("ot ndis provider referral sydney",        "PHRASE"),
            ("occupational therapist ndis referral",    "BROAD"),
            ("ndis provider recommended by ot",         "BROAD"),
            ("ot refer ndis support worker sydney",     "BROAD"),
        ],
        "headlines": [
            "OT Referrals — Good Nurse Sydney",
            "Trusted NDIS Partner for OTs",
            "Reliable NDIS Provider Sydney",
            "Refer Your NDIS Clients to Us",
            "Complex Care You Can Trust",
            "We Work With Your NDIS Goals",
            "Good Nurse — OT Preferred Partner",
        ],
        "descriptions": [
            "Good Nurse works alongside OTs to deliver NDIS support that meets your clients' therapy goals. Sydney-wide.",
            "Partner with Good Nurse. We follow your plans and communicate progress. NDIS registered, complex care experts.",
        ],
    },
    {
        "name": "Case Managers & GPs",
        "cpc_bid_micros": 4_500_000,
        "keywords": [
            ("case manager ndis provider sydney",       "PHRASE"),
            ("gp referral ndis home care sydney",       "BROAD"),
            ("refer ndis client home nursing sydney",   "BROAD"),
            ("care manager ndis provider referral",     "BROAD"),
        ],
        "headlines": [
            "GP & Case Manager Referrals",
            "NDIS Home Nursing Sydney",
            "Refer Patients to Good Nurse",
            "Complex Care After Discharge",
            "We Handle the Hard Cases",
            "NDIS & Private Nursing Care",
            "Good Nurse — Refer Today",
        ],
        "descriptions": [
            "Good Nurse accepts GP & case manager referrals for NDIS and private home nursing care across Sydney.",
            "Complex post-discharge nursing, wound care, PEG feeding. Fast intake for your patients. 1300 457 557.",
        ],
    },
]


def is_configured() -> bool:
    """Returns True if all required Google Ads env vars are set."""
    required = [
        "GOOGLE_ADS_DEVELOPER_TOKEN",
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",
    ]
    return all(os.getenv(k) for k in required)


def _get_client():
    from google.ads.googleads.client import GoogleAdsClient
    creds = {
        "developer_token":  os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id":        os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret":    os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token":    os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "use_proto_plus":   True,
    }
    login_cid = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    if login_cid:
        creds["login_customer_id"] = login_cid.replace("-", "")
    return GoogleAdsClient.load_from_dict(creds)


def _customer_id() -> str:
    return os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")


# ── Core helpers ───────────────────────────────────────────────────────────────

def _create_budget(client, customer_id: str, name: str, daily_budget_aud: float) -> str:
    svc = client.get_service("CampaignBudgetService")
    op  = client.get_type("CampaignBudgetOperation")
    b   = op.create
    b.name                  = name
    b.delivery_method       = client.enums.BudgetDeliveryMethodEnum.STANDARD
    b.amount_micros         = int(daily_budget_aud * 1_000_000)
    b.explicitly_shared     = False
    res = svc.mutate_campaign_budgets(customer_id=customer_id, operations=[op])
    return res.results[0].resource_name


def _get_sydney_location_id(client, customer_id: str) -> str:
    """Look up Sydney's geo target constant resource name."""
    svc = client.get_service("GeoTargetConstantService")
    req = client.get_type("SuggestGeoTargetConstantsRequest")
    req.locale = "en"
    req.country_code = "AU"
    req.location_names.names.append("Sydney")
    resp = svc.suggest_geo_target_constants(request=req)
    for suggestion in resp.geo_target_constant_suggestions:
        g = suggestion.geo_target_constant
        if "Sydney" in g.name and "New South Wales" in g.canonical_name:
            return g.resource_name
    # Fallback: hardcoded Sydney, NSW Australia criterion ID
    return "geoTargetConstants/21167"


def _create_campaign(client, customer_id: str, budget_rn: str,
                     name: str, location_rn: str) -> str:
    svc = client.get_service("CampaignService")
    op  = client.get_type("CampaignOperation")
    c   = op.create

    c.name                              = name
    c.status                            = client.enums.CampaignStatusEnum.PAUSED  # starts paused — user enables
    c.advertising_channel_type          = client.enums.AdvertisingChannelTypeEnum.SEARCH
    c.campaign_budget                   = budget_rn
    c.manual_cpc.enhanced_cpc_enabled   = True
    c.network_settings.target_google_search    = True
    c.network_settings.target_search_network   = True
    c.network_settings.target_content_network  = False

    # Location: Sydney
    c.geo_target_type_setting.positive_geo_target_type = (
        client.enums.PositiveGeoTargetTypeEnum.PRESENCE_OR_INTEREST
    )

    # Ad schedule: Mon-Sat business hours
    for day, start_h, end_h in [
        ("MONDAY", 7, 20), ("TUESDAY", 7, 20), ("WEDNESDAY", 7, 20),
        ("THURSDAY", 7, 20), ("FRIDAY", 7, 20), ("SATURDAY", 8, 17),
    ]:
        sch = c.ad_schedule_target.ad_schedules.add()
        sch.day_of_week = getattr(client.enums.DayOfWeekEnum, day)
        sch.start_hour  = start_h
        sch.end_hour    = end_h

    res = svc.mutate_campaigns(customer_id=customer_id, operations=[op])
    campaign_rn = res.results[0].resource_name

    # Add location targeting
    criterion_svc = client.get_service("CampaignCriterionService")
    crit_op = client.get_type("CampaignCriterionOperation")
    crit    = crit_op.create
    crit.campaign             = campaign_rn
    crit.location.geo_target_constant = location_rn
    criterion_svc.mutate_campaign_criteria(customer_id=customer_id, operations=[crit_op])

    return campaign_rn


def _create_ad_group(client, customer_id: str, campaign_rn: str,
                     name: str, cpc_bid_micros: int) -> str:
    svc = client.get_service("AdGroupService")
    op  = client.get_type("AdGroupOperation")
    ag  = op.create
    ag.name                 = name
    ag.campaign             = campaign_rn
    ag.status               = client.enums.AdGroupStatusEnum.ENABLED
    ag.type_                = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    ag.cpc_bid_micros       = cpc_bid_micros
    res = svc.mutate_ad_groups(customer_id=customer_id, operations=[op])
    return res.results[0].resource_name


def _add_keywords(client, customer_id: str, ad_group_rn: str,
                  keywords: list):
    svc = client.get_service("AdGroupCriterionService")
    ops = []
    match_map = {
        "EXACT":  client.enums.KeywordMatchTypeEnum.EXACT,
        "PHRASE": client.enums.KeywordMatchTypeEnum.PHRASE,
        "BROAD":  client.enums.KeywordMatchTypeEnum.BROAD,
    }
    for text, match_type in keywords:
        op = client.get_type("AdGroupCriterionOperation")
        kw = op.create
        kw.ad_group             = ad_group_rn
        kw.status               = client.enums.AdGroupCriterionStatusEnum.ENABLED
        kw.keyword.text         = text
        kw.keyword.match_type   = match_map.get(match_type, match_map["PHRASE"])
        ops.append(op)
    svc.mutate_ad_group_criteria(customer_id=customer_id, operations=ops)


def _create_rsa(client, customer_id: str, ad_group_rn: str,
                headlines: list, descriptions: list, final_url: str):
    svc = client.get_service("AdGroupAdService")
    op  = client.get_type("AdGroupAdOperation")
    ad  = op.create
    ad.ad_group = ad_group_rn
    ad.status   = client.enums.AdGroupAdStatusEnum.ENABLED

    rsa = ad.ad.responsive_search_ad
    rsa.path1 = "NDIS"
    rsa.path2 = "Sydney"

    for i, text in enumerate(headlines[:15]):
        asset = client.get_type("AdTextAsset")
        asset.text = text[:30]
        if i < 3:
            asset.pinned_field = client.enums.ServedAssetFieldTypeEnum.HEADLINE_1 if i == 0 else (
                client.enums.ServedAssetFieldTypeEnum.HEADLINE_2 if i == 1 else
                client.enums.ServedAssetFieldTypeEnum.HEADLINE_3
            )
        rsa.headlines.append(asset)

    for text in descriptions[:4]:
        asset = client.get_type("AdTextAsset")
        asset.text = text[:90]
        rsa.descriptions.append(asset)

    ad.ad.final_urls.append(final_url)
    svc.mutate_ad_group_ads(customer_id=customer_id, operations=[op])


# ── Public API ─────────────────────────────────────────────────────────────────

def create_campaigns(daily_budget_direct: float = 30.0,
                     daily_budget_referral: float = 20.0) -> dict:
    """
    Create both campaign strategies in Google Ads.
    Campaigns start PAUSED — user activates when ready.
    Returns a summary dict.
    """
    client      = _get_client()
    customer_id = _customer_id()
    final_url   = "https://goodnurse.com.au"
    summary     = {"direct": None, "referral": None, "errors": []}

    try:
        location_rn = _get_sydney_location_id(client, customer_id)
    except Exception as e:
        location_rn = "geoTargetConstants/21167"
        logger.warning(f"Location lookup failed, using fallback: {e}")

    for strategy, ad_groups, budget, label in [
        ("direct",   DIRECT_AD_GROUPS,   daily_budget_direct,   "Good Nurse — NDIS Clients Sydney"),
        ("referral", REFERRAL_AD_GROUPS, daily_budget_referral, "Good Nurse — Professional Referrals Sydney"),
    ]:
        try:
            budget_rn   = _create_budget(client, customer_id, f"{label} Budget", budget)
            campaign_rn = _create_campaign(client, customer_id, budget_rn, label, location_rn)
            campaign_id = campaign_rn.split("/")[-1]

            for ag_def in ad_groups:
                ag_rn = _create_ad_group(
                    client, customer_id, campaign_rn,
                    ag_def["name"], ag_def["cpc_bid_micros"]
                )
                _add_keywords(client, customer_id, ag_rn, ag_def["keywords"])
                _create_rsa(
                    client, customer_id, ag_rn,
                    ag_def["headlines"], ag_def["descriptions"], final_url
                )

            summary[strategy] = {
                "campaign_id":   campaign_id,
                "campaign_rn":   campaign_rn,
                "name":          label,
                "daily_budget":  budget,
                "ad_groups":     len(ad_groups),
                "status":        "PAUSED",
            }
            logger.info(f"Created campaign: {label} (ID: {campaign_id})")

        except Exception as e:
            summary["errors"].append(f"{strategy}: {e}")
            logger.error(f"Failed to create {strategy} campaign: {e}")

    return summary


def get_campaigns() -> list:
    """Return all campaigns with live performance metrics."""
    client      = _get_client()
    customer_id = _customer_id()
    svc         = client.get_service("GoogleAdsService")

    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign_budget.amount_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM campaign
        WHERE segments.date DURING LAST_7_DAYS
            AND campaign.advertising_channel_type = 'SEARCH'
        ORDER BY metrics.impressions DESC
    """
    response = svc.search(customer_id=customer_id, query=query)
    campaigns = []
    seen = set()
    for row in response:
        cid = row.campaign.id
        if cid in seen:
            continue
        seen.add(cid)
        campaigns.append({
            "id":           cid,
            "name":         row.campaign.name,
            "status":       row.campaign.status.name,
            "budget_aud":   row.campaign_budget.amount_micros / 1_000_000,
            "impressions":  row.metrics.impressions,
            "clicks":       row.metrics.clicks,
            "cost_aud":     row.metrics.cost_micros / 1_000_000,
            "conversions":  row.metrics.conversions,
            "ctr_pct":      round(row.metrics.ctr * 100, 2),
            "avg_cpc_aud":  row.metrics.average_cpc / 1_000_000,
        })
    return campaigns


def set_campaign_status(campaign_id: str, enable: bool):
    """Pause or enable a campaign by ID."""
    client      = _get_client()
    customer_id = _customer_id()
    svc         = client.get_service("CampaignService")
    op          = client.get_type("CampaignOperation")
    c           = op.update
    c.resource_name = svc.campaign_path(customer_id, campaign_id)
    c.status    = (client.enums.CampaignStatusEnum.ENABLED if enable
                   else client.enums.CampaignStatusEnum.PAUSED)
    client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, c._pb))
    svc.mutate_campaigns(customer_id=customer_id, operations=[op])


def get_proposal_text(daily_budget_direct: float, daily_budget_referral: float) -> str:
    """Return a human-readable campaign proposal for user approval."""
    direct_keywords  = sum(len(ag["keywords"]) for ag in DIRECT_AD_GROUPS)
    referral_keywords = sum(len(ag["keywords"]) for ag in REFERRAL_AD_GROUPS)
    total_budget = daily_budget_direct + daily_budget_referral

    return f"""
## Google Ads Campaign Proposal — Good Nurse

### Strategy 1: Direct Client Acquisition (${daily_budget_direct}/day)
Target: NDIS participants and families searching for providers in Sydney.

**Ad Groups ({len(DIRECT_AD_GROUPS)} groups, {direct_keywords} keywords):**
- NDIS Provider Sydney — "ndis provider sydney", "registered ndis provider sydney"...
- Disability Support Services — "disability support services sydney"...
- Home Nursing Care — "home nursing care sydney", "in home nurse sydney"...
- Aged Care At Home — "in home aged care sydney"...

**Goal:** Families and participants call 1300 457 557 or visit goodnurse.com.au

---

### Strategy 2: Professional Referral Network (${daily_budget_referral}/day)
Target: Support coordinators, social workers, OTs, GPs, and case managers who refer clients.

**Ad Groups ({len(REFERRAL_AD_GROUPS)} groups, {referral_keywords} keywords):**
- Support Coordinators — "ndis provider for support coordinators"...
- Social Workers — "refer patient ndis home care sydney"...
- Occupational Therapists — "ot ndis provider referral sydney"...
- Case Managers & GPs — "gp referral ndis home care sydney"...

**Goal:** One referrer = multiple clients. Higher CPC bids ($4.50–$5.00) justified by lifetime value.

---

### Summary
| | |
|---|---|
| Total daily budget | **${total_budget} AUD/day** |
| Monthly estimate | **~${total_budget * 30:.0f} AUD/month** |
| Location | Sydney metro + Westmead |
| Schedule | Mon–Fri 7am–8pm, Sat 8am–5pm |
| Start status | **PAUSED** — you activate when ready |

**Both campaigns start PAUSED. You switch them on when you're ready.**
""".strip()
