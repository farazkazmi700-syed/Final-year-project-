"""
backend/routers/auth.py
=======================
Google OAuth 2.0 authentication routes.
FR2: Google OAuth login page | FR3: User authentication.

Routes:
  GET /auth/login      → Login page (HTML)
  GET /auth/google     → Redirect to Google consent screen
  GET /auth/callback   → Handle Google's response
  GET /auth/logout     → Clear session cookie
  GET /auth/me         → Return current user profile (JSON)
"""

from flask import Blueprint, render_template, redirect, request, make_response, jsonify, url_for
from backend.core.security import (
    get_google_auth_url,
    exchange_code_for_tokens,
    fetch_google_user_info,
    create_token,
    get_user_from_request,
)
from backend.services.auth_service import upsert_user

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login')
def login_page():
    """
    Serve the login page.
    If already authenticated, redirect to chat.
    """
    user = get_user_from_request(request)
    if user:
        return redirect('/chat')
    return render_template('login.html')


@auth_bp.route('/google')
def google_login():
    """
    Kick off the Google OAuth flow.
    Redirects user to Google's consent screen.
    """
    auth_url = get_google_auth_url()
    return redirect(auth_url)


@auth_bp.route('/callback')
def google_callback():
    """
    Handle the OAuth callback from Google.

    Steps:
      1. Receive one-time 'code' from Google
      2. Exchange code for access token
      3. Fetch user profile from Google
      4. Create/update user in SQLite
      5. Issue JWT cookie
      6. Redirect to /chat
    """
    code = request.args.get('code')
    error = request.args.get('error')

    # User denied permission or other error
    if error or not code:
        return redirect(url_for('auth.login_page') + '?error=access_denied')

    try:
        # Step 1: Exchange authorization code for tokens
        token_data = exchange_code_for_tokens(code)

        # Step 2: Fetch user profile from Google
        user_info = fetch_google_user_info(token_data['access_token'])

    except ValueError as e:
        return redirect(url_for('auth.login_page') + f'?error=oauth_failed')

    # Step 3: Create or update user in database
    google_id = user_info['sub']
    email     = user_info.get('email', '')
    name      = user_info.get('name', 'User')
    picture   = user_info.get('picture', '')

    upsert_user(google_id, email, name, picture)

    # Step 4: Issue JWT in an HttpOnly cookie (secure, JS can't read it)
    token = create_token(google_id, email, name)

    response = make_response(redirect('/chat'))
    response.set_cookie(
        'auth_token',
        value=token,
        httponly=True,    # Prevent XSS attacks from reading token
        samesite='Lax',
        max_age=86400,    # 24 hours
        secure=False,     # Set True in production with HTTPS
    )
    return response


@auth_bp.route('/logout')
def logout():
    """Clear the auth cookie and redirect to login."""
    response = make_response(redirect(url_for('auth.login_page')))
    response.delete_cookie('auth_token')
    return response


@auth_bp.route('/me')
def get_current_user():
    """
    Return the currently authenticated user's profile as JSON.
    Used by the frontend to display the user's name/avatar.
    """
    user = get_user_from_request(request)
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    from backend.services.auth_service import get_user_by_id
    profile = get_user_by_id(user['sub'])
    if not profile:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(profile)
