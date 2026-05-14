"""
backend/services/chat_service.py
=================================
Core multi-turn chat logic.
FR3: Message routing | FR4: LLaMA 3 inference | FR5: Service connectivity.

Pipeline for every user message:
  1. Get or create session
  2. Load full conversation history from SQLite
  3. Save user message
  4. Send history → Groq (LLaMA 3) → get response
  5. Save assistant response
  6. Return result to route handler
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict
from backend.core.database import get_db
from backend.core.groq_client import generate_response


def get_or_create_session(user_id: str, session_id: Optional[str] = None) -> str:
    """
    Return an existing session ID or create a new one.

    Args:
        user_id:    The authenticated user's ID.
        session_id: Existing session ID from frontend (or None).

    Returns:
        A valid session_id string.
    """
    with get_db() as conn:
        if session_id:
            # Verify this session belongs to the user
            row = conn.execute(
                "SELECT id FROM sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id)
            ).fetchone()
            if row:
                return session_id  # Valid existing session

        # Create a brand new session
        new_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO sessions (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (new_id, user_id, "New Chat", now, now)
        )
        return new_id


def load_conversation_history(session_id: str, user_id: str) -> List[Dict[str, str]]:
    """
    Load all messages in a session as LLaMA-ready dicts.
    Ordered oldest → newest for proper multi-turn context.

    Returns:
        List of {"role": "user"/"assistant", "content": "..."} dicts.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM messages
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at ASC
            """,
            (session_id, user_id)
        ).fetchall()

    return [{"role": row["role"], "content": row["content"]} for row in rows]


def _update_session_title(conn, session_id: str, first_message: str):
    """
    Set the session title to the first user message (truncated to 50 chars).
    Only updates if title is still the default 'New Chat'.
    """
    title = first_message[:50] + ("..." if len(first_message) > 50 else "")
    conn.execute(
        "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ? AND title = 'New Chat'",
        (title, datetime.utcnow().isoformat(), session_id)
    )


def process_message(user_id: str, content: str, session_id: Optional[str] = None) -> dict:
    """
    Full message processing pipeline (FR3 + FR4 + FR5).

    Args:
        user_id:    Authenticated user's ID.
        content:    The user's message text.
        session_id: Existing session or None to start a new one.

    Returns:
        {
            "session_id":  str,
            "message_id":  str,   # ID of the assistant's response message
            "response":    str,   # The AI's text response
            "timestamp":   str,
        }
    """
    # ── Step 1: Resolve session ───────────────────────────────────────────────
    session_id = get_or_create_session(user_id, session_id)

    # ── Step 2: Load history for multi-turn context ───────────────────────────
    history = load_conversation_history(session_id, user_id)

    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        # ── Step 3: Save user message ─────────────────────────────────────────
        user_msg_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO messages (id, session_id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_msg_id, session_id, user_id, "user", content, now)
        )

        # Update session title from first message
        _update_session_title(conn, session_id, content)

    # ── Step 4: Call LLaMA 3 via Groq ────────────────────────────────────────
    history.append({"role": "user", "content": content})

    try:
        ai_text = generate_response(history)
    except ConnectionError:
        ai_text = "⚠️ Cannot reach the AI service. Please check your GROQ_API_KEY."
    except RuntimeError as e:
        ai_text = f"⚠️ AI error: {str(e)}"
    except Exception as e:
        ai_text = f"⚠️ Unexpected error: {str(e)}"

    # ── Step 5: Save assistant response ──────────────────────────────────────
    assistant_msg_id = str(uuid.uuid4())
    response_time = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (id, session_id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (assistant_msg_id, session_id, user_id, "assistant", ai_text, response_time)
        )
        # Update session's updated_at timestamp
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (response_time, session_id)
        )

    return {
        "session_id": session_id,
        "message_id": assistant_msg_id,
        "response":   ai_text,
        "timestamp":  response_time,
    }


def get_user_sessions(user_id: str) -> List[dict]:
    """
    Get all sessions for a user with message counts and last preview.
    Used to populate the session list panel in the UI.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.title,
                s.created_at,
                s.updated_at,
                COUNT(m.id) AS message_count,
                MAX(m.content) AS last_message
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            WHERE s.user_id = ?
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            """,
            (user_id,)
        ).fetchall()

    return [
        {
            "session_id":    row["id"],
            "title":         row["title"],
            "created_at":    row["created_at"],
            "updated_at":    row["updated_at"],
            "message_count": row["message_count"],
        }
        for row in rows
    ]


def get_session_messages(session_id: str, user_id: str) -> List[dict]:
    """
    Get all messages in a session for display in the chat window.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at ASC
            """,
            (session_id, user_id)
        ).fetchall()

    return [
        {
            "id":         row["id"],
            "role":       row["role"],
            "content":    row["content"],
            "timestamp":  row["created_at"],
        }
        for row in rows
    ]


def delete_session(session_id: str, user_id: str) -> int:
    """Delete a session and all its messages. Returns number of messages deleted."""
    with get_db() as conn:
        # Delete messages first (no CASCADE in SQLite by default)
        result = conn.execute(
            "DELETE FROM messages WHERE session_id = ? AND user_id = ?",
            (session_id, user_id)
        )
        deleted = result.rowcount
        conn.execute(
            "DELETE FROM sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id)
        )
    return deleted
