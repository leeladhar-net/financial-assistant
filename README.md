# Personalized Financial Intelligence Assistant — Backend Foundation (Part 1)

Production-ready backend foundation for a personalized **Financial Intelligence Assistant** for financial professionals, using Telegram as the natural text conversational frontend.

---

## 1. Product Overview

The Financial Intelligence Assistant helps financial professionals (equity research analysts, portfolio managers, investment bankers, traders, venture capitalists) monitor markets, companies, financial news, documents, spreadsheets, and important events.

Telegram serves purely as the conversational user interface — all intelligence, personalization, memory, and routing reside cleanly in the backend.

### Key UX Directives
- **Natural Language Interaction Only**: Standard natural text chat. No buttons, slash commands, inline keyboards, or complex menus.
- **Flexible Conversational Onboarding**: Natural profile extraction that accepts multi-field user responses and skips redundant prompts automatically.
- **User Memory & Context Isolation**: Strict data isolation per user with persistent memory for tailored future research.

---

## 2. Part 1 Features Implemented

- **FastAPI & Async Architecture**: Modular, extensible architecture prepared for Part 2 (Financial Data, AI Research Agents, Daily Briefings) and Part 3 (Google Workspace, Documents, Voice & Image analysis).
- **PostgreSQL Database Schema**:
  - `users`: Telegram User ID mapping, onboarding state, timestamps.
  - `user_preferences`: Role, target markets, briefing time, response style (`quick`, `standard`, `detailed`).
  - `watchlists`: Ticker symbols, company names, markets, priority.
  - `user_interests`: Financial topics (AI, Earnings, M&A, Interest Rates, Inflation), priority.
  - `conversations` & `messages`: Thread history tracking user/assistant/system messages and types.
  - `user_memory`: Key-value persistent store for preference/fact recall.
- **Alembic Database Migrations**: Version-controlled DB schema migration scripts (`001_initial_schema.py`).
- **Conversational Onboarding State Machine**: State transitions (`NEW` -> `ASK_ROLE` -> `ASK_MARKETS` -> `ASK_WATCHLIST` -> `ASK_INTERESTS` -> `ASK_BRIEFING_TIME` -> `ASK_RESPONSE_STYLE` -> `COMPLETED`).
- **Natural Language Profile Extractor**: Rule-based regex & NLP keyword parsing with optional LLM hook.
- **Demo Mode (`DEMO_MODE=true`)**: Full system functionality without requiring live financial data or LLM API keys.
- **Telegram Bot Client & Handler**: Webhook endpoint (`POST /api/v1/telegram/webhook`) & local polling runner script (`scripts/run_polling.py`).
- **Docker Setup**: `docker-compose.yml` for PostgreSQL, Redis, and FastAPI Backend containers.
- **Automated Test Suite**: 100% test coverage using `pytest` & `pytest-asyncio`.

---

## 3. Directory Structure

```text
financial-assistant/
├── backend/
│   ├── app/
│   │   ├── api/             # Health check & Telegram webhook routes
│   │   ├── core/            # Config, logging, security
│   │   ├── database/        # Engine, session, base model
│   │   ├── models/          # SQLAlchemy DB models
│   │   ├── schemas/         # Pydantic request/response validation
│   │   ├── services/        # User, Onboarding, Conversation, Memory, Assistant services
│   │   ├── telegram/        # Bot client & update handler
│   │   ├── integrations/    # Stubs for Part 2 & 3 (LLM, Market Data)
│   │   ├── agents/          # Stubs for Part 2 Research Agents
│   │   ├── scheduler/       # Stubs for Daily Briefings & Smart Alerts
│   │   ├── notifications/   # Push notification dispatcher
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # Pytest unit & integration tests
│   └── requirements.txt
├── migrations/              # Alembic migration scripts
├── scripts/
│   └── run_polling.py      # Local development polling script
├── docker/
│   └── Dockerfile
├── .env.example
├── docker-compose.yml
├── alembic.ini
└── README.md
```

---

## 4. Setup & Running Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL (or Docker Desktop)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

---

### A. Quick Start using Docker Compose (Recommended)

1. Clone the repository and navigate to project root:
   ```bash
   cd financial-assistant
   ```

2. Copy `.env.example` to `.env`:
   ```bash
   # Windows PowerShell
   copy .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```

3. Configure your `TELEGRAM_BOT_TOKEN` in `.env`.

4. Start containers with Docker Compose:
   ```bash
   docker-compose up --build
   ```

5. Access backend health endpoint at `http://localhost:8000/health`.

---

### B. Local Development Setup (Without Docker)

1. Create a virtual environment and activate it:
   ```bash
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Set up `.env` file with your local database URL:
   ```env
   DATABASE_URL=sqlite:///./financial_assistant.db
   # Or PostgreSQL: postgresql://postgres:postgres@localhost:5432/financial_assistant
   DEMO_MODE=true
   TELEGRAM_BOT_TOKEN=your_token_here
   ```

4. Run database migrations:
   ```bash
   alembic upgrade head
   ```

5. Start the FastAPI backend server:
   ```bash
   # Windows / Linux / macOS
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

---

### C. Running Telegram Bot in Local Development (Polling Mode)

If you are developing locally without setting up a public HTTPS webhook (e.g. ngrok), use the long-polling runner:

```bash
python scripts/run_polling.py
```

Open Telegram, search for your bot, and send any text message (e.g., `"Hello"` or `"I'm an equity research analyst covering US tech and watching NVDA"`). The bot will engage in natural conversational onboarding.

---

### D. Running Test Suite

Run the full automated test suite to verify user creation, natural language profile extraction, onboarding state machine, conversation persistence, memory store, and health checks:

```bash
# Set PYTHONPATH to backend directory
# Windows PowerShell:
$env:PYTHONPATH="backend"
pytest backend/tests -v

# Linux / macOS:
PYTHONPATH=backend pytest backend/tests -v
```

---

## 5. Verification Checklist

- [x] `/health` endpoint returns `HTTP 200 OK` and `"database": "connected"`
- [x] Telegram text update creates user, preference, and initial active conversation thread
- [x] Onboarding handles single-response and multi-response natural user messages
- [x] User watchlists, interests, role, markets, briefing time, and response style persist in PostgreSQL
- [x] Full user isolation enforced on all queries
- [x] Key-value memories saved to `user_memory` table
- [x] Stubs and clean interfaces prepared for Part 2 & Part 3 additions
