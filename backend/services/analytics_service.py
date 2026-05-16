"""
backend/services/analytics_service.py
=====================================
Professional analytics aggregation and visual reporting.

Libraries used:
  - pandas: structured data processing and aggregation
  - matplotlib / seaborn: static server-rendered charts
  - plotly: interactive browser-rendered analytics
  - scikit-learn: lightweight topic classification support
"""

import base64
import io
import json
from datetime import datetime, timedelta, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.core.database import get_db

try:
    import plotly.graph_objects as go
    import plotly.utils
except ImportError:
    go = None
    plotly = None


CHART_BG = "#172033"
PAPER_BG = "#111827"
GRID = "#334155"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
ACCENT = "#2563eb"

TOPIC_PROFILES = {
    "Programming": "python javascript code function bug api database flask html css software development",
    "Study": "study learning exam assignment university notes summarize explain concept education",
    "Science": "science physics chemistry biology quantum research experiment technology",
    "Writing": "write email essay paragraph report improve grammar communication content",
    "Career": "career job resume interview productivity planning business professional workplace",
    "General": "conversation general question help advice information assistant",
}


def _utcnow():
    return datetime.now(timezone.utc)


def _apply_chart_theme(ax):
    ax.set_facecolor(CHART_BG)
    ax.figure.set_facecolor(PAPER_BG)
    ax.tick_params(colors=MUTED)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)
    ax.title.set_color(TEXT)
    ax.grid(True, color=GRID, alpha=0.35, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color(GRID)


def _fig_to_base64(fig) -> str:
    """Convert a matplotlib figure to an inline PNG data URL."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=130, facecolor=fig.get_facecolor())
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


def _read_messages(user_id: str) -> pd.DataFrame:
    with get_db() as conn:
        return pd.read_sql_query(
            """
            SELECT id, session_id, role, content, created_at
            FROM messages
            WHERE user_id = ?
            ORDER BY created_at ASC
            """,
            conn,
            params=(user_id,),
        )


def _read_feedback(user_id: str) -> pd.DataFrame:
    with get_db() as conn:
        return pd.read_sql_query(
            """
            SELECT rating, correctness, length_rating, comment, submitted_at
            FROM feedback
            WHERE user_id = ?
            ORDER BY submitted_at DESC
            """,
            conn,
            params=(user_id,),
        )


def _read_session_count(user_id: str) -> int:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user_id,)).fetchone()
    return int(row[0] if row else 0)


def _classify_topics(texts: list[str]) -> pd.Series:
    """Classify user messages into broad topics with TF-IDF cosine similarity."""
    clean_texts = [text.strip() for text in texts if text and text.strip()]
    if not clean_texts:
        return pd.Series(dtype="object")

    labels = list(TOPIC_PROFILES.keys())
    profile_texts = [TOPIC_PROFILES[label] for label in labels]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(profile_texts + clean_texts)
    profile_matrix = matrix[: len(labels)]
    message_matrix = matrix[len(labels) :]
    scores = cosine_similarity(message_matrix, profile_matrix)

    topics = []
    for row in scores:
        best_idx = int(row.argmax())
        topics.append(labels[best_idx] if row[best_idx] > 0 else "General")
    return pd.Series(topics)


def get_user_stats(user_id: str) -> dict:
    """Return analytics KPIs for dashboard cards and summaries."""
    messages = _read_messages(user_id)
    feedback = _read_feedback(user_id)
    session_count = _read_session_count(user_id)

    if messages.empty:
        user_messages = pd.DataFrame(columns=messages.columns)
        assistant_messages = pd.DataFrame(columns=messages.columns)
        recent_count = 0
    else:
        messages["created_at"] = pd.to_datetime(messages["created_at"], errors="coerce", utc=True)
        user_messages = messages[messages["role"] == "user"].copy()
        assistant_messages = messages[messages["role"] == "assistant"].copy()
        week_ago = _utcnow() - timedelta(days=7)
        recent_count = int(user_messages[user_messages["created_at"] >= week_ago].shape[0])

    if not feedback.empty:
        feedback["rating"] = pd.to_numeric(feedback["rating"], errors="coerce")

    topics = _classify_topics(user_messages["content"].dropna().astype(str).tolist())
    topic_breakdown = topics.value_counts().to_dict() if not topics.empty else {}
    top_topic = max(topic_breakdown, key=topic_breakdown.get) if topic_breakdown else "No topic data"

    correctness = feedback["correctness"].value_counts().to_dict() if not feedback.empty else {}
    length_rating = feedback["length_rating"].value_counts().to_dict() if not feedback.empty else {}
    avg_rating = float(round(feedback["rating"].mean(), 1)) if not feedback.empty else 0.0
    avg_messages = round(len(messages) / session_count, 1) if session_count else 0.0

    return {
        "total_messages": int(len(messages)),
        "user_messages": int(len(user_messages)),
        "assistant_messages": int(len(assistant_messages)),
        "total_sessions": int(session_count),
        "messages_last_7_days": recent_count,
        "avg_messages_per_session": avg_messages,
        "avg_rating": avg_rating,
        "total_feedback": int(len(feedback)),
        "correctness_breakdown": correctness,
        "length_breakdown": length_rating,
        "topic_breakdown": topic_breakdown,
        "top_topic": top_topic,
    }


def generate_daily_activity_chart(user_id: str) -> str:
    """Generate a seaborn bar chart for user message activity over 14 days."""
    messages = _read_messages(user_id)
    today = _utcnow().date()
    days = pd.date_range(end=today, periods=14, freq="D")
    frame = pd.DataFrame({"date": days})

    if messages.empty:
        frame["messages"] = 0
    else:
        messages["created_at"] = pd.to_datetime(messages["created_at"], errors="coerce", utc=True)
        daily = (
            messages[messages["role"] == "user"]
            .dropna(subset=["created_at"])
            .assign(date=lambda df: df["created_at"].dt.tz_convert(None).dt.floor("D"))
            .groupby("date")
            .size()
            .rename("messages")
            .reset_index()
        )
        frame = frame.merge(daily, on="date", how="left").fillna({"messages": 0})

    frame["label"] = frame["date"].dt.strftime("%b %d")
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.barplot(data=frame, x="label", y="messages", color=ACCENT, ax=ax)
    _apply_chart_theme(ax)
    ax.set_title("Daily Activity - Last 14 Days", fontsize=13, pad=12)
    ax.set_xlabel("Date")
    ax.set_ylabel("Messages")
    ax.bar_label(ax.containers[0], fmt="%.0f", padding=2, color=TEXT, fontsize=8)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return _fig_to_base64(fig)


def generate_correctness_pie_chart(user_id: str) -> str:
    """Generate a matplotlib pie chart for response correctness feedback."""
    feedback = _read_feedback(user_id)
    if feedback.empty or feedback["correctness"].dropna().empty:
        return _placeholder_chart("No correctness feedback yet")

    counts = feedback["correctness"].value_counts()
    labels = [label.replace("_", " ").title() for label in counts.index]
    colors = ["#22c55e", "#f59e0b", "#ef4444", "#60a5fa"]

    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    fig.set_facecolor(PAPER_BG)
    ax.set_facecolor(CHART_BG)
    ax.pie(
        counts.values,
        labels=labels,
        colors=colors[: len(counts)],
        autopct="%1.0f%%",
        startangle=135,
        textprops={"color": TEXT, "fontsize": 10},
    )
    ax.set_title("Response Correctness", color=TEXT, pad=10)
    plt.tight_layout()
    return _fig_to_base64(fig)


def generate_rating_distribution_chart(user_id: str) -> str:
    """Generate a seaborn horizontal bar chart for rating distribution."""
    feedback = _read_feedback(user_id)
    all_ratings = pd.DataFrame({"rating": [1, 2, 3, 4, 5]})
    if feedback.empty:
        all_ratings["count"] = 0
    else:
        counts = feedback["rating"].value_counts().rename_axis("rating").reset_index(name="count")
        all_ratings = all_ratings.merge(counts, on="rating", how="left").fillna({"count": 0})

    all_ratings["label"] = all_ratings["rating"].astype(str) + " stars"
    fig, ax = plt.subplots(figsize=(6, 3.6))
    sns.barplot(data=all_ratings, y="label", x="count", palette="Blues_r", hue="label", legend=False, ax=ax)
    _apply_chart_theme(ax)
    ax.set_title("Rating Distribution", fontsize=12, pad=10)
    ax.set_xlabel("Feedback Entries")
    ax.set_ylabel("")
    ax.bar_label(ax.containers[0], fmt="%.0f", padding=3, color=TEXT, fontsize=9)
    plt.tight_layout()
    return _fig_to_base64(fig)


def generate_topic_distribution_plot(user_id: str) -> dict:
    """Generate an interactive Plotly topic distribution chart."""
    messages = _read_messages(user_id)
    user_texts = messages[messages["role"] == "user"]["content"].dropna().astype(str).tolist()
    topics = _classify_topics(user_texts)
    counts = topics.value_counts().sort_values(ascending=True)

    if counts.empty:
        labels = ["No topic data"]
        values = [0]
    else:
        labels = counts.index.tolist()
        values = counts.values.tolist()

    data = [
        {
            "type": "bar",
            "x": values,
            "y": labels,
            "orientation": "h",
            "marker": {"color": "#60a5fa"},
            "hovertemplate": "<b>%{y}</b><br>Messages: %{x}<extra></extra>",
        }
    ]
    layout = {
        "title": "Topic Classification",
        "paper_bgcolor": PAPER_BG,
        "plot_bgcolor": CHART_BG,
        "font": {"color": TEXT, "family": "Inter, sans-serif"},
        "margin": {"l": 96, "r": 24, "t": 52, "b": 42},
        "xaxis": {"title": "Messages", "gridcolor": GRID, "zerolinecolor": GRID},
        "yaxis": {"title": ""},
        "height": 320,
    }

    if go and plotly:
        fig = go.Figure(data=data, layout=layout)
        return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

    return {"data": data, "layout": layout}


def _placeholder_chart(message: str) -> str:
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    fig.set_facecolor(PAPER_BG)
    ax.set_facecolor(CHART_BG)
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=13, color=MUTED, transform=ax.transAxes)
    ax.set_axis_off()
    return _fig_to_base64(fig)
