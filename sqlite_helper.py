import sqlite3
import uuid
from datetime import datetime
from crypto_helper import encrypt_value, decrypt_value, mask_key

DB_PATH = "autopost.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Run once on startup to create all tables."""
    conn = get_connection()
    conn.executescript("""
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
            tone           TEXT DEFAULT 'professional',
            topics         TEXT DEFAULT '',
            is_enabled     INTEGER DEFAULT 1,
            updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
    print("SQLite: Database initialized.")


# ── User Operations ──────────────────────────────────────────────

def create_user(user_data: dict):
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (id, email, password, name, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_data["id"], user_data["email"], user_data["password"],
         user_data.get("name", ""), user_data["created_at"])
    )
    conn.commit()
    conn.close()


def get_user_by_email(email: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
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
    """Encrypts and saves. Overwrites if key already exists for this user+service+key_name."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO user_api_keys
            (id, user_id, service, key_name, encrypted_value,
             is_active, verified, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?)
        ON CONFLICT(user_id, service, key_name)
        DO UPDATE SET encrypted_value = excluded.encrypted_value,
                      updated_at = excluded.updated_at,
                      verified = 0,
                      is_active = 1
    """, (str(uuid.uuid4()), user_id, service, key_name,
          encrypt_value(value), now, now))
    conn.commit()
    conn.close()


def get_api_key(user_id: str, service: str, key_name: str) -> str | None:
    """Returns decrypted key value or None if not found."""
    conn = get_connection()
    row = conn.execute("""
        SELECT encrypted_value FROM user_api_keys
        WHERE user_id = ? AND service = ? AND key_name = ? AND is_active = 1
    """, (user_id, service, key_name)).fetchone()
    conn.close()
    if not row:
        return None
    return decrypt_value(row["encrypted_value"])


def get_all_keys_masked(user_id: str) -> list:
    """Returns all keys for a user with values masked for UI display."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT service, key_name, encrypted_value, verified, updated_at
        FROM user_api_keys
        WHERE user_id = ? AND is_active = 1
        ORDER BY service, key_name
    """, (user_id,)).fetchall()
    conn.close()
    return [{
        "service":    r["service"],
        "key_name":   r["key_name"],
        "masked":     mask_key(decrypt_value(r["encrypted_value"])),
        "verified":   bool(r["verified"]),
        "updated_at": r["updated_at"],
    } for r in rows]


def mark_key_verified(user_id: str, service: str, key_name: str):
    conn = get_connection()
    conn.execute("""
        UPDATE user_api_keys SET verified = 1
        WHERE user_id = ? AND service = ? AND key_name = ?
    """, (user_id, service, key_name))
    conn.commit()
    conn.close()


def delete_api_key(user_id: str, service: str, key_name: str):
    conn = get_connection()
    conn.execute("""
        UPDATE user_api_keys SET is_active = 0
        WHERE user_id = ? AND service = ? AND key_name = ?
    """, (user_id, service, key_name))
    conn.commit()
    conn.close()


# ── User Settings Operations ────────────────────────────────────

def get_user_settings(user_id: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_settings WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return {
            "news_provider": "rss",
            "llm_provider": "openai",
            "post_time": "07:00",
            "tone": "professional",
            "topics": "",
            "is_enabled": 1,
        }
    return dict(row)


def save_user_settings(user_id: str, settings: dict):
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO user_settings (user_id, news_provider, llm_provider, post_time, tone, topics, is_enabled, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET news_provider = excluded.news_provider,
                      llm_provider = excluded.llm_provider,
                      post_time = excluded.post_time,
                      tone = excluded.tone,
                      topics = excluded.topics,
                      is_enabled = excluded.is_enabled,
                      updated_at = excluded.updated_at
    """, (user_id,
          settings.get("news_provider", "rss"),
          settings.get("llm_provider", "openai"),
          settings.get("post_time", "07:00"),
          settings.get("tone", "professional"),
          settings.get("topics", ""),
          settings.get("is_enabled", 1),
          now))
    conn.commit()
    conn.close()
