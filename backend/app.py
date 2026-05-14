"""
backend/app.py
==============
Flask application entry point.
FR1: System Initialization — loads all modules at startup.

Run locally:
    cd backend
    python app.py

Run on Colab:
    See scripts/colab_setup.py
"""

import os
import sys

# ── Make sure project root is on the path ─────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env before importing config-dependent modules
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from backend.config import Config
from backend.core.database import init_db
from backend.routers.auth import auth_bp
from backend.routers.chat import chat_bp
from backend.routers.feedback import feedback_bp
from backend.routers.analytics import analytics_bp


def create_app() -> Flask:
    """
    Application factory — creates and configures the Flask app.
    All modules are initialized here (FR1).
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static'),
    )

    # ── Flask config ──────────────────────────────────────────────────────────
    app.config['SECRET_KEY'] = Config.FLASK_SECRET_KEY
    app.config['ENV'] = Config.FLASK_ENV

    # ── CORS: allow frontend JS to call the API ───────────────────────────────
    CORS(app, supports_credentials=True)

    # ── FR1: Initialize SQLite database (creates tables if not exist) ─────────
    print("[INIT] Setting up SQLite database...")
    init_db()
    print("[INIT] ✅ Database ready")

    # ── FR1: Register all route blueprints (FR3, FR5) ─────────────────────────
    app.register_blueprint(auth_bp)        # /auth/*
    app.register_blueprint(chat_bp)        # /chat/*
    app.register_blueprint(feedback_bp)    # /feedback/*
    app.register_blueprint(analytics_bp)   # /analytics/*

    # ── Root redirect ─────────────────────────────────────────────────────────
    @app.route('/')
    def index():
        """Redirect root to login page."""
        return redirect(url_for('auth.login_page'))

    # ── Startup log ───────────────────────────────────────────────────────────
    print("[INIT] ✅ All modules initialized")
    print(f"[INIT] 🚀 Groq model: {Config.GROQ_MODEL}")
    print(f"[INIT] 📁 Database:   {Config.DATABASE_PATH}")

    return app


# ── Run directly ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app = create_app()
    print(f"\n🌐 Server running at: http://localhost:{Config.APP_PORT}")
    print("   Press CTRL+C to stop\n")
    app.run(
        host='0.0.0.0',
        port=Config.APP_PORT,
        debug=(Config.FLASK_ENV == 'development'),
    )
