"""
Project Glass X - SQLite database layer (local only)
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent / "data" / "glassx.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()

    # Settings (key-value style for flexibility)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Scheduled posts (the queue)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_json TEXT NOT NULL,           -- JSON: [{text, ...}, ...] for threads
            scheduled_at TEXT NOT NULL,           -- ISO format
            status TEXT DEFAULT 'pending',        -- pending | posted | failed | cancelled
            media_paths_json TEXT,                -- JSON array of local file paths
            virality_score INTEGER,
            virality_grade TEXT,
            posted_tweet_ids TEXT,                -- JSON array after successful post
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # History of everything that was attempted (for analytics)
    c.execute("""
        CREATE TABLE IF NOT EXISTS post_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheduled_post_id INTEGER,
            tweet_id TEXT,
            text TEXT,
            posted_at TEXT,
            impressions INTEGER,
            likes INTEGER,
            reposts INTEGER,
            replies INTEGER,
            bookmarks INTEGER,
            virality_score_at_post INTEGER,
            FOREIGN KEY (scheduled_post_id) REFERENCES scheduled_posts(id)
        )
    """)

    # Simple cache for analytics computations
    c.execute("""
        CREATE TABLE IF NOT EXISTS analytics_cache (
            key TEXT PRIMARY KEY,
            value_json TEXT,
            computed_at TEXT
        )
    """)

    # FUTURE: Per-account performance history
    # Supports multiple advantages:
    # - Personalization (learns your specific patterns)
    # - Data Ownership & Portability (users can export everything)
    # - Lower long-term dependency
    # See COMPETITIVE_ADVANTAGES.md for full list (advantages #2, #7, #8, #9).
    c.execute("""
        CREATE TABLE IF NOT EXISTS account_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,           -- e.g. X username or internal account ref
            post_id TEXT,
            posted_at TEXT,
            impressions INTEGER,
            engagements INTEGER,
            replies INTEGER,
            reposts INTEGER,
            likes INTEGER,
            content_features_json TEXT,         -- e.g. had_question, length, media_count, etc.
            virality_score_at_post INTEGER,
            UNIQUE(account_id, post_id)
        )
    """)

    conn.commit()
    conn.close()


def get_setting(key: str, default: str | None = None) -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        (key, value, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def create_scheduled_post(
    content_json: str,
    scheduled_at: str,
    media_paths_json: str | None = None,
    virality_score: int | None = None,
    virality_grade: str | None = None,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO scheduled_posts 
        (content_json, scheduled_at, media_paths_json, virality_score, virality_grade)
        VALUES (?, ?, ?, ?, ?)
        """,
        (content_json, scheduled_at, media_paths_json, virality_score, virality_grade)
    )
    post_id = cur.lastrowid
    conn.commit()
    conn.close()
    return post_id


def get_pending_posts(limit: int = 50) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM scheduled_posts 
        WHERE status = 'pending' AND scheduled_at <= ?
        ORDER BY scheduled_at ASC
        LIMIT ?
        """,
        (datetime.utcnow().isoformat(), limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_post_status(post_id: int, status: str, **kwargs) -> None:
    conn = get_connection()
    sets = ["status = ?", "updated_at = ?"]
    values = [status, datetime.utcnow().isoformat()]
    for k, v in kwargs.items():
        sets.append(f"{k} = ?")
        values.append(v)
    values.append(post_id)
    conn.execute(f"UPDATE scheduled_posts SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_upcoming_posts(limit: int = 30) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM scheduled_posts 
        WHERE status = 'pending'
        ORDER BY scheduled_at ASC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_history(limit: int = 100) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM post_history ORDER BY posted_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
