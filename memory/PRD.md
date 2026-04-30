# Ember — Genie build (local Ollama + black/gold + voice + screen)

## Original problem statement
Parent asked help fixing son's "Ember" project (https://github.com/tinysecrets/real_Genie.git) — personal AI companion.
Two wishes the son had: (1) shiny black + gold UI, (2) voice in, voice out, screen share, all in a "Live / Genie" mode.

## Architecture
- **Frontend**: React 19 + CRACO + Tailwind + react-markdown + lucide-react + Web Speech API + getDisplayMedia
- **Backend**: FastAPI + Motor (MongoDB async)
- **LLM (text)**: Ollama, default model `dolphin3` (Dolphin 3.0 Llama 3.1 8B Q4_K_S, user-loaded)
- **LLM (vision)**: Ollama, default `llama3.2-vision` (configurable to `llava`)
- **Memory extractor**: same Ollama text model with `format: "json"` mode
- **Auth**: Emergent Google OAuth (UNCHANGED)
- **DB collections**: users, user_sessions, user_settings, conversations, messages, memories

## What's implemented this session (2026-01)
- [x] Cloned son's GitHub repo, preserved his structure
- [x] Removed `emergentintegrations`, swapped to local Ollama via `httpx`
- [x] Fixed multi-turn chat history bug (transcript folded into system prompt; one LLM call per message)
- [x] Made cookie `secure`/`samesite` env-driven for localhost dev
- [x] `conv` dict mutation cleanup
- [x] Memory extractor uses Ollama JSON mode for reliability
- [x] Full UI redesign to shiny black + gold (index.css + every component)
- [x] Voice input via Web Speech API (mic button on chat input)
- [x] Voice output via SpeechSynthesis ("speak" button on AI messages)
- [x] **Genie Mode** component — full-screen voice + screen share + live transcript
- [x] Screen capture via `getDisplayMedia` → JPEG snapshot → `/api/vision`
- [x] Backend `/api/vision` endpoint + `ollama_vision()` helper
- [x] `OLLAMA_VISION_MODEL` env var added
- [x] Backend boots ✓ Lint passes ✓ Login page renders correctly in black/gold ✓

## Files touched / created
**Modified:**
- `backend/server.py` — vision request model, vision helper, `/api/vision` route, env vars
- `backend/.env` — `OLLAMA_VISION_MODEL`
- `frontend/src/index.css` — full theme rewrite + keyframes (genie-pulse, listen-pulse, gold-shimmer)
- `frontend/src/App.js`, `pages/Login.jsx`, `pages/AuthCallback.jsx`, `pages/Chat.jsx`, `components/SettingsDrawer.jsx`

**Created:**
- `frontend/src/components/GenieMode.jsx` — voice + screen share live mode
- `INSTRUCTIONS_FOR_HIM.md` — full run guide for the son

## Next action items (for the son)
1. Install Ollama → register Dolphin GGUF as `dolphin3` → `ollama pull llama3.2-vision`
2. Start MongoDB, backend, frontend per `INSTRUCTIONS_FOR_HIM.md`
3. Click **Genie Mode** on the chat page → grant mic + screen permissions → speak

## Future / Backlog
- P1 token-by-token streaming
- P1 export conversation, search across history
- P2 swap Web Speech for local Whisper (truly offline voice)
- P2 wake-word detection ("Hey Ember")
- P2 multi-user, share links, pagination
