"""
Multi-tenant database layer.
Supports SQLite (local dev) and PostgreSQL (Supabase production).
Set DATABASE_URL env var to switch to PostgreSQL — everything else is automatic.
"""
import os, json, uuid, bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional
from contextlib import contextmanager
from urllib.parse import urlparse, unquote

# ── DB detection ───────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES  = bool(DATABASE_URL) or bool(os.environ.get("DB_HOST"))
DB_PATH       = os.environ.get("DB_PATH", "./saas_data.db")
PH            = "%s" if USE_POSTGRES else "?"   # SQL placeholder

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

# ── Connection ─────────────────────────────────────────────────────────────────
@contextmanager
def get_conn():
    if USE_POSTGRES:
        import psycopg2, psycopg2.extras
        # Prefer explicit DB_* vars (avoids URL encoding issues with special chars in passwords).
        # Fall back to parsing DATABASE_URL if individual vars aren't set.
        db_host     = os.environ.get("DB_HOST")
        db_port     = int(os.environ.get("DB_PORT", "5432"))
        db_name     = os.environ.get("DB_NAME", "postgres")
        db_user     = os.environ.get("DB_USER", "postgres")
        db_password = os.environ.get("DB_PASSWORD")
        if not db_host:
            _u = urlparse(DATABASE_URL)
            db_host     = _u.hostname
            db_port     = _u.port or 5432
            db_name     = (_u.path or "/postgres").lstrip("/")
            db_user     = unquote(_u.username or "")
            db_password = unquote(_u.password or "")
        conn = psycopg2.connect(
            host=db_host, port=db_port, dbname=db_name,
            user=db_user, password=db_password,
            sslmode="require",
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

def _exec(conn, sql: str, params=()):
    """Run a query and return the cursor — works for both SQLite and psycopg2."""
    if USE_POSTGRES:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur
    return conn.execute(sql, params)

def _execmany(conn, sql: str, params_list):
    if USE_POSTGRES:
        cur = conn.cursor()
        cur.executemany(sql, params_list)
    else:
        conn.executemany(sql, params_list)

def _row(cur) -> Optional[dict]:
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)

def _rows(cur) -> list:
    return [dict(r) for r in cur.fetchall()]

