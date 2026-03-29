import sqlite3
import uuid
import json
from datetime import datetime

DB_PATH = "autopost.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_content_db():
    """Initialize content-related tables in SQLite."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS news_items (
            news_id      TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            title        TEXT NOT NULL,
            summary      TEXT,
            category     TEXT,
            source_url   TEXT,
            date_found   TEXT,
            status       TEXT DEFAULT 'New',
            source_name  TEXT,
            relevance_score TEXT,
            media_url    TEXT,
            user_id      TEXT,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS posts (
            id                TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            brand_id          TEXT,
            topic             TEXT,
            content_category  TEXT,
            type              TEXT,
            platforms_json    TEXT,
            caption_instagram TEXT,
            caption_linkedin  TEXT,
            caption_facebook  TEXT,
            caption_tiktok    TEXT,
            caption_x         TEXT,
            image_urls_json   TEXT,
            video_urls_json   TEXT,
            metadata          TEXT,
            scheduled_time    TEXT,
            status            TEXT DEFAULT 'generated',
            version           INTEGER DEFAULT 0,
            created_at        TEXT DEFAULT CURRENT_TIMESTAMP,
            published_at      TEXT,
            publish_url       TEXT
        );

        CREATE TABLE IF NOT EXISTS analytics (
            id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            post_id          TEXT,
            platform         TEXT,
            likes            INTEGER DEFAULT 0,
            comments         INTEGER DEFAULT 0,
            shares           INTEGER DEFAULT 0,
            saves            INTEGER DEFAULT 0,
            reach            INTEGER DEFAULT 0,
            impressions      INTEGER DEFAULT 0,
            engagement_score REAL DEFAULT 0,
            fetched_at       TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS platform_timing (
            id             TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            brand_id       TEXT,
            platform       TEXT,
            time_window    TEXT,
            avg_score      REAL DEFAULT 0,
            sample_count   INTEGER DEFAULT 0,
            last_updated   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS agent_runs (
            id             TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            brand_id       TEXT,
            run_type       TEXT,
            status         TEXT,
            tasks_total    INTEGER DEFAULT 0,
            tasks_complete INTEGER DEFAULT 0,
            error_log      TEXT,
            started_at     TEXT,
            completed_at   TEXT
        );
    """)
    conn.commit()
    conn.close()
    print("SQLite: Content tables initialized (Phase 3).")

# ── News Operations ──────────────────────────────────────────────

def add_news_row(title, summary, category, source_url, date_found,
                 status="New", source_name="", relevance_score="", media_url="", user_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    # Duplicate check
    row = cursor.execute("SELECT 1 FROM news_items WHERE source_url = ? OR title = ?", (source_url, title)).fetchone()
    if row:
        conn.close()
        return False
    news_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO news_items (news_id, title, summary, category, source_url, date_found, status, source_name, relevance_score, media_url, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (news_id, title, summary, category, source_url, str(date_found), status, source_name, str(relevance_score), media_url or "", user_id))
    conn.commit()
    conn.close()
    return True

def get_all_news():
    conn = get_connection()
    rows = conn.execute("SELECT *, news_id as _id FROM news_items ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_news_by_id(news_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM news_items WHERE news_id = ?", (news_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# ── Post Queue Operations ────────────────────────────────────────

def create_post(brand_id, data):
    """Creates a post entry in the 'posts' table."""
    conn = get_connection()
    post_id = str(uuid.uuid4())
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO posts (id, brand_id, topic, content_category, type, platforms_json, caption_instagram, caption_linkedin, caption_facebook, caption_tiktok, caption_x, image_urls_json, video_urls_json, metadata, scheduled_time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (post_id, brand_id, data.get('topic'), data.get('category'), data.get('type'), 
          json.dumps(data.get('platforms', [])), data.get('ig_caption'), data.get('li_caption'), 
          data.get('fb_caption'), data.get('tt_caption'), data.get('x_caption'),
          json.dumps(data.get('image_urls', [])), json.dumps(data.get('video_urls', [])),
          data.get('metadata'), data.get('scheduled_time'), data.get('status', 'generated')))
    conn.commit()
    conn.close()
    return post_id

def get_posts_by_range(brand_id, start_date, end_date):
    """Fetch posts for the calendar view."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM posts 
        WHERE brand_id = ? AND scheduled_time BETWEEN ? AND ?
        ORDER BY scheduled_time ASC
    """, (brand_id, start_date, end_date)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_post_status(post_id, new_status, publish_url=None):
    conn = get_connection()
    cursor = conn.cursor()
    if publish_url:
        cursor.execute("UPDATE posts SET status = ?, publish_url = ?, published_at = ? WHERE id = ?", 
                       (new_status, publish_url, datetime.utcnow().isoformat(), post_id))
    else:
        cursor.execute("UPDATE posts SET status = ? WHERE id = ?", (new_status, post_id))
    conn.commit()
    conn.close()
