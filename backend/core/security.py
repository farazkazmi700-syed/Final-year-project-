"""
backend/core/security.py
========================
JWT token helpers and Google OAuth 2.0 flow.
FR2: Google OAuth login | FR3: User authentication.
"""

import jwt
import time
import requests
from typing import Optional
from flask import Request
from backend.config import Config


# ── Google OAuth URLs ─────────────────────────────────────────────────────────
GOOGLE_AUTH_URL    = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL   = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

GOOGLE_SCOPES = "openid email profile"


# ── JWT Helpers ───────────────────────────────────────────────────────────────

def create_token(user_id: str, email: str, name: str) -> str:
    """
    Create a signed JWT for an authenticated user.

    Payload includes:
      sub   - user ID (Google 'sub')
      email - user email
      name  - display name
      iat   - issued at (Unix timestamp)
      exp   - expiry (24 hours from now)

    Returns:
        Encoded JWT string.
    """
    payload = {
        "sub":   user_id,
        "email": email,
        "name":  name,
        "iat":   int(time.time()),
        "exp":   int(time.time()) + (60 * 60 * 24),  # 24 hours
    }
    return jwt.encode(payload, Config.FLASK_SECRET_KEY, algorithm="HS256")


def verify_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT string from the cookie.

    Returns:
        The decoded payload dict, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            Config.FLASK_SECRET_KEY,
            algorithms=["HS256"],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None    # Token expired
    except jwt.InvalidTokenError:
        return None    # Token tampered or malformed


def get_user_from_request(request: Request) -> Optional[dict]:
    """
    Extract the authenticated user from the request cookie.

    Returns:
        User payload dict (sub, email, name) or None if not authenticated.
    """
    token = request.cookies.get('auth_token')
    if not token:
        return None
    return verify_token(token)


# ── Google OAuth Helpers ──────────────────────────────────────────────────────

def get_google_auth_url() -> str:
    """
    Build the URL that the user is redirected to for Google sign-in.
    """
    params = "&".join([
        f"client_id={Config.GOOGLE_CLIENT_ID}",
        f"redirect_uri={Config.GOOGLE_REDIRECT_URI}",
        "response_type=code",
        f"scope={GOOGLE_SCOPES.replace(' ', '%20')}",
        "access_type=offline",
        "prompt=select_account",
    ])
    return f"{GOOGLE_AUTH_URL}?{params}"


def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange the OAuth authorization code for Google access tokens.

    Args:
        code: One-time code returned by Google to the callback URL.

    Returns:
        Token response dict (access_token, id_token, etc.)

    Raises:
        ValueError: If the exchange fails.
    """
    response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code":          code,
            "client_id":     Config.GOOGLE_CLIENT_ID,
            "client_secret": Config.GOOGLE_CLIENT_SECRET,
            "redirect_uri":  Config.GOOGLE_REDIRECT_URI,
            "grant_type":    "authorization_code",
        },
        timeout=10,
    )

    if response.status_code != 200:
        raise ValueError(f"Token exchange failed: {response.text}")

    return response.json()


def fetch_google_user_info(access_token: str) -> dict:
    """
    Fetch the authenticated user's profile from Google.

    Returns:
        Dict with: sub (google_id), email, name, picture.

    Raises:
        ValueError: If the request fails.
    """
    response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )

    if response.status_code != 200:
        raise ValueError(f"Failed to fetch user info: {response.text}")

    return response.json()