# ── Schema ─────────────────────────────────────────────────────────────────────
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name          TEXT NOT NULL,
    business_name TEXT,
    avatar_url    TEXT,
    role          TEXT DEFAULT 'subscriber',
    created_at    TEXT DEFAULT (datetime('now')),
    last_login    TEXT
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id                      TEXT PRIMARY KEY,
    user_id                 TEXT NOT NULL REFERENCES users(id),
    tier                    TEXT NOT NULL DEFAULT 'free',
    status                  TEXT NOT NULL DEFAULT 'active',
    stripe_customer_id      TEXT,
    stripe_subscription_id  TEXT,
    current_period_start    TEXT,
    current_period_end      TEXT,
    cancel_at_period_end    INTEGER DEFAULT 0,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS platform_connections (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    platform        TEXT NOT NULL,
    access_token    TEXT,
    refresh_token   TEXT,
    token_expiry    TEXT,
    page_id         TEXT,
    page_name       TEXT,
    username        TEXT,
    profile_pic     TEXT,
    extra_data      TEXT,
    connected_at    TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, platform)
);
CREATE TABLE IF NOT EXISTS posts (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users(id),
    platform         TEXT NOT NULL,
    content          TEXT NOT NULL,
    image_url        TEXT,
    image_prompt     TEXT,
    hashtags         TEXT,
    scheduled_at     TEXT,
    published_at     TEXT,
    status           TEXT NOT NULL DEFAULT 'draft',
    platform_post_id TEXT,
    error_message    TEXT,
    created_at       TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS post_analytics (
    id           TEXT PRIMARY KEY,
    post_id      TEXT NOT NULL REFERENCES posts(id),
    user_id      TEXT NOT NULL REFERENCES users(id),
    platform     TEXT NOT NULL,
    likes        INTEGER DEFAULT 0,
    comments     INTEGER DEFAULT 0,
    shares       INTEGER DEFAULT 0,
    reach        INTEGER DEFAULT 0,
    impressions  INTEGER DEFAULT 0,
    clicks       INTEGER DEFAULT 0,
    saves        INTEGER DEFAULT 0,
    recorded_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(post_id, user_id, platform)
);
CREATE TABLE IF NOT EXISTS account_analytics (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id),
    platform          TEXT NOT NULL,
    followers         INTEGER DEFAULT 0,
    following         INTEGER DEFAULT 0,
    total_reach       INTEGER DEFAULT 0,
    total_impressions INTEGER DEFAULT 0,
    engagement_rate   REAL DEFAULT 0,
    recorded_at       TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS ai_suggestions (
    id                    TEXT PRIMARY KEY,
    user_id               TEXT NOT NULL REFERENCES users(id),
    title                 TEXT NOT NULL,
    description           TEXT,
    rationale             TEXT,
    pros                  TEXT,
    cons                  TEXT,
    cost_estimate         TEXT,
    expected_impact       TEXT,
    implementation_steps  TEXT,
    suggestion_type       TEXT,
    urgency               TEXT DEFAULT 'MEDIUM',
    auto_implementable    INTEGER DEFAULT 0,
    implementation_data   TEXT,
    status                TEXT DEFAULT 'pending',
    result_message        TEXT,
    created_at            TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS usage_tracking (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    action      TEXT NOT NULL,
    platform    TEXT,
    month_year  TEXT NOT NULL,
    count       INTEGER DEFAULT 1,
    UNIQUE(user_id, action, platform, month_year)
);
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS model_configs (
    id          TEXT PRIMARY KEY,
    model_type  TEXT NOT NULL,
    tier        TEXT NOT NULL,
    model_id    TEXT,
    provider    TEXT,
    updated_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(model_type, tier)
);
CREATE TABLE IF NOT EXISTS business_profiles (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id),
    business_name        TEXT NOT NULL,
    industry             TEXT,
    business_type        TEXT,
    location             TEXT,
    website              TEXT,
    target_audience      TEXT,
    competitors          TEXT,
    goals                TEXT,
    monthly_budget       REAL,
    tone                 TEXT DEFAULT 'professional',
    usp                  TEXT,
    services             TEXT,
    social_channels      TEXT,
    onboarding_complete  INTEGER DEFAULT 0,
    raw_conversation     TEXT,
    preferred_model      TEXT DEFAULT 'claude-sonnet-4-6',
    preferred_provider   TEXT DEFAULT 'anthropic',
    created_at           TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id)
);
CREATE TABLE IF NOT EXISTS ad_campaigns (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users(id),
    title            TEXT NOT NULL,
    description      TEXT,
    campaign_type    TEXT DEFAULT '30_day',
    start_date       TEXT,
    end_date         TEXT,
    total_budget     REAL,
    status           TEXT DEFAULT 'draft',
    channels         TEXT,
    timeline         TEXT,
    goals            TEXT,
    ai_rationale     TEXT,
    user_feedback    TEXT,
    market_research  TEXT,
    approved_at      TEXT,
    created_at       TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS campaign_items (
    id             TEXT PRIMARY KEY,
    campaign_id    TEXT NOT NULL REFERENCES ad_campaigns(id),
    user_id        TEXT NOT NULL REFERENCES users(id),
    platform       TEXT NOT NULL,
    content_type   TEXT,
    title          TEXT,
    content        TEXT,
    image_prompt   TEXT,
    image_url      TEXT,
    scheduled_date TEXT,
    budget         REAL,
    status         TEXT DEFAULT 'pending',
    post_id        TEXT,
    created_at     TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_posts_user        ON posts(user_id, status);
CREATE INDEX IF NOT EXISTS idx_posts_scheduled   ON posts(scheduled_at, status);
CREATE INDEX IF NOT EXISTS idx_analytics_user    ON post_analytics(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_suggestions_user  ON ai_suggestions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_sessions_token    ON sessions(token, expires_at);
CREATE INDEX IF NOT EXISTS idx_campaigns_user    ON ad_campaigns(user_id, status);
CREATE INDEX IF NOT EXISTS idx_biz_profile_user  ON business_profiles(user_id);
"""

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name          TEXT NOT NULL,
    business_name TEXT,
    avatar_url    TEXT,
    role          TEXT DEFAULT 'subscriber',
    created_at    TEXT DEFAULT '',
    last_login    TEXT
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id                      TEXT PRIMARY KEY,
    user_id                 TEXT NOT NULL REFERENCES users(id),
    tier                    TEXT NOT NULL DEFAULT 'free',
    status                  TEXT NOT NULL DEFAULT 'active',
    stripe_customer_id      TEXT,
    stripe_subscription_id  TEXT,
    current_period_start    TEXT,
    current_period_end      TEXT,
    cancel_at_period_end    INTEGER DEFAULT 0,
    created_at              TEXT DEFAULT '',
    updated_at              TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS platform_connections (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    platform        TEXT NOT NULL,
    access_token    TEXT,
    refresh_token   TEXT,
    token_expiry    TEXT,
    page_id         TEXT,
    page_name       TEXT,
    username        TEXT,
    profile_pic     TEXT,
    extra_data      TEXT,
    connected_at    TEXT DEFAULT '',
    updated_at      TEXT DEFAULT '',
    UNIQUE(user_id, platform)
);
CREATE TABLE IF NOT EXISTS posts (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users(id),
    platform         TEXT NOT NULL,
    content          TEXT NOT NULL,
    image_url        TEXT,
    image_prompt     TEXT,
    hashtags         TEXT,
    scheduled_at     TEXT,
    published_at     TEXT,
    status           TEXT NOT NULL DEFAULT 'draft',
    platform_post_id TEXT,
    error_message    TEXT,
    created_at       TEXT DEFAULT '',
    updated_at       TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS post_analytics (
    id           TEXT PRIMARY KEY,
    post_id      TEXT NOT NULL REFERENCES posts(id),
    user_id      TEXT NOT NULL REFERENCES users(id),
    platform     TEXT NOT NULL,
    likes        INTEGER DEFAULT 0,
    comments     INTEGER DEFAULT 0,
    shares       INTEGER DEFAULT 0,
    reach        INTEGER DEFAULT 0,
    impressions  INTEGER DEFAULT 0,
    clicks       INTEGER DEFAULT 0,
    saves        INTEGER DEFAULT 0,
    recorded_at  TEXT DEFAULT '',
    UNIQUE(post_id, user_id, platform)
);
CREATE TABLE IF NOT EXISTS account_analytics (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id),
    platform          TEXT NOT NULL,
    followers         INTEGER DEFAULT 0,
    following         INTEGER DEFAULT 0,
    total_reach       INTEGER DEFAULT 0,
    total_impressions INTEGER DEFAULT 0,
    engagement_rate   DOUBLE PRECISION DEFAULT 0,
    recorded_at       TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS ai_suggestions (
    id                    TEXT PRIMARY KEY,
    user_id               TEXT NOT NULL REFERENCES users(id),
    title                 TEXT NOT NULL,
    description           TEXT,
    rationale             TEXT,
    pros                  TEXT,
    cons                  TEXT,
    cost_estimate         TEXT,
    expected_impact       TEXT,
    implementation_steps  TEXT,
    suggestion_type       TEXT,
    urgency               TEXT DEFAULT 'MEDIUM',
    auto_implementable    INTEGER DEFAULT 0,
    implementation_data   TEXT,
    status                TEXT DEFAULT 'pending',
    result_message        TEXT,
    created_at            TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS usage_tracking (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    action      TEXT NOT NULL,
    platform    TEXT,
    month_year  TEXT NOT NULL,
    count       INTEGER DEFAULT 1,
    UNIQUE(user_id, action, platform, month_year)
);
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS model_configs (
    id          TEXT PRIMARY KEY,
    model_type  TEXT NOT NULL,
    tier        TEXT NOT NULL,
    model_id    TEXT,
    provider    TEXT,
    updated_at  TEXT DEFAULT '',
    UNIQUE(model_type, tier)
);
CREATE TABLE IF NOT EXISTS business_profiles (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id),
    business_name        TEXT NOT NULL,
    industry             TEXT,
    business_type        TEXT,
    location             TEXT,
    website              TEXT,
    target_audience      TEXT,
    competitors          TEXT,
    goals                TEXT,
    monthly_budget       DOUBLE PRECISION,
    tone                 TEXT DEFAULT 'professional',
    usp                  TEXT,
    services             TEXT,
    social_channels      TEXT,
    onboarding_complete  INTEGER DEFAULT 0,
    raw_conversation     TEXT,
    preferred_model      TEXT DEFAULT 'claude-sonnet-4-6',
    preferred_provider   TEXT DEFAULT 'anthropic',
    created_at           TEXT DEFAULT '',
    updated_at           TEXT DEFAULT '',
    UNIQUE(user_id)
);
CREATE TABLE IF NOT EXISTS ad_campaigns (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users(id),
    title            TEXT NOT NULL,
    description      TEXT,
    campaign_type    TEXT DEFAULT '30_day',
    start_date       TEXT,
    end_date         TEXT,
    total_budget     DOUBLE PRECISION,
    status           TEXT DEFAULT 'draft',
    channels         TEXT,
    timeline         TEXT,
    goals            TEXT,
    ai_rationale     TEXT,
    user_feedback    TEXT,
    market_research  TEXT,
    approved_at      TEXT,
    created_at       TEXT DEFAULT '',
    updated_at       TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS campaign_items (
    id             TEXT PRIMARY KEY,
    campaign_id    TEXT NOT NULL REFERENCES ad_campaigns(id),
    user_id        TEXT NOT NULL REFERENCES users(id),
    platform       TEXT NOT NULL,
    content_type   TEXT,
    title          TEXT,
    content        TEXT,
    image_prompt   TEXT,
    image_url      TEXT,
    scheduled_date TEXT,
    budget         DOUBLE PRECISION,
    status         TEXT DEFAULT 'pending',
    post_id        TEXT,
    created_at     TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_posts_user        ON posts(user_id, status);
CREATE INDEX IF NOT EXISTS idx_posts_scheduled   ON posts(scheduled_at, status);
CREATE INDEX IF NOT EXISTS idx_analytics_user    ON post_analytics(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_suggestions_user  ON ai_suggestions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_sessions_token    ON sessions(token, expires_at);
CREATE INDEX IF NOT EXISTS idx_campaigns_user    ON ad_campaigns(user_id, status);
CREATE INDEX IF NOT EXISTS idx_biz_profile_user  ON business_profiles(user_id);
"""

def init_db():
    with get_conn() as conn:  # noqa: SIM117
        if USE_POSTGRES:
            cur = conn.cursor()
            for stmt in (s.strip() for s in PG_SCHEMA.split(";") if s.strip()):
                cur.execute(stmt)
        else:
            conn.executescript(SQLITE_SCHEMA)
    _migrate()
    _seed_model_configs()
    _seed_owner()


def _migrate():
    """Safe column additions for schema updates after initial deploy."""
    migrations = [
        ("users",             "role",               "TEXT DEFAULT 'subscriber'"),
        ("business_profiles", "preferred_model",    "TEXT DEFAULT 'claude-sonnet-4-6'"),
        ("business_profiles", "preferred_provider", "TEXT DEFAULT 'anthropic'"),
    ]
    with get_conn() as conn:
        for table, column, col_def in migrations:
            try:
                _exec(conn, f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
            except Exception:
                pass


def _seed_owner():
    owner_email = os.environ.get("OWNER_EMAIL", "").lower().strip()
    if not owner_email:
        return
    with get_conn() as conn:
        _exec(conn,
              f"UPDATE users SET role='owner' WHERE email={PH} AND role!='owner'",
              (owner_email,))


def _seed_model_configs():
    from saas.model_registry import DEFAULT_TEXT_CONFIGS, get_provider_for_model
    with get_conn() as conn:
        cur = _exec(conn, "SELECT COUNT(*) as c FROM model_configs")
        row = _row(cur)
        count = row["c"] if row else 0
        if count and int(count) > 0:
            return
        rows = []
        for tier, mid in DEFAULT_TEXT_CONFIGS.items():
            provider = get_provider_for_model(mid, "text") if mid else None
            rows.append((str(uuid.uuid4()), "text", tier, mid, provider, _now()))
        rows.append((str(uuid.uuid4()), "image", "best", "fal-ai/flux-pro", "fal", _now()))
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.executemany(
                "INSERT INTO model_configs (id, model_type, tier, model_id, provider, updated_at)"
                " VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (model_type, tier) DO NOTHING",
                rows,
            )
        else:
            conn.executemany(
                "INSERT OR IGNORE INTO model_configs (id, model_type, tier, model_id, provider, updated_at)"
                " VALUES (?,?,?,?,?,?)",
                rows,
            )


try:
    init_db()
except Exception as _db_init_err:
    import sys
    print(f"DATABASE CONNECTION ERROR: {_db_init_err}", file=sys.stderr)
    raise RuntimeError(
        f"Cannot connect to database.\n\nError: {_db_init_err}\n\n"
        f"Check: 1) Supabase project is not paused  "
        f"2) DB_HOST/DATABASE_URL secrets are correct  "
        f"3) No IP restrictions blocking Streamlit Cloud"
    ) from _db_init_err

# ── Users ──────────────────────────────────────────────────────────────────────

def create_user(email: str, password: str, name: str, business_name: str = "") -> dict:
    uid     = str(uuid.uuid4())
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    now     = _now()
    with get_conn() as conn:
        _exec(conn,
              f"INSERT INTO users (id, email, password_hash, name, business_name, created_at)"
              f" VALUES ({PH},{PH},{PH},{PH},{PH},{PH})",
              (uid, email.lower().strip(), pw_hash, name, business_name, now))
        _exec(conn,
              f"INSERT INTO subscriptions (id, user_id, tier, status, created_at, updated_at)"
              f" VALUES ({PH},{PH},{PH},{PH},{PH},{PH})",
              (str(uuid.uuid4()), uid, "free", "active", now, now))
    return get_user_by_email(email)


def get_user_by_email(email: str) -> Optional[dict]:
    with get_conn() as conn:
        cur = _exec(conn, f"SELECT * FROM users WHERE email={PH}", (email.lower().strip(),))
        return _row(cur)


def get_user_by_id(uid: str) -> Optional[dict]:
    with get_conn() as conn:
        cur = _exec(conn, f"SELECT * FROM users WHERE id={PH}", (uid,))
        return _row(cur)


def verify_password(email: str, password: str) -> Optional[dict]:
    user = get_user_by_email(email)
    if not user:
        return None
    if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        with get_conn() as conn:
            _exec(conn, f"UPDATE users SET last_login={PH} WHERE id={PH}", (_now(), user["id"]))
        return user
    return None


def update_user(uid: str, **kwargs):
    allowed = {"name", "business_name", "avatar_url"}
    fields  = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    sql = ", ".join(f"{k}={PH}" for k in fields)
    with get_conn() as conn:
        _exec(conn, f"UPDATE users SET {sql} WHERE id={PH}", (*fields.values(), uid))


# ── Sessions ───────────────────────────────────────────────────────────────────

def create_session(user_id: str, days: int = 30) -> str:
    token   = str(uuid.uuid4())
    expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    now     = _now()
    with get_conn() as conn:
        _exec(conn, f"DELETE FROM sessions WHERE user_id={PH}", (user_id,))
        _exec(conn,
              f"INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES ({PH},{PH},{PH},{PH})",
              (token, user_id, expires, now))
    return token


def get_session(token: str) -> Optional[dict]:
    if not token:
        return None
    now = _now()
    with get_conn() as conn:
        cur = _exec(conn,
                    f"SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id"
                    f" WHERE s.token={PH} AND s.expires_at > {PH}",
                    (token, now))
        return _row(cur)


def delete_session(token: str):
    with get_conn() as conn:
        _exec(conn, f"DELETE FROM sessions WHERE token={PH}", (token,))


# ── Model Configs ──────────────────────────────────────────────────────────────

def get_model_config(model_type: str, tier: str) -> Optional[dict]:
    with get_conn() as conn:
        cur = _exec(conn,
                    f"SELECT * FROM model_configs WHERE model_type={PH} AND tier={PH}",
                    (model_type, tier))
        return _row(cur)


def get_all_model_configs() -> list:
    with get_conn() as conn:
        cur = _exec(conn, "SELECT * FROM model_configs ORDER BY model_type, tier")
        return _rows(cur)


def set_model_config(model_type: str, tier: str, model_id: Optional[str], provider: Optional[str]):
    with get_conn() as conn:
        cur     = _exec(conn,
                        f"SELECT id FROM model_configs WHERE model_type={PH} AND tier={PH}",
                        (model_type, tier))
        existing = _row(cur)
        if existing:
            _exec(conn,
                  f"UPDATE model_configs SET model_id={PH}, provider={PH}, updated_at={PH}"
                  f" WHERE model_type={PH} AND tier={PH}",
                  (model_id, provider, _now(), model_type, tier))
        else:
            _exec(conn,
                  f"INSERT INTO model_configs (id, model_type, tier, model_id, provider, updated_at)"
                  f" VALUES ({PH},{PH},{PH},{PH},{PH},{PH})",
                  (str(uuid.uuid4()), model_type, tier, model_id, provider, _now()))


# ── Subscriptions ──────────────────────────────────────────────────────────────

def get_subscription(user_id: str) -> dict:
    with get_conn() as conn:
        cur = _exec(conn,
                    f"SELECT * FROM subscriptions WHERE user_id={PH} ORDER BY created_at DESC LIMIT 1",
                    (user_id,))
        row = _row(cur)
        if row:
            return row
        sub_id = str(uuid.uuid4())
        now    = _now()
        _exec(conn,
              f"INSERT INTO subscriptions (id, user_id, tier, status, created_at, updated_at)"
              f" VALUES ({PH},{PH},{PH},{PH},{PH},{PH})",
              (sub_id, user_id, "free", "active", now, now))
        return {"id": sub_id, "user_id": user_id, "tier": "free", "status": "active"}


def update_subscription(user_id: str, **kwargs):
    fields = {**kwargs, "updated_at": _now()}
    sql    = ", ".join(f"{k}={PH}" for k in fields)
    with get_conn() as conn:
        _exec(conn, f"UPDATE subscriptions SET {sql} WHERE user_id={PH}",
              (*fields.values(), user_id))


# ── Platform Connections ───────────────────────────────────────────────────────

def upsert_platform_connection(user_id: str, platform: str, **kwargs) -> dict:
    conn_id = str(uuid.uuid4())
    now     = _now()
    fields  = {"id": conn_id, "user_id": user_id, "platform": platform,
               **kwargs, "updated_at": now}
    cols    = ", ".join(fields.keys())
    phs     = ", ".join([PH] * len(fields))
    updates = ", ".join(f"{k}=EXCLUDED.{k}" if USE_POSTGRES else f"{k}=excluded.{k}"
                        for k in fields if k not in ("id", "user_id", "platform"))
    conflict = "(user_id, platform)"
    sql = (f"INSERT INTO platform_connections ({cols}) VALUES ({phs})"
           f" ON CONFLICT {conflict} DO UPDATE SET {updates}")
    with get_conn() as conn:
        _exec(conn, sql, list(fields.values()))
    return get_platform_connection(user_id, platform)


def get_platform_connection(user_id: str, platform: str) -> Optional[dict]:
    with get_conn() as conn:
        cur = _exec(conn,
                    f"SELECT * FROM platform_connections WHERE user_id={PH} AND platform={PH}",
                    (user_id, platform))
        return _row(cur)


def get_all_connections(user_id: str) -> list:
    with get_conn() as conn:
        cur = _exec(conn,
                    f"SELECT * FROM platform_connections WHERE user_id={PH}", (user_id,))
        return _rows(cur)


def disconnect_platform(user_id: str, platform: str):
    with get_conn() as conn:
        _exec(conn,
              f"DELETE FROM platform_connections WHERE user_id={PH} AND platform={PH}",
              (user_id, platform))


# ── Posts ──────────────────────────────────────────────────────────────────────

def create_post(user_id: str, platform: str, content: str, **kwargs) -> dict:
    post_id = str(uuid.uuid4())
    now     = _now()
    fields  = {"id": post_id, "user_id": user_id, "platform": platform,
               "content": content, "created_at": now, "updated_at": now, **kwargs}
    cols    = ", ".join(fields.keys())
    phs     = ", ".join([PH] * len(fields))
    with get_conn() as conn:
        _exec(conn, f"INSERT INTO posts ({cols}) VALUES ({phs})", list(fields.values()))
    return get_post(post_id)


def get_post(post_id: str) -> Optional[dict]:
    with get_conn() as conn:
        cur = _exec(conn, f"SELECT * FROM posts WHERE id={PH}", (post_id,))
        return _row(cur)


def get_posts(user_id: str, platform: str = None, status: str = None,
              limit: int = 50, offset: int = 0) -> list:
    query  = f"SELECT * FROM posts WHERE user_id={PH}"
    params = [user_id]
    if platform:
        query += f" AND platform={PH}"; params.append(platform)
    if status:
        query += f" AND status={PH}";   params.append(status)
    query += f" ORDER BY created_at DESC LIMIT {PH} OFFSET {PH}"
    params += [limit, offset]
    with get_conn() as conn:
        cur = _exec(conn, query, params)
        return _rows(cur)


def update_post(post_id: str, **kwargs):
    kwargs["updated_at"] = _now()
    sql = ", ".join(f"{k}={PH}" for k in kwargs)
    with get_conn() as conn:
        _exec(conn, f"UPDATE posts SET {sql} WHERE id={PH}", (*kwargs.values(), post_id))


def get_scheduled_posts() -> list:
    now = _now()
    with get_conn() as conn:
        cur = _exec(conn,
                    f"SELECT * FROM posts WHERE status='scheduled' AND scheduled_at<={PH}",
                    (now,))
        return _rows(cur)


# ── Analytics ──────────────────────────────────────────────────────────────────

def upsert_post_analytics(post_id: str, user_id: str, platform: str, **metrics):
    now    = _now()
    fields = {"id": str(uuid.uuid4()), "post_id": post_id, "user_id": user_id,
              "platform": platform, **metrics, "recorded_at": now}
    cols   = ", ".join(fields.keys())
    phs    = ", ".join([PH] * len(fields))
    updates = ", ".join(
        f"{k}=EXCLUDED.{k}" if USE_POSTGRES else f"{k}=excluded.{k}"
        for k in fields if k != "id"
    )
    conflict = "(post_id, user_id, platform)"
    sql = (f"INSERT INTO post_analytics ({cols}) VALUES ({phs})"
           f" ON CONFLICT {conflict} DO UPDATE SET {updates}")
    with get_conn() as conn:
        _exec(conn, sql, list(fields.values()))


def get_analytics_summary(user_id: str, platform: str = None, days: int = 30) -> dict:
    since  = _ago(days)
    query  = f"""
        SELECT
            COUNT(DISTINCT p.id)                           AS total_posts,
            COALESCE(SUM(a.likes),        0)               AS total_likes,
            COALESCE(SUM(a.comments),     0)               AS total_comments,
            COALESCE(SUM(a.shares),       0)               AS total_shares,
            COALESCE(SUM(a.reach),        0)               AS total_reach,
            COALESCE(SUM(a.impressions),  0)               AS total_impressions,
            COALESCE(AVG(a.likes + a.comments + a.shares), 0) AS avg_engagement
        FROM posts p
        LEFT JOIN post_analytics a ON a.post_id = p.id
        WHERE p.user_id={PH} AND p.status='published'
        AND p.published_at >= {PH}
    """
    params = [user_id, since]
    if platform:
        query += f" AND p.platform={PH}"
        params.append(platform)
    with get_conn() as conn:
        cur = _exec(conn, query, params)
        return _row(cur) or {}


def get_posts_per_platform(user_id: str, days: int = 30) -> list:
    since = _ago(days)
    with get_conn() as conn:
        cur = _exec(conn, f"""
            SELECT platform, COUNT(*) AS count,
                   COALESCE(SUM(a.likes+a.comments+a.shares), 0) AS engagement
            FROM posts p
            LEFT JOIN post_analytics a ON a.post_id=p.id
            WHERE p.user_id={PH} AND p.status='published'
            AND p.published_at >= {PH}
            GROUP BY p.platform
        """, (user_id, since))
        return _rows(cur)


# ── AI Suggestions ─────────────────────────────────────────────────────────────

def save_suggestion(user_id: str, **kwargs) -> str:
    sid    = str(uuid.uuid4())
    fields = {"id": sid, "user_id": user_id, "created_at": _now(), **kwargs}
    cols   = ", ".join(fields.keys())
    phs    = ", ".join([PH] * len(fields))
    with get_conn() as conn:
        _exec(conn, f"INSERT INTO ai_suggestions ({cols}) VALUES ({phs})", list(fields.values()))
    return sid


def get_suggestions(user_id: str, status: str = "pending") -> list:
    query  = f"SELECT * FROM ai_suggestions WHERE user_id={PH}"
    params = [user_id]
    if status != "all":
        query += f" AND status={PH}"
        params.append(status)
    query += " ORDER BY CASE urgency WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END, created_at DESC LIMIT 50"
    with get_conn() as conn:
        cur = _exec(conn, query, params)
        return _rows(cur)


def update_suggestion(sid: str, status: str, msg: str = ""):
    with get_conn() as conn:
        _exec(conn,
              f"UPDATE ai_suggestions SET status={PH}, result_message={PH} WHERE id={PH}",
              (status, msg, sid))


# ── Usage Tracking ─────────────────────────────────────────────────────────────

def track_usage(user_id: str, action: str, platform: str = None):
    month_year = datetime.now().strftime("%Y-%m")
    plat       = platform or ""
    if USE_POSTGRES:
        sql = (
            f"INSERT INTO usage_tracking (id, user_id, action, platform, month_year, count)"
            f" VALUES ({PH},{PH},{PH},{PH},{PH},1)"
            f" ON CONFLICT (user_id, action, platform, month_year)"
            f" DO UPDATE SET count=usage_tracking.count+1"
        )
    else:
        sql = (
            "INSERT INTO usage_tracking (id, user_id, action, platform, month_year, count)"
            " VALUES (?,?,?,?,?,1)"
            " ON CONFLICT(user_id, action, platform, month_year)"
            " DO UPDATE SET count=count+1"
        )
    with get_conn() as conn:
        _exec(conn, sql, (str(uuid.uuid4()), user_id, action, plat, month_year))


def get_usage(user_id: str, action: str = None) -> dict:
    month_year = datetime.now().strftime("%Y-%m")
    query      = f"SELECT action, platform, SUM(count) AS total FROM usage_tracking WHERE user_id={PH} AND month_year={PH}"
    params     = [user_id, month_year]
    if action:
        query += f" AND action={PH}"
        params.append(action)
    query += " GROUP BY action, platform"
    with get_conn() as conn:
        cur  = _exec(conn, query, params)
        rows = _rows(cur)
    return {f"{r['action']}_{r['platform'] or 'any'}": r['total'] for r in rows}


# ── Business Profiles ──────────────────────────────────────────────────────────

def upsert_business_profile(user_id: str, **kwargs) -> dict:
    now = _now()
    with get_conn() as conn:
        cur      = _exec(conn, f"SELECT id FROM business_profiles WHERE user_id={PH}", (user_id,))
        existing = _row(cur)
        kwargs["updated_at"] = now
        if existing:
            sql = ", ".join(f"{k}={PH}" for k in kwargs)
            _exec(conn, f"UPDATE business_profiles SET {sql} WHERE user_id={PH}",
                  (*kwargs.values(), user_id))
        else:
            pid    = str(uuid.uuid4())
            fields = {"id": pid, "user_id": user_id, "created_at": now, **kwargs}
            cols   = ", ".join(fields.keys())
            phs    = ", ".join([PH] * len(fields))
            _exec(conn, f"INSERT INTO business_profiles ({cols}) VALUES ({phs})",
                  list(fields.values()))
    return get_business_profile(user_id)


def get_business_profile(user_id: str) -> Optional[dict]:
    with get_conn() as conn:
        cur = _exec(conn, f"SELECT * FROM business_profiles WHERE user_id={PH}", (user_id,))
        return _row(cur)


# ── Ad Campaigns ───────────────────────────────────────────────────────────────

def create_campaign(user_id: str, title: str, **kwargs) -> dict:
    cid    = str(uuid.uuid4())
    now    = _now()
    fields = {"id": cid, "user_id": user_id, "title": title,
              "created_at": now, "updated_at": now, **kwargs}
    cols   = ", ".join(fields.keys())
    phs    = ", ".join([PH] * len(fields))
    with get_conn() as conn:
        _exec(conn, f"INSERT INTO ad_campaigns ({cols}) VALUES ({phs})", list(fields.values()))
    return get_campaign(cid)


def get_campaign(campaign_id: str) -> Optional[dict]:
    with get_conn() as conn:
        cur = _exec(conn, f"SELECT * FROM ad_campaigns WHERE id={PH}", (campaign_id,))
        return _row(cur)


def get_campaigns(user_id: str, status: str = None) -> list:
    query  = f"SELECT * FROM ad_campaigns WHERE user_id={PH}"
    params = [user_id]
    if status:
        query += f" AND status={PH}"
        params.append(status)
    query += " ORDER BY created_at DESC"
    with get_conn() as conn:
        cur = _exec(conn, query, params)
        return _rows(cur)


def update_campaign(campaign_id: str, **kwargs):
    kwargs["updated_at"] = _now()
    sql = ", ".join(f"{k}={PH}" for k in kwargs)
    with get_conn() as conn:
        _exec(conn, f"UPDATE ad_campaigns SET {sql} WHERE id={PH}",
              (*kwargs.values(), campaign_id))


# ── Campaign Items ─────────────────────────────────────────────────────────────

def create_campaign_items(campaign_id: str, user_id: str, items: list) -> list:
    now     = _now()
    created = []
    with get_conn() as conn:
        for item in items:
            iid    = str(uuid.uuid4())
            fields = {"id": iid, "campaign_id": campaign_id, "user_id": user_id,
                      "created_at": now, **item}
            cols   = ", ".join(fields.keys())
            phs    = ", ".join([PH] * len(fields))
            _exec(conn, f"INSERT INTO campaign_items ({cols}) VALUES ({phs})",
                  list(fields.values()))
            created.append(iid)
    return created


def get_campaign_items(campaign_id: str) -> list:
    with get_conn() as conn:
        cur = _exec(conn,
                    f"SELECT * FROM campaign_items WHERE campaign_id={PH}"
                    f" ORDER BY scheduled_date, platform",
                    (campaign_id,))
        return _rows(cur)


def update_campaign_item(item_id: str, **kwargs):
    sql = ", ".join(f"{k}={PH}" for k in kwargs)
    with get_conn() as conn:
        _exec(conn, f"UPDATE campaign_items SET {sql} WHERE id={PH}",
              (*kwargs.values(), item_id))


# ── Owner / Role Management ────────────────────────────────────────────────────

def is_owner(user_id: str) -> bool:
    with get_conn() as conn:
        cur = _exec(conn, f"SELECT role FROM users WHERE id={PH}", (user_id,))
        row = _row(cur)
    return bool(row and row.get("role") == "owner")


def set_user_role(user_id: str, role: str):
    with get_conn() as conn:
        _exec(conn, f"UPDATE users SET role={PH} WHERE id={PH}", (role, user_id))


def get_all_users(exclude_owner: bool = False) -> list:
    owner_email = os.environ.get("OWNER_EMAIL", "").lower().strip()
    with get_conn() as conn:
        if exclude_owner and owner_email:
            cur = _exec(conn,
                        f"SELECT * FROM users WHERE email!={PH} ORDER BY created_at DESC",
                        (owner_email,))
        else:
            cur = _exec(conn, "SELECT * FROM users ORDER BY created_at DESC")
        return _rows(cur)


# ── Model Preferences ──────────────────────────────────────────────────────────

def set_preferred_model(user_id: str, model_id: str, provider: str):
    upsert_business_profile(user_id, preferred_model=model_id, preferred_provider=provider)


def get_preferred_model(user_id: str) -> tuple:
    profile = get_business_profile(user_id)
    if profile:
        model    = profile.get("preferred_model")    or "claude-sonnet-4-6"
        provider = profile.get("preferred_provider") or "anthropic"
        return model, provider
    return "claude-sonnet-4-6", "anthropic"
