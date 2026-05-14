"""
scripts/init_db.py
==================
Manually initialize or reset the SQLite database.

Usage:
    python scripts/init_db.py           # Create tables (safe, won't drop existing)
    python scripts/init_db.py --reset   # DROP all tables and recreate (DELETES ALL DATA)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from backend.core.database import init_db, get_db
from backend.config import Config


def reset_db():
    """Drop all tables and recreate schema. WARNING: deletes all data."""
    print("⚠️  RESETTING DATABASE — all data will be deleted!")
    confirm = input("Type 'yes' to confirm: ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return

    with get_db() as conn:
        conn.execute("DROP TABLE IF EXISTS feedback")
        conn.execute("DROP TABLE IF EXISTS messages")
        conn.execute("DROP TABLE IF EXISTS sessions")
        conn.execute("DROP TABLE IF EXISTS users")
    print("✅ All tables dropped.")
    init_db()
    print("✅ Database recreated.")


def show_stats():
    """Print a quick summary of what's in the database."""
    with get_db() as conn:
        users    = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        feedback = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]

    print(f"\n📊 Database contents:")
    print(f"   Users:    {users}")
    print(f"   Sessions: {sessions}")
    print(f"   Messages: {messages}")
    print(f"   Feedback: {feedback}")
    print(f"   Path:     {Config.DATABASE_PATH}\n")


if __name__ == '__main__':
    if '--reset' in sys.argv:
        reset_db()
    else:
        init_db()

    show_stats()
