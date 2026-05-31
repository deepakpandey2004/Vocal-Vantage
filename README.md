<div align="center">

# 🎙️ Vocal Vantage

### AI-Powered Public Speaking Coach

*Transforming speeches into actionable intelligence through AI power.*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-async-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-cache-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Tests](https://img.shields.io/badge/tests-passing-success)](#-testing)

</div>

---

## 📖 Overview

**Vocal Vantage** is an AI-powered public speaking coach. Upload an audio recording of
your talk and the app runs a complete, automated pipeline:

> **audio ingestion → Whisper transcription → Python linguistic analysis → LLM feedback → structured JSON report card**

It detects filler words (`umm`, `uh`, `like`, `you know`, …), measures your speaking
pace (WPM) and vocabulary diversity, computes a **0–100 fluency score**, and uses
**Google Gemini** to generate personalised coaching insights — all delivered as a clean,
shareable report card.

This is a **backend-focused** project demonstrating authentication, async PostgreSQL,
Redis caching & rate-limiting, an AI processing pipeline, containerisation, and
cloud deployment.

---

Live URL    -----     https://vocal-vantage.onrender.com




## ✨ Features

| Area | What it does |
|------|--------------|
| 🔐 **Authentication** | JWT-based register / login, hashed passwords (bcrypt), **plus "Continue as Guest"** for instant, frictionless trials |
| 🗣️ **Transcription** | OpenAI **Whisper** API converts speech → text |
| 📊 **Linguistic analysis** | 3 metrics computed in pure Python: **Words-Per-Minute**, **filler-word rate** (with per-word breakdown), **vocabulary diversity** (type-token ratio) |
| 🎯 **Fluency scoring** | Weighted 0–100 score combining pace, fillers and diversity |
| 🤖 **AI coaching** | **Gemini** turns metrics into strengths, improvements & actionable tips as structured JSON |
| ⚡ **Redis** | Rate limiting + report/transcript caching (degrades gracefully if unavailable) |
| 🗄️ **PostgreSQL** | Async SQLAlchemy 2.0 ORM; SQLite fallback for zero-config local dev |
| 📑 **Auto API docs** | Interactive Swagger UI at `/docs` |
| 🐳 **Deploy-ready** | Dockerfile, `render.yaml` blueprint, `Procfile`, health checks |
| 🧪 **Tested** | Unit + integration tests with a **mock AI mode** (no API keys/cost needed) |

---

## 🏗️ Architecture

```
                         ┌──────────────────────────────────────────┐
   Browser  ──────────▶  │  FastAPI (Jinja2 UI + JSON REST API)      │
  (HTML/JS UI)           │                                          │
                         │  ┌─ Auth router  (JWT, guest, bcrypt)    │
                         │  ┌─ Analysis router (upload, history)    │
                         │  └─ Pipeline orchestrator               │
                         └───────┬───────────────┬──────────────────┘
                                 │               │
              ┌──────────────────┘               └───────────────────┐
              ▼                                                       ▼
   ┌───────────────────────┐                              ┌────────────────────┐
   │  AI PIPELINE          │                              │  PostgreSQL (async)│
   │  1. Whisper (OpenAI)  │                              │  users / analyses  │
   │  2. Python analyzer   │                              └────────────────────┘
   │  3. Gemini feedback   │                              ┌────────────────────┐
   │  4. JSON report card  │  ◀── cache ──────────────▶  │  Redis (cache + RL)│
   └───────────────────────┘                              └────────────────────┘
```

### Project structure

```
vocal-vantage/
├── app/
│   ├── main.py                 # FastAPI app, middleware, lifespan, routers
│   ├── config.py               # Pydantic settings (env-driven)
│   ├── database.py             # Async SQLAlchemy engine + session
│   ├── models.py               # ORM models: User, Analysis
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── core/
│   │   ├── security.py         # Password hashing + JWT
│   │   ├── dependencies.py     # Auth dependencies (user / guest / optional)
│   │   ├── redis_client.py     # Redis connection (graceful fallback)
│   │   └── rate_limit.py       # Redis-backed rate limiter
│   ├── services/
│   │   ├── transcription.py    # Whisper transcription (+ mock mode)
│   │   ├── analyzer.py         # Linguistic metrics + fluency scoring
│   │   ├── feedback.py         # Gemini LLM feedback (+ rule-based fallback)
│   │   └── pipeline.py         # End-to-end orchestrator + caching
│   ├── routers/
│   │   ├── auth.py             # /api/auth/*
│   │   ├── analysis.py         # /api/analyses/*
│   │   └── pages.py            # Server-rendered HTML pages
│   ├── templates/              # Jinja2 templates (landing, auth, dashboard, report)
│   └── static/                 # CSS / JS / images
├── tests/                      # pytest unit + integration tests
├── requirements.txt
├── Dockerfile / .dockerignore
├── render.yaml / Procfile      # Deployment configs
├── .env.example / .gitignore
└── README.md
```

---

## 🚀 Quick start (local)

### Prerequisites
- Python 3.12+
- (Optional) PostgreSQL & Redis — the app falls back to SQLite and runs without Redis.

### 1. Clone & set up

```bash
git clone https://github.com/<your-username>/vocal-vantage.git
cd vocal-vantage

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

For an **instant zero-cost demo**, leave the defaults — `AI_MOCK_MODE=true` runs the
whole pipeline with deterministic mock data (no API keys needed). To use real AI:

```env
AI_MOCK_MODE=false
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000** — landing page, sign-up / guest login, dashboard & reports.
Interactive API docs: **http://localhost:8000/docs**

---

## 🔌 API reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register` | — | Create account, returns JWT |
| `POST` | `/api/auth/login` | — | Login, returns JWT |
| `POST` | `/api/auth/guest` | — | Issue a guest token (no account) |
| `POST` | `/api/auth/logout` | — | Clear auth cookie |
| `GET`  | `/api/auth/me` | ✅ user | Current user profile |
| `POST` | `/api/analyses` | ✅ user/guest | Upload audio → run pipeline → report |
| `GET`  | `/api/analyses` | ✅ user/guest | List your analyses |
| `GET`  | `/api/analyses/{id}` | ✅ user/guest | Get one report card |
| `DELETE` | `/api/analyses/{id}` | ✅ user/guest | Delete an analysis |
| `GET`  | `/health` | — | Health check (used by Render) |

### Example report card (JSON)

```json
{
  "scores": { "fluency_score": 85, "max_score": 100 },
  "metrics": {
    "words_per_minute": 142.0,
    "filler_count": 7,
    "filler_rate_per_min": 2.1,
    "vocabulary_diversity": 0.58
  },
  "filler_breakdown": [{ "word": "um", "count": 3 }, { "word": "like", "count": 2 }],
  "ai_insights": {
    "summary": "Confident, well-paced delivery with minor filler usage.",
    "strengths": ["Ideal speaking pace", "Rich vocabulary"],
    "improvements": ["Reduce 'um' at sentence starts"],
    "actionable_tips": ["Replace fillers with a brief pause"],
    "confidence_estimate": "high"
  }
}
```

---

## 🧪 Testing

```bash
pip install -r requirements-dev.txt
pytest -q
```

Tests run in **mock AI mode** against SQLite with Redis disabled, so they need no
external services, API keys, or network access.

---

## ☁️ Deployment (Render)

This repo ships a **`render.yaml` Blueprint** that provisions the web service,
PostgreSQL, and Redis together.

1. Push the repo to GitHub.
2. In Render: **New → Blueprint** and select your repo.
3. Render auto-creates the Postgres DB + Redis and wires `DATABASE_URL` / `REDIS_URL`.
4. Add your secrets in the dashboard: `OPENAI_API_KEY`, `GEMINI_API_KEY`
   (or set `AI_MOCK_MODE=true` to skip them).
5. Deploy 🎉 — health checks hit `/health`.

> Also works on any Docker host: `docker build -t vocal-vantage . && docker run -p 8000:8000 --env-file .env vocal-vantage`

---

## 🛠️ Tech stack

**Backend:** FastAPI · Uvicorn/Gunicorn · Pydantic v2
**Database:** PostgreSQL · SQLAlchemy 2.0 (async) · asyncpg
**Cache:** Redis (caching + rate limiting)
**Auth:** JWT (PyJWT) · Passlib/bcrypt
**AI:** OpenAI Whisper · Google Gemini
**Frontend:** Jinja2 · vanilla JS · custom CSS design system
**DevOps:** Docker · Render · pytest

---

## 📝 License

MIT — free to use, learn from, and build upon.
