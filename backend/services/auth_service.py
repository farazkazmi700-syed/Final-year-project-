"""
backend/services/auth_service.py
=================================
User management: create or update users on login.
FR3: User authentication & session creation.
"""

from datetime import datetime
from backend.core.database import get_db


def upsert_user(google_id: str, email: str, name: str, picture: str = None) -> dict:
    """
    Create a new user or update an existing user's profile on login.
    Uses INSERT OR REPLACE so it's safe to call every time a user logs in.

    Args:
        google_id: The user's unique Google 'sub' identifier.
        email:     User's Gmail address.
        name:      Display name from Google profile.
        picture:   Profile photo URL (optional).

    Returns:
        Dict representation of the user record.
    """
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        # Check if user already exists
        existing = conn.execute(
            "SELECT id FROM users WHERE id = ?", (google_id,)
        ).fetchone()

        if existing:
            # Update login timestamp and profile info (name/picture may change)
            conn.execute(
                """
                UPDATE users
                SET name = ?, picture = ?, last_login = ?
                WHERE id = ?
                """,
                (name, picture, now, google_id)
            )
        else:
            # Create new user record
            conn.execute(
                """
                INSERT INTO users (id, email, name, picture, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (google_id, email, name, picture, now, now)
            )

    return {"id": google_id, "email": email, "name": name, "picture": picture}


def get_user_by_id(user_id: str) -> dict | None:
    """
    Fetch a user record by ID.

    Returns:
        User dict or None if not found.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, name, picture, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

    if row:
        return dict(row)
    return None
