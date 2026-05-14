"""
backend/config.py
=================
All application configuration loaded from environment variables / .env file.
Import `Config` anywhere in the app to access settings.
"""

import os


class Config:
    """Static configuration class — reads from environment at import time."""

    # ── Groq API ──────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv('GROQ_API_KEY', '')
    GROQ_MODEL: str = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')

    # ── Google OAuth ──────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET: str = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI: str = os.getenv(
        'GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/callback'
    )

    # ── Flask ─────────────────────────────────────────────────────────────────
    FLASK_SECRET_KEY: str = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-me')
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'development')
    APP_PORT: int = int(os.getenv('APP_PORT', '5000'))

    # ── SQLite Database ───────────────────────────────────────────────────────
    # Resolve relative path from this file's location → project root
    _raw_db_path: str = os.getenv('DATABASE_PATH', '../chatbot.db')
    DATABASE_PATH: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', _raw_db_path.lstrip('../'))
    )

    # ── Analytics ────────────────────────────────────────────────────────────
    ANALYTICS_OUTPUT_DIR: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'analytics_output')
    )

    @classmethod
    def validate(cls):
        """Warn about missing required keys at startup."""
        if not cls.GROQ_API_KEY:
            print("⚠️  WARNING: GROQ_API_KEY is not set. Chat will return error responses.")
        if not cls.GOOGLE_CLIENT_ID:
            print("⚠️  WARNING: GOOGLE_CLIENT_ID is not set. OAuth login won't work.")
