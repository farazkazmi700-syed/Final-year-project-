# 🤖 Multi-Turn AI Chatbot with LLaMA 3
**CS619 – Spring 2026 | VU | Supervisor: Neelam Alam (neelam.alam@vu.edu.pk)**

A full-stack conversational AI chatbot using **LLaMA 3 via Groq API** (free),
**Flask backend**, **SQLite database**, and a clean **HTML/CSS/JS frontend**.
Designed to run locally **or** on Google Colab.

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   LOCAL BROWSER (Frontend)                  │
│          HTML + CSS + Vanilla JavaScript                    │
│   Login Page → Chat UI → Feedback Panel → Analytics View   │
└───────────────────────┬─────────────────────────────────────┘
                        │  HTTP (fetch / XMLHttpRequest)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              FLASK BACKEND  (app.py)                        │
│  /auth/login   /auth/callback   /auth/logout                │
│  /chat/send    /chat/history    /chat/sessions              │
│  /feedback/submit               /analytics/stats            │
└──────────┬────────────────┬────────────────────────────────-┘
           │                │
           ▼                ▼
┌──────────────────┐  ┌─────────────────────────────────────┐
│  SQLite DB       │  │  Groq Cloud API (free tier)         │
│  chatbot.db      │  │  Model: llama3-8b-8192              │
│  - users         │  │  https://console.groq.com           │
│  - sessions      │  │  (LLaMA 3 — no GPU needed locally)  │
│  - messages      │  └─────────────────────────────────────┘
│  - feedback      │
└──────────────────┘
```

---

## 📁 Project Structure

```
llama-chatbot/
│
├── backend/
│   ├── app.py                    ← Flask app entry point (run this)
│   ├── config.py                 ← All settings & env variables
│   ├── core/
│   │   ├── database.py           ← SQLite connection & schema init
│   │   ├── security.py           ← JWT tokens + Google OAuth helpers
│   │   └── groq_client.py        ← Groq API / LLaMA 3 inference
│   ├── models/
│   │   └── schemas.py            ← Dataclass schemas (User, Message, Feedback)
│   ├── routers/
│   │   ├── auth.py               ← /auth/* routes (Google OAuth)
│   │   ├── chat.py               ← /chat/* routes (send, history, sessions)
│   │   ├── feedback.py           ← /feedback/* routes
│   │   └── analytics.py          ← /analytics/* routes + graph generation
│   └── services/
│       ├── chat_service.py       ← Multi-turn chat logic
│       ├── auth_service.py       ← User upsert & session helpers
│       └── analytics_service.py  ← Stats aggregation + matplotlib graphs
│
├── frontend/
│   ├── templates/
│   │   ├── login.html            ← Google Sign-In page
│   │   └── chat.html             ← Main chat + feedback + analytics
│   └── static/
│       ├── css/
│       │   └── style.css         ← Full responsive stylesheet
│       └── js/
│           └── app.js            ← All frontend logic (fetch, render, feedback)
│
├── scripts/
│   ├── colab_setup.py            ← Run this on Google Colab to start server
│   └── init_db.py                ← Manually initialize/reset the database
│
├── analytics_output/             ← Auto-generated graph images saved here
├── chatbot.db                    ← SQLite database (auto-created on first run)
├── .env.example                  ← Environment variable template
├── requirements.txt              ← pip dependencies
└── README.md                     ← This file
```

---

## ⚙️ Prerequisites

| Tool | Notes |
|------|-------|
| Python 3.9+ | Backend language |
| Groq API Key | Free at https://console.groq.com — no credit card |
| Google OAuth Credentials | Free at https://console.cloud.google.com |

---

## 🚀 Setup — Run Locally (VS Code / Terminal)

### Step 1 — Extract Project
```bash
unzip llama-chatbot.zip
cd llama-chatbot
```

### Step 2 — Create Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Get Your Free Groq API Key
1. Go to **https://console.groq.com**
2. Sign up (free, no credit card)
3. Click **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

### Step 5 — Configure Google OAuth
1. Go to **https://console.cloud.google.com**
2. Create project → **APIs & Services** → **Credentials**
3. Create **OAuth 2.0 Client ID** → Web Application
4. Add Authorized Redirect URI: http://localhost:5000/auth/callback
5. Copy **Client ID** and **Client Secret**

### Step 6 — Set Environment Variables
```bash
cp .env.example .env
# Open .env in any text editor and fill in your values
```

### Step 7 — Run the App
```bash
cd backend
python app.py
```

### Step 8 — Open Browser
```
http://localhost:5000
```

---

## ☁️ Run on Google Colab

```python
# In a Colab cell, run:
!pip install -r /content/llama-chatbot/requirements.txt
%cd /content/llama-chatbot
exec(open('scripts/colab_setup.py').read())
```
The script installs `pyngrok`, starts Flask, and prints a public URL.

---

## 🔑 API Reference

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/` | No | Redirect to login |
| GET | `/auth/login` | No | Google OAuth login page |
| GET | `/auth/google` | No | Start OAuth flow |
| GET | `/auth/callback` | No | OAuth callback |
| GET | `/auth/logout` | Yes | Clear session |
| POST | `/chat/send` | Yes | Send message, get AI reply |
| GET | `/chat/sessions` | Yes | List all sessions |
| GET | `/chat/history/<session_id>` | Yes | Get messages in a session |
| DELETE | `/chat/session/<session_id>` | Yes | Delete a session |
| POST | `/feedback/submit` | Yes | Submit rating + feedback |
| GET | `/analytics/stats` | Yes | Get usage statistics |
| GET | `/analytics/graphs` | Yes | Get chart image URLs |

---

## 🧠 LLaMA 3 via Groq

- **Model**: `llama3-8b-8192` (fast, free tier)
- **Alternative models**: `llama3-70b-8192`, `mixtral-8x7b-32768`
- **Context window**: 8192 tokens (full multi-turn history fits)
- **Rate limits**: 30 req/min, 500 req/day on free tier

---

## 📊 Analytics Features
- Total messages sent / received
- Active sessions count
- Average feedback rating
- Daily activity chart (bar graph — saved as PNG)
- Correctness breakdown chart (pie chart)
- Response length distribution

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `GROQ_API_KEY not set` | Add key to `.env` file |
| `Google OAuth error` | Check redirect URI matches exactly |
| `Port 5000 in use` | Change `APP_PORT=5001` in `.env` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Colab tunnel expired | Re-run `colab_setup.py` |
