"""
backend/services/analytics_service.py
======================================
Analytics aggregation and graph generation.
FR1: Analytics module initialization.
Uses pandas for data processing, matplotlib/seaborn for charts.
"""

import os
import io
import base64
from datetime import datetime, timedelta, timezone

def _utcnow():
    """Return current UTC time (timezone-aware, avoids deprecation warning)."""
    return datetime.now(timezone.utc)

import pandas as pd
import matplotlib
matplotlib.use('Agg')          # Non-interactive backend (no display needed)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

from backend.core.database import get_db
from backend.config import Config

# Style all charts consistently
sns.set_theme(style="darkgrid", palette="muted")
plt.rcParams.update({'figure.facecolor': '#1e1e2e', 'axes.facecolor': '#2a2a3e',
                     'text.color': 'white', 'axes.labelcolor': 'white',
                     'xtick.color': 'white', 'ytick.color': 'white'})

# Ensure output directory exists
os.makedirs(Config.ANALYTICS_OUTPUT_DIR, exist_ok=True)


def _fig_to_base64(fig) -> str:
    """Convert a matplotlib figure to a base64 PNG string for inline HTML display."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=120,
                facecolor=fig.get_facecolor())
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{b64}"


def get_user_stats(user_id: str) -> dict:
    """
    Aggregate key statistics for a user.
    FR1: Analytics module.

    Returns dict with:
      - total_messages, user_messages, assistant_messages
      - total_sessions
      - messages_last_7_days
      - avg_rating, total_feedback
      - correctness_breakdown, length_breakdown
    """
    with get_db() as conn:
        # ── Message counts ─────────────────────────────────────────────────
        total = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

        user_msgs = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE user_id = ? AND role = 'user'", (user_id,)
        ).fetchone()[0]

        assistant_msgs = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE user_id = ? AND role = 'assistant'", (user_id,)
        ).fetchone()[0]

        # ── Session count ──────────────────────────────────────────────────
        sessions = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

        # ── Last 7 days ────────────────────────────────────────────────────
        week_ago = (_utcnow() - timedelta(days=7)).isoformat()
        recent = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE user_id = ? AND role = 'user' AND created_at >= ?",
            (user_id, week_ago)
        ).fetchone()[0]

        # ── Feedback stats ─────────────────────────────────────────────────
        fb_rows = conn.execute(
            "SELECT rating, correctness, length_rating FROM feedback WHERE user_id = ?",
            (user_id,)
        ).fetchall()

    ratings       = [r["rating"] for r in fb_rows]
    correctness   = {}
    length_rating = {}

    for row in fb_rows:
        c = row["correctness"]
        l = row["length_rating"]
        correctness[c]   = correctness.get(c, 0) + 1
        length_rating[l] = length_rating.get(l, 0) + 1

    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

    return {
        "total_messages":       total,
        "user_messages":        user_msgs,
        "assistant_messages":   assistant_msgs,
        "total_sessions":       sessions,
        "messages_last_7_days": recent,
        "avg_rating":           avg_rating,
        "total_feedback":       len(ratings),
        "correctness_breakdown": correctness,
        "length_breakdown":      length_rating,
    }


def generate_daily_activity_chart(user_id: str) -> str:
    """
    Bar chart: messages sent per day over the last 14 days.
    Returns base64 PNG string.
    """
    # Build a list of the last 14 days
    days = [(_utcnow() - timedelta(days=i)).date() for i in range(13, -1, -1)]

    counts = []
    with get_db() as conn:
        for day in days:
            day_start = datetime.combine(day, datetime.min.time()).isoformat()
            day_end   = datetime.combine(day, datetime.max.time()).isoformat()
            count = conn.execute(
                """SELECT COUNT(*) FROM messages
                   WHERE user_id = ? AND role = 'user'
                   AND created_at BETWEEN ? AND ?""",
                (user_id, day_start, day_end)
            ).fetchone()[0]
            counts.append(count)

    # Create DataFrame for pandas processing
    df = pd.DataFrame({"date": days, "messages": counts})
    df["date_str"] = df["date"].apply(lambda d: d.strftime("%b %d"))

    fig, ax = plt.subplots(figsize=(10, 4), facecolor='#1e1e2e')
    ax.set_facecolor('#2a2a3e')
    bars = ax.bar(df["date_str"], df["messages"], color='#7c6af7', alpha=0.85,
                  edgecolor='#a898ff', linewidth=0.5)

    # Annotate bars with counts
    for bar, val in zip(bars, df["messages"]):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    str(val), ha='center', va='bottom', fontsize=8, color='white')

    ax.set_title("Messages Sent — Last 14 Days", fontsize=13, pad=12, color='white')
    ax.set_xlabel("Date", fontsize=10)
    ax.set_ylabel("Messages", fontsize=10)
    plt.xticks(rotation=45, ha='right', fontsize=8)
    plt.tight_layout()

    return _fig_to_base64(fig)


def generate_correctness_pie_chart(user_id: str) -> str:
    """
    Pie chart: breakdown of feedback correctness ratings.
    Returns base64 PNG string.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT correctness, COUNT(*) AS cnt FROM feedback WHERE user_id = ? GROUP BY correctness",
            (user_id,)
        ).fetchall()

    if not rows:
        # No feedback yet — return placeholder chart
        fig, ax = plt.subplots(figsize=(5, 4), facecolor='#1e1e2e')
        ax.text(0.5, 0.5, 'No feedback yet', ha='center', va='center',
                fontsize=14, color='#888', transform=ax.transAxes)
        ax.set_axis_off()
        return _fig_to_base64(fig)

    labels = [row["correctness"].replace("_", " ").title() for row in rows]
    sizes  = [row["cnt"] for row in rows]
    colors = ['#4ade80', '#facc15', '#f87171'][:len(labels)]

    fig, ax = plt.subplots(figsize=(5, 4), facecolor='#1e1e2e')
    ax.set_facecolor('#1e1e2e')
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors,
        autopct='%1.0f%%', startangle=140,
        textprops={'color': 'white', 'fontsize': 10}
    )
    for autotext in autotexts:
        autotext.set_color('white')

    ax.set_title("Feedback Correctness", fontsize=12, color='white', pad=10)
    plt.tight_layout()

    return _fig_to_base64(fig)


def generate_rating_distribution_chart(user_id: str) -> str:
    """
    Horizontal bar chart: distribution of star ratings (1–5).
    Returns base64 PNG string.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT rating, COUNT(*) AS cnt FROM feedback WHERE user_id = ? GROUP BY rating ORDER BY rating",
            (user_id,)
        ).fetchall()

    all_ratings = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for row in rows:
        all_ratings[row["rating"]] = row["cnt"]

    df = pd.DataFrame({"stars": list(all_ratings.keys()),
                        "count": list(all_ratings.values())})

    fig, ax = plt.subplots(figsize=(6, 3.5), facecolor='#1e1e2e')
    ax.set_facecolor('#2a2a3e')
    colors = ['#f87171', '#fb923c', '#facc15', '#4ade80', '#4ade80']
    bars = ax.barh(df["stars"].astype(str) + " stars", df["count"],
                   color=colors, alpha=0.85)

    for bar, val in zip(bars, df["count"]):
        ax.text(val + 0.1, bar.get_y() + bar.get_height() / 2,
                str(val), va='center', fontsize=9, color='white')

    ax.set_title("Rating Distribution", fontsize=12, color='white', pad=10)
    ax.set_xlabel("Number of Ratings", fontsize=9)
    plt.tight_layout()

    return _fig_to_base64(fig)
