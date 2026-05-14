"""
backend/models/schemas.py
=========================
Data schemas for request validation and response formatting.
Uses Python dataclasses for lightweight, dependency-free models.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


# ── User ──────────────────────────────────────────────────────────────────────

@dataclass
class User:
    """Represents an authenticated user."""
    id:         str           # Google 'sub' (unique user ID)
    email:      str
    name:       str
    picture:    Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None


# ── Chat ──────────────────────────────────────────────────────────────────────

@dataclass
class SendMessageRequest:
    """
    Request body for POST /chat/send.
    Validated manually in the route handler.
    """
    content:    str                    # The user's message (required)
    session_id: Optional[str] = None  # Existing session, or None for new chat


@dataclass
class Message:
    """A single chat message stored in the database."""
    id:         str
    session_id: str
    user_id:    str
    role:       str    # "user" or "assistant"
    content:    str
    created_at: Optional[str] = None


@dataclass
class Session:
    """A chat session containing multiple messages."""
    id:            str
    user_id:       str
    title:         str
    created_at:    Optional[str] = None
    updated_at:    Optional[str] = None
    message_count: int = 0


# ── Feedback ──────────────────────────────────────────────────────────────────

@dataclass
class FeedbackRequest:
    """
    Request body for POST /feedback/submit.
    FR2: Feedback panel (rating, correctness, length type).
    """
    message_id:   str   # ID of the AI message being rated
    session_id:   str
    rating:       int   # 1–5 stars
    correctness:  str   # "correct" | "partially_correct" | "incorrect"
    length_rating: str  # "too_short" | "just_right" | "too_long"
    comment:      Optional[str] = None


# ── Validation Helpers ────────────────────────────────────────────────────────

def validate_send_message(data: dict) -> tuple:
    """
    Validate POST /chat/send request data.

    Returns:
        (content, session_id) on success.

    Raises:
        ValueError: with descriptive message on invalid data.
    """
    content = data.get('content', '').strip()
    if not content:
        raise ValueError("Message content cannot be empty.")
    if len(content) > 4000:
        raise ValueError("Message too long. Maximum 4000 characters.")

    session_id = data.get('session_id')  # Optional
    return content, session_id


def validate_feedback(data: dict) -> FeedbackRequest:
    """
    Validate POST /feedback/submit request data.

    Raises:
        ValueError: with descriptive message on invalid data.
    """
    required = ['message_id', 'session_id', 'rating', 'correctness', 'length_rating']
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: '{field}'")

    rating = data['rating']
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise ValueError("Rating must be an integer between 1 and 5.")

    valid_correctness = {'correct', 'partially_correct', 'incorrect'}
    if data['correctness'] not in valid_correctness:
        raise ValueError(f"correctness must be one of: {valid_correctness}")

    valid_length = {'too_short', 'just_right', 'too_long'}
    if data['length_rating'] not in valid_length:
        raise ValueError(f"length_rating must be one of: {valid_length}")

    return FeedbackRequest(
        message_id=data['message_id'],
        session_id=data['session_id'],
        rating=rating,
        correctness=data['correctness'],
        length_rating=data['length_rating'],
        comment=data.get('comment'),
    )
