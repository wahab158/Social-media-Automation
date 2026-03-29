import sqlite3
import uuid
import json
from datetime import datetime
from crypto_helper import encrypt_value, decrypt_value, mask_key

DB_PATH = "autopost.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database with all necessary tables."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id         TEXT PRIMARY KEY,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            name       TEXT,
            created_at TEXT NOT NULL,
            last_login TEXT
        );

        CREATE TABLE IF NOT EXISTS user_api_keys (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            service         TEXT NOT NULL,
            key_name        TEXT NOT NULL,
            encrypted_value TEXT NOT NULL,
            is_active       INTEGER DEFAULT 1,
            verified        INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            UNIQUE(user_id, service, key_name)
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            user_id        TEXT PRIMARY KEY,
            news_provider  TEXT DEFAULT 'rss',
            llm_provider   TEXT DEFAULT 'openai',
            post_time      TEXT DEFAULT '07:00',
            post_day       TEXT DEFAULT 'Monday',
            tone           TEXT DEFAULT 'professional',
            topics         TEXT DEFAULT '',
            is_enabled     INTEGER DEFAULT 1,
            news_limit     INTEGER DEFAULT 10,
            updated_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS brand_profiles (
            id                 TEXT PRIMARY KEY,
            user_id            TEXT NOT NULL,
            name               TEXT NOT NULL,
            system_instruction TEXT,
            logo_light_url     TEXT,
            logo_dark_url      TEXT,
            primary_color      TEXT,
            secondary_color    TEXT,
            font_name          TEXT,
            contact_json       TEXT,
            dna_config_json    TEXT, /* Stores: archetype, emoji_strategy, core_values */
            platform_toggles   TEXT,
            topics_include     TEXT,
            topics_exclude     TEXT,
            is_active          BOOLEAN DEFAULT 1,
            created_at         TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS analytics (
            id TEXT PRIMARY KEY, brand_id TEXT, platform TEXT, post_id TEXT, engagement_score REAL, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS platform_timing (
            id TEXT PRIMARY KEY, brand_id TEXT, platform TEXT, day_of_week TEXT, hour TEXT, score REAL
        );
        CREATE TABLE IF NOT EXISTS agent_runs (
            id TEXT PRIMARY KEY, brand_id TEXT, status TEXT, started_at TEXT, completed_at TEXT, log TEXT
        );
        CREATE TABLE IF NOT EXISTS whatsapp_subscribers (
            id TEXT PRIMARY KEY, brand_id TEXT, phone_number TEXT, name TEXT, opted_in BOOLEAN, created_at TEXT
        );
    """)
    conn.commit()

    # Apply safe migrations for existing tables
    try:
        conn.execute("ALTER TABLE brand_profiles ADD COLUMN platform_toggles TEXT")
        conn.execute("ALTER TABLE brand_profiles ADD COLUMN topics_include TEXT")
        conn.execute("ALTER TABLE brand_profiles ADD COLUMN topics_exclude TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        conn.execute("ALTER TABLE content_drafts ADD COLUMN version INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    print("SQLite: Database initialized (Phase 3 with Orchestrator schema).")

# ── User Operations ──────────────────────────────────────────────

def create_user(user_data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (id, email, password, name, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_data["id"], user_data["email"], user_data["password"],
         user_data.get("name", ""), user_data["created_at"])
    )
    conn.commit()
    conn.close()

def get_user_by_email(email: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_last_login(user_id: str):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), user_id)
    )
    conn.commit()
    conn.close()

# ── API Key Operations ───────────────────────────────────────────

def save_api_key(user_id: str, service: str, key_name: str, value: str):
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_api_keys
            (id, user_id, service, key_name, encrypted_value, is_active, verified, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?)
        ON CONFLICT(user_id, service, key_name)
        DO UPDATE SET encrypted_value = excluded.encrypted_value,
                      updated_at = excluded.updated_at,
                      verified = 0,
                      is_active = 1
    """, (str(uuid.uuid4()), user_id, service, key_name, encrypt_value(value), now, now))
    conn.commit()
    conn.close()

def get_api_key(user_id: str, service: str, key_name: str) -> str | None:
    conn = get_connection()
    row = conn.execute("""
        SELECT encrypted_value FROM user_api_keys
        WHERE user_id = ? AND service = ? AND key_name = ? AND is_active = 1
    """, (user_id, service, key_name)).fetchone()
    conn.close()
    return decrypt_value(row["encrypted_value"]) if row else None

def get_all_keys_masked(user_id: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT service, key_name, encrypted_value, verified, is_active, updated_at FROM user_api_keys WHERE user_id = ? AND is_active = 1",
        (user_id,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["masked_value"] = mask_key(decrypt_value(d["encrypted_value"]))
        del d["encrypted_value"]
        result.append(d)
    return result

def mark_key_verified(user_id: str, service: str, key_name: str, verified: bool = True):
    conn = get_connection()
    conn.execute(
        "UPDATE user_api_keys SET verified = ? WHERE user_id = ? AND service = ? AND key_name = ?",
        (1 if verified else 0, user_id, service, key_name)
    )
    conn.commit()
    conn.close()

def delete_api_key(user_id: str, service: str, key_name: str):
    conn = get_connection()
    conn.execute(
        "UPDATE user_api_keys SET is_active = 0 WHERE user_id = ? AND service = ? AND key_name = ?",
        (user_id, service, key_name)
    )
    conn.commit()
    conn.close()

# ── User Settings Operations ─────────────────────────────────────

def get_user_settings(user_id: str) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "user_id": user_id,
        "news_provider": "rss",
        "llm_provider": "openai",
        "post_time": "07:00",
        "post_day": "Monday",
        "tone": "professional",
        "topics": "",
        "is_enabled": 1,
        "news_limit": 10,
        "updated_at": datetime.utcnow().isoformat()
    }

def save_user_settings(user_id: str, data: dict):
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO user_settings (user_id, news_provider, llm_provider, post_time, post_day, tone, topics, is_enabled, news_limit, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            news_provider = excluded.news_provider,
            llm_provider = excluded.llm_provider,
            post_time = excluded.post_time,
            post_day = excluded.post_day,
            tone = excluded.tone,
            topics = excluded.topics,
            is_enabled = excluded.is_enabled,
            news_limit = excluded.news_limit,
            updated_at = excluded.updated_at
    """, (
        user_id,
        data.get("news_provider", "rss"),
        data.get("llm_provider", "openai"),
        data.get("post_time", "07:00"),
        data.get("post_day", "Monday"),
        data.get("tone", "professional"),
        data.get("topics", ""),
        data.get("is_enabled", 1),
        data.get("news_limit", 10),
        now
    ))
    conn.commit()
    conn.close()

# ── Brand Profile Operations ─────────────────────────────────────

def get_brand_profiles(user_id: str) -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM brand_profiles WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_brand_profile(user_id: str, data: dict):
    conn = get_connection()
    profile_id = data.get("id") or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    # Deactivate others if this is being set to active
    if data.get("is_active"):
        conn.execute("UPDATE brand_profiles SET is_active = 0 WHERE user_id = ?", (user_id,))

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO brand_profiles (id, user_id, name, system_instruction, logo_light_url, logo_dark_url, primary_color, secondary_color, font_name, contact_json, dna_config_json, platform_toggles, topics_include, topics_exclude, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET 
            name = excluded.name,
            system_instruction = excluded.system_instruction,
            logo_light_url = excluded.logo_light_url,
            logo_dark_url = excluded.logo_dark_url,
            primary_color = excluded.primary_color,
            secondary_color = excluded.secondary_color,
            font_name = excluded.font_name,
            contact_json = excluded.contact_json,
            dna_config_json = excluded.dna_config_json,
            platform_toggles = excluded.platform_toggles,
            topics_include = excluded.topics_include,
            topics_exclude = excluded.topics_exclude,
            is_active = excluded.is_active
    """, (profile_id, user_id, data["name"], data.get("system_instruction"), data.get("logo_light_url"), data.get("logo_dark_url"), 
          data.get("primary_color"), data.get("secondary_color"), data.get("font_name"), 
          json.dumps(data.get("contact_json", {})) if isinstance(data.get("contact_json"), dict) else data.get("contact_json"), 
          json.dumps(data.get("dna_config_json", {})) if isinstance(data.get("dna_config_json"), dict) else data.get("dna_config_json"), 
          json.dumps(data.get("platform_toggles", {})) if isinstance(data.get("platform_toggles"), dict) else data.get("platform_toggles"), 
          json.dumps(data.get("topics_include", [])) if isinstance(data.get("topics_include"), list) else data.get("topics_include"), 
          json.dumps(data.get("topics_exclude", [])) if isinstance(data.get("topics_exclude"), list) else data.get("topics_exclude"), 
          data.get("is_active", 1), now))
    conn.commit()
    conn.close()
    return profile_id
