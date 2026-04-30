# Ember — local Ollama edition

## Original problem statement
Parent asked help fixing son's GitHub project (https://github.com/tinysecrets/real_Genie.git) — a personal AI companion ("Ember"). Goal: make it run, keep his code style intact, swap to local Ollama (Dolphin 3.0 Llama 3.1 8B Q4_K_S) for free / private / offline use.

## Architecture
- **Frontend**: React 19 + CRACO + Tailwind + react-markdown + lucide-react (UNCHANGED — son's design preserved 100%)
- **Backend**: FastAPI + Motor (MongoDB async) — son's structure preserved
- **LLM**: **Ollama** (local), default model `dolphin3` — was Claude Sonnet 4.5 via emergentintegrations
- **Memory extractor**: same Ollama model with `format: "json"` mode — was Claude Haiku 4.5
- **Auth**: Emergent Google OAuth (UNCHANGED)
- **DB collections**: users, user_sessions, user_settings, conversations, messages, memories

## Changes this session (2026-01)
1. Cloned son's GitHub repo into `/app` with zero code changes
2. Removed `emergentintegrations` import + dependency
3. Added `ollama_chat()` helper using existing `httpx` import
4. Replaced LLM calls in `/api/chat` and memory extractor
5. Fixed multi-turn chat history bug (was replaying user messages causing N extra LLM calls + hallucinated context)
6. Made cookie `secure`/`samesite` env-driven so localhost dev works
7. Cleaned up `conv` dict mutation in `/api/chat`
8. Memory extractor uses Ollama JSON mode for reliability with smaller models
9. Verified backend boots, lint passes, `/api/` returns model name

## Files touched
- `backend/server.py` — 9 small in-place edits, structure preserved
- `backend/.env` — swapped Emergent key for Ollama vars + cookie flags
- `backend/requirements.txt` — removed `emergentintegrations==0.1.0`
- `INSTRUCTIONS_FOR_HIM.md` — new, run-at-home guide for the son

## Next action items (for the son)
1. Install Ollama, register Dolphin GGUF as `dolphin3`, run `ollama serve`
2. Set `REACT_APP_BACKEND_URL=http://localhost:8001` in `frontend/.env`
3. Start MongoDB → `uvicorn server:app --reload --port 8001` → `yarn start`
4. Sign in via Google, send a message, watch Ember reply locally

## Future / Backlog (his own roadmap)
- P1 token-by-token streaming
- P1 export conversation (markdown / JSON)
- P1 search across conversations
- P2 voice I/O (whisper + TTS)
- P2 custom persona editor UI
- P2 multi-user, public share links
- P2 pagination on conversation/memory endpoints
