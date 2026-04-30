# Ember — Local Genie build (final)

## Original problem statement
Parent asked help fixing son's "Ember" project (https://github.com/tinysecrets/real_Genie.git). Son's vision: personal AI dolphin/genie with shiny black + gold UI, voice in/out, screen share, and **browser automation** (Playwright + Stagehand).

## Architecture
- **Frontend**: React 19 + CRACO + Tailwind + react-markdown + lucide-react + Web Speech API + getDisplayMedia
- **Backend**: FastAPI + Motor (MongoDB async) + Playwright
- **LLM (text)**: Ollama, default `dolphin3` (Dolphin 3.0 Llama 3.1 8B Q4_K_S, user-loaded)
- **LLM (vision)**: Ollama, default `llama3.2-vision` (configurable to `llava`)
- **Browser Agent**: Custom `EmberAgent` using pure Playwright + Ollama (Stagehand-equivalent; chose this over Stagehand-py because v0.3.10 still requires Browserbase API key even in "LOCAL" mode, breaking free/local goal)
- **Auth**: Emergent Google OAuth (UNCHANGED)
- **DB collections**: users, user_sessions, user_settings, conversations, messages, memories

## Final state (2026-01)
- [x] Cloned son's GitHub repo, structure preserved
- [x] Removed `emergentintegrations`, swapped to local Ollama via httpx
- [x] Multi-turn chat history bug fixed (transcript folded into system prompt)
- [x] Cookie `secure`/`samesite` env-driven for localhost
- [x] `conv` dict mutation cleanup
- [x] Memory extractor uses Ollama JSON mode
- [x] Full UI redesigned to shiny black + gold
- [x] Voice input via Web Speech API
- [x] Voice output via SpeechSynthesis
- [x] Genie Mode component (voice + screen + tabbed right pane)
- [x] Screen capture via getDisplayMedia → /api/vision endpoint with multimodal Ollama
- [x] **Browser Agent**: Playwright + Ollama (act/extract/run/goto/screenshot)
- [x] **AgentPanel** UI inside Genie Mode (live screenshot, URL bar, goal input, action trace)
- [x] Tested: Playwright launches, navigates example.com, screenshot returns 18KB JPEG
- [x] All Python and JS lint checks pass
- [x] Backend boots, all endpoints registered (agent/* returns 401 without auth as expected)

## Files modified
- `backend/server.py` — agent routes, vision route, Ollama swap, history fix, cookie env, conv cleanup
- `backend/.env` — Ollama vars + cookie flags + vision model
- `backend/requirements.txt` — emergentintegrations removed, playwright added
- `frontend/src/index.css` — black/gold theme + keyframes
- `frontend/src/App.js`, `pages/Login.jsx`, `pages/AuthCallback.jsx`, `pages/Chat.jsx`, `components/SettingsDrawer.jsx`

## Files created
- `backend/agent.py` — EmberAgent (Playwright + Ollama)
- `frontend/src/components/GenieMode.jsx` — voice + screen + tabbed pane
- `frontend/src/components/AgentPanel.jsx` — live browser-agent UI
- `INSTRUCTIONS_FOR_HIM.md` — full handoff doc with run guide + API reference

## Next action items (for the son)
1. Install Ollama → register Dolphin GGUF as `dolphin3` → `ollama pull llama3.2-vision`
2. `pip install -r requirements.txt` and `playwright install chromium`
3. Start MongoDB → backend → frontend per `INSTRUCTIONS_FOR_HIM.md`
4. Click Genie Mode → try voice → try screen share → try Agent tab → "launch" → goal: "go to ycombinator.com and list top 3"

## Future / Backlog
- P1 token-by-token streaming, conversation export, search
- P2 swap Web Speech for local Whisper (offline voice)
- P2 wake-word detection (picovoice/porcupine-web)
- P2 stream agent actions over WebSocket (vs 1.5s polling)
- P2 persist agent sessions per conversation
- P2 multi-user, share links, pagination
