"""
backend/core/database.py
========================
SQLite database setup using Python's built-in sqlite3 module.
FR1: Database connection setup.

Tables created:
  - users      : authenticated users (Google OAuth)
  - sessions   : chat sessions per user
  - messages   : individual messages within sessions
  - feedback   : user ratings per AI response
"""

import sqlite3
import os
from contextlib import contextmanager
from backend.config import Config


# ── Connection Factory ────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """
    Open a new SQLite connection with row_factory set to Row
    so results can be accessed like dicts: row['column_name'].
    """
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row          # Access columns by name
    conn.execute("PRAGMA journal_mode=WAL") # Better concurrent read performance
    conn.execute("PRAGMA foreign_keys=ON")  # Enforce FK constraints
    return conn


@contextmanager
def get_db():
    """
    Context manager for database access.
    Automatically commits on success, rolls back on exception.

    Usage:
        with get_db() as db:
            db.execute("INSERT INTO ...")
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema Initialization ─────────────────────────────────────────────────────

def init_db():
    """
    Create all tables if they don't already exist.
    Called once at app startup (FR1: Database connection setup).
    Safe to call multiple times — uses IF NOT EXISTS.
    """
    # Ensure the database directory exists
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)

    with get_db() as conn:

        # ── users table ───────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,           -- Google 'sub' (unique ID)
                email       TEXT UNIQUE NOT NULL,
                name        TEXT NOT NULL,
                picture     TEXT,                       -- Profile photo URL
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── sessions table ────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,           -- UUID
                user_id     TEXT NOT NULL,
                title       TEXT DEFAULT 'New Chat',    -- First user message (truncated)
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ── messages table ────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          TEXT PRIMARY KEY,           -- UUID
                session_id  TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                role        TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content     TEXT NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                FOREIGN KEY (user_id)    REFERENCES users(id)
            )
        """)

        # ── feedback table ────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id              TEXT PRIMARY KEY,       -- UUID
                message_id      TEXT NOT NULL,          -- The AI message being rated
                session_id      TEXT NOT NULL,
                user_id         TEXT NOT NULL,
                rating          INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                correctness     TEXT NOT NULL CHECK(correctness IN
                                    ('correct','partially_correct','incorrect')),
                length_rating   TEXT NOT NULL CHECK(length_rating IN
                                    ('too_short','just_right','too_long')),
                comment         TEXT,
                submitted_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages(id),
                FOREIGN KEY (user_id)    REFERENCES users(id)
            )
        """)

        # ── Indexes for fast queries ───────────────────────────────────────────
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user    ON messages(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user    ON sessions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback(message_id)")

    print(f"[DB] ✅ SQLite database initialized at: {Config.DATABASE_PATH}")
