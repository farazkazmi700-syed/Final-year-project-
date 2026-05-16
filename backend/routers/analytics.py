"""
backend/routers/analytics.py
=============================
Analytics routes — usage stats and chart generation.
FR1: Analytics module initialization.

Routes:
  GET /analytics/stats   → Aggregated usage statistics (JSON)
  GET /analytics/graphs  → Base64 chart images (JSON)
  GET /analytics/health  → Groq API health check (JSON)
"""

from flask import Blueprint, request, jsonify, render_template
from backend.core.security import get_user_from_request
from backend.core.groq_client import check_groq_connection
from backend.services.analytics_service import (
    get_user_stats,
    generate_daily_activity_chart,
    generate_correctness_pie_chart,
    generate_rating_distribution_chart,
    generate_topic_distribution_plot,
)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('/stats')
def get_stats():
    """
    Return aggregated analytics stats for the current user.

    Response JSON:
        {
            "total_messages":        42,
            "user_messages":         21,
            "assistant_messages":    21,
            "total_sessions":         5,
            "messages_last_7_days":  10,
            "avg_rating":           4.2,
            "total_feedback":         8,
            "correctness_breakdown": { "correct": 5, "partially_correct": 2, "incorrect": 1 },
            "length_breakdown":      { "just_right": 6, "too_long": 2 }
        }
    """
    user = get_user_from_request(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    stats = get_user_stats(user['sub'])
    return jsonify(stats)


@analytics_bp.route('/graphs')
def get_graphs():
    """
    Generate and return all analytics charts as base64 PNG strings.
    These are rendered inline in the analytics tab of the frontend.

    Response JSON:
        {
            "daily_activity":   "data:image/png;base64,...",
            "correctness_pie":  "data:image/png;base64,...",
            "rating_dist":      "data:image/png;base64,..."
        }
    """
    user = get_user_from_request(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        graphs = {
            'daily_activity': generate_daily_activity_chart(user['sub']),
            'correctness_pie': generate_correctness_pie_chart(user['sub']),
            'rating_dist': generate_rating_distribution_chart(user['sub']),
            'topic_plot': generate_topic_distribution_plot(user['sub']),
        }
        return jsonify(graphs)
    except Exception as e:
        return jsonify({'error': f'Chart generation error: {str(e)}'}), 500


@analytics_bp.route('/health')
def health_check():
    """
    Check the Groq API connection status.
    Used by the frontend to display a connection indicator.

    Response JSON:
        { "status": "ok", "model": "llama3-8b-8192" }
        or
        { "status": "error", "message": "..." }
    """
    result = check_groq_connection()
    status_code = 200 if result['status'] == 'ok' else 503
    return jsonify(result), status_code


@analytics_bp.route('')
def analytics_page():
    """Serve the dedicated frontend analytics dashboard."""
    return render_template('analytics.html')
