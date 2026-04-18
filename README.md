# Career Coach

An AI-powered career coaching app built with Django, Temporal, Vite/React, Zustand, and Ollama (llama3.2).

## Prerequisites

- Docker + Docker Compose
- [Ollama](https://ollama.com) installed and running on your host machine

## Setup

### 1. Pull the LLM model

```bash
ollama pull llama3.2
```

Verify it's ready:
```bash
curl http://localhost:11434/api/tags
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env if needed (e.g. change OLLAMA_MODEL)
```

### 3. Start everything

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on port 5432
- **Temporal server** on port 7233 (UI at http://localhost:8088)
- **Django backend** on port 8000
- **Temporal worker** (background job processor)
- **Frontend** at http://localhost:80

First run will run Django migrations automatically.

### 4. Open the app

Visit http://localhost and sign up.

## Development (without Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
# Set env vars (or create a .env in backend/)
export DATABASE_URL=postgresql://career:career@localhost:5432/career
export OLLAMA_BASE_URL=http://localhost:11434
export TEMPORAL_HOST=localhost:7233
python manage.py migrate
python manage.py runserver
# In another terminal:
python worker.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:5173
```

## Architecture

```
User -> React (Vite + Zustand) -> Django REST API -> Temporal Workflow
                                                   -> Ollama (llama3.2)
                                                   -> PostgreSQL
```

### LLM Agents

| Agent | Purpose |
|-------|---------|
| EXTRACTOR | Parses resume PDF into structured JSON profile |
| PERSONA_DETECTOR | Classifies user as Pivot / Grow / Graduate |
| OPENING_GENERATOR | Creates personalised first message from profile |
| PATH_GENERATOR | Generates 3 career path cards per round |
| TOPIC_CLASSIFIER | Guards against off-topic (non-career) queries |
| CONVERSATION_ROUTER | Routes free-text messages to correct handler |

### Flow

1. Signup / Login
2. Upload PDF resume -> EXTRACTOR -> UserProfile stored
3. Start session -> SSE streams personalised opening message
4. Goal discovery (alive moments, friction, direction, geography)
5. PATH_GENERATOR -> 3 path cards
6. Select path or regenerate (max 3 rounds, then forced recommendation)
7. Free-text chat available at every state (TOPIC_CLASSIFIER guards off-topic)
8. /metrics dashboard shows session funnel, persona breakdown, action counts

## Metrics Dashboard

Visit http://localhost/metrics after starting a session.
