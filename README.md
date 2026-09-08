# Ember

An honest AI companion — not a script. Ember remembers you, pushes back when you're wrong, admits uncertainty, and skips the sycophancy. Built on a local [Ollama](https://ollama.com) model with a FastAPI + MongoDB backend and a warm, editorial React frontend.

## Architecture

| Layer      | Stack                                                        |
| ---------- | ------------------------------------------------------------ |
| Frontend   | React 19, Tailwind CSS, react-markdown, CRACO (Create React App) |
| Backend    | FastAPI, Motor (async MongoDB), httpx                        |
| LLM        | Local Ollama (`/api/chat`), inferred from `.env`             |
| Database   | MongoDB collections: `users`, `user_sessions`, `conversations`, `messages`, `memories`, `user_settings` |

## Prerequisites

- Python 3.11+
- Node.js 18+ / Yarn 1.x
- [Ollama](https://ollama.com/download) running locally
- MongoDB running locally (or a MONGO_URL)

## Setup

### 1. Backend

```bash
cd backend
pip install -r ../requirements.txt
cp .env.example .env   # review values
uvicorn backend.server:app --reload --port 8000
```

`server.py` loads `.env` from the `backend/` directory. Minimum required variables:

| Variable      | Default                   | Purpose                              |
| ------------- | ------------------------- | ------------------------------------ |
| `MONGO_URL`   | *(required)*              | MongoDB connection string            |
| `DB_NAME`     | `ember`                   | Database name                        |
| `CORS_ORIGINS`| `*`                       | Comma-separated allowed origins      |
| `OLLAMA_URL`  | `http://localhost:11434`  | Local Ollama endpoint                |
| `OLLAMA_MODEL`| `dolphin3`                | Ollama model name                    |

### 2. Register the Ollama model

Create a `Modelfile` in a folder with your GGUF and register it under the name matching `OLLAMA_MODEL` (default `dolphin3`):

```
FROM ./Dolphin3.0-Llama3.1-8B-Q4_K_S.gguf
```

```bash
ollama create dolphin3 -f Modelfile
ollama serve
```

### 3. Frontend

```bash
cd frontend
yarn install
REACT_APP_BACKEND_URL=http://localhost:8000 yarn start
```

Set `REACT_APP_BACKEND_URL` in `frontend/.env.local` (e.g. `REACT_APP_BACKEND_URL=http://localhost:8000`) — the frontend prefixes all API calls with `${REACT_APP_BACKEND_URL}/api`. On localhost it defaults to `http://localhost:8000`, so this is optional for local dev.

## API Overview

All routes are prefixed with `/api` and require auth (cookie `session_token` or `Authorization: Bearer ...`):

| Method | Path                            | Purpose                          |
| ------ | ------------------------------- | -------------------------------- |
| POST   | `/auth/session`                 | Exchange OAuth session for a token |
| GET    | `/auth/me`                      | Current user                     |
| POST   | `/auth/logout`                  | Invalidate session + clear cookie |
| POST   | `/chat`                         | Send a message (request/response LLM) |
| POST   | `/chat/stream`                  | Send a message (SSE streaming LLM response) |
| GET/POST/PATCH/DELETE | `/conversations[/id]` | Conversation CRUD            |
| GET    | `/conversations/{id}/messages`  | Message history                  |
| GET/POST/PATCH/DELETE | `/memory[/id]`        | Long-term memory CRUD            |
| GET/PUT| `/settings/persona`             | Custom persona                   |
| GET    | `/`                             | Root banner (model name)          |
| GET    | `/health`                       | Health check: `{"status":"ok"}`   |

> CSRF: mutating auth endpoints (`/auth/session`, `/auth/logout`) reject requests whose
> `Origin` is not in `CORS_ORIGINS` (`backend/.env`, default `http://localhost:3000,http://127.0.0.1:3000`) or the same host.

## Testing

```bash
# Unit tests (no live Mongo/Ollama needed)
pytest

# End-to-end suites (require a live backend, MongoDB, and Ollama)
pytest backend/tests/test_ember_auth_api.py --maxfail=1
```

> The end-to-end pytest suites hit a live backend and MongoDB. Point `REACT_APP_BACKEND_URL` at the running server before running them.

## Deployment

- **Docker / Fly**: `Dockerfile` builds the FastAPI app and runs `uvicorn backend.server:app` on port `8080`.
- **Render / Heroku**: `Procfile` runs `uvicorn backend.server:app --host 0.0.0.0 --port $PORT`.

Deployment images must include Ollama (or set `OLLAMA_URL` to an accessible instance) — Ember generates responses against a local model, not a hosted LLM API.