"""
backend/routers/chat.py
=======================
Chat API routes.
FR3: Message routing to model | FR5: Service connectivity.

Routes:
  GET  /chat                         → Chat page (HTML)
  POST /chat/send                    → Send message, get AI response
  GET  /chat/sessions                → List user's sessions
  GET  /chat/history/<session_id>    → Get messages in a session
  DELETE /chat/session/<session_id>  → Delete a session
"""

from flask import Blueprint, render_template, request, jsonify, redirect
from backend.core.security import get_user_from_request
from backend.services import chat_service

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


def _require_auth():
    """
    Helper: verify authentication.
    Returns (user_payload, None) on success, (None, redirect_response) on failure.
    """
    user = get_user_from_request(request)
    if not user:
        return None, redirect('/auth/login')
    return user, None


@chat_bp.route('')
@chat_bp.route('/')
def chat_page():
    """
    Serve the main chat interface.
    Requires authentication — unauthenticated users are sent to login.
    """
    user, err = _require_auth()
    if err:
        return err
    return render_template('chat.html', user=user)


@chat_bp.route('/send', methods=['POST'])
def send_message():
    """
    Process a user message and return the AI response.
    FR3: Route message → FR4: LLaMA 3 inference → save → return.

    Request JSON:
        {
            "content":    "Hello, who are you?",
            "session_id": "optional-uuid-string"   // omit for new session
        }

    Response JSON:
        {
            "session_id": "uuid",
            "message_id": "uuid",
            "response":   "I'm LLaMA 3 ...",
            "timestamp":  "2024-01-01T12:00:00"
        }
    """
    user, err = _require_auth()
    if err:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    # Validate input
    from backend.models.schemas import validate_send_message
    try:
        content, session_id = validate_send_message(data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # Run the full chat pipeline
    try:
        result = chat_service.process_message(
            user_id=user['sub'],
            content=content,
            session_id=session_id,
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@chat_bp.route('/sessions')
def list_sessions():
    """
    Return all sessions for the current user.
    Used to populate the sidebar session list.

    Response JSON:
        { "sessions": [ { "session_id", "title", "created_at", "message_count" }, ... ] }
    """
    user, err = _require_auth()
    if err:
        return jsonify({'error': 'Unauthorized'}), 401

    sessions = chat_service.get_user_sessions(user['sub'])
    return jsonify({'sessions': sessions})


@chat_bp.route('/history/<session_id>')
def get_history(session_id):
    """
    Return all messages in a specific session.

    Response JSON:
        {
            "session_id": "uuid",
            "messages": [ { "id", "role", "content", "timestamp" }, ... ]
        }
    """
    user, err = _require_auth()
    if err:
        return jsonify({'error': 'Unauthorized'}), 401

    messages = chat_service.get_session_messages(session_id, user['sub'])
    if not messages:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify({'session_id': session_id, 'messages': messages})


@chat_bp.route('/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """
    Delete a session and all its messages.

    Response JSON:
        { "message": "Deleted X messages" }
    """
    user, err = _require_auth()
    if err:
        return jsonify({'error': 'Unauthorized'}), 401

    deleted = chat_service.delete_session(session_id, user['sub'])
    return jsonify({'message': f'Deleted {deleted} messages'})
