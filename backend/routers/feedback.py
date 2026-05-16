"""
backend/routers/feedback.py
============================
Feedback submission routes.
FR2: Feedback panel — rating, correctness, length type.

Routes:
  POST /feedback/submit   → Save feedback for an AI message
  GET  /feedback/list     → Get all feedback for the current user
"""

import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from backend.core.security import get_user_from_request
from backend.core.database import get_db
from backend.models.schemas import validate_feedback

feedback_bp = Blueprint('feedback', __name__, url_prefix='/feedback')


@feedback_bp.route('/submit', methods=['POST'])
def submit_feedback():
    """
    Save user feedback for a specific AI response.
    FR2: Feedback panel — rating (1–5), correctness, length type.

    Request JSON:
        {
            "message_id":   "uuid of the assistant message",
            "session_id":   "uuid",
            "rating":        4,
            "correctness":  "correct",          // correct|partially_correct|incorrect
            "length_rating":"just_right",        // too_short|just_right|too_long
            "comment":      "Optional text"      // optional
        }

    Response JSON:
        { "message": "Feedback saved", "feedback_id": "uuid" }
    """
    user = get_user_from_request(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    # Validate all feedback fields
    try:
        fb = validate_feedback(data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # Save to SQLite
    feedback_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO feedback
                    (id, message_id, session_id, user_id, rating,
                     correctness, length_rating, comment, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback_id, fb.message_id, fb.session_id,
                    user['sub'], fb.rating, fb.correctness,
                    fb.length_rating, fb.comment, now,
                )
            )
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    return jsonify({'message': 'Feedback saved', 'feedback_id': feedback_id}), 201


@feedback_bp.route('/list')
def list_feedback():
    """
    Return all feedback submitted by the current user.
    Useful for review and analytics display.
    """
    user = get_user_from_request(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, message_id, session_id, rating,
                   correctness, length_rating, comment, submitted_at
            FROM feedback
            WHERE user_id = ?
            ORDER BY submitted_at DESC
            """,
            (user['sub'],)
        ).fetchall()

    return jsonify({'feedback': [dict(row) for row in rows]})


@feedback_bp.route('')
def feedback_page():
    """Serve the dedicated frontend feedback page."""
    return render_template('feedback.html')
