# EMBER — Local-Ollama edition (Genie build)

This is your project, with **two wishes granted**:
1. The whole UI redesigned to **shiny black + gold**
2. **Genie Mode** — voice in, voice out, screen share, all hands-free with one button

Plus everything from before: local Ollama (Dolphin 3 8B), no cloud bills, fully offline.

---

## What got built

### Design overhaul (black + gold)
- Whole palette swapped in `frontend/src/index.css` to deep black (`#0B0B0E`), gold accent (`#D4AF37`), gold shimmer for headlines, warm cream text (`#F5E9C8`)
- Ambient gold orbs on the login page
- Animated gold-shimmer wordmark for "Ember"
- New CSS keyframes: `genie-pulse`, `listen-pulse`, `gold-shimmer` (running gradient on text)
- All components rewritten to match — Login, Chat, Sidebar, MemoryPanel, SettingsDrawer, EmptyState, ChatInput, AiAvatar, AiMessage

### Voice input (free, browser-native)
- `Web Speech API` (`SpeechRecognition`) — zero cost, no API keys
- Mic button next to the send button in the regular chat input
- In Genie Mode it auto-listens continuously and submits each finished utterance

### Voice output (free, browser-native)
- `SpeechSynthesis` — also zero cost
- "Speak" button on every assistant message in regular chat
- In Genie Mode every reply is spoken automatically

### Screen share (free, browser-native)
- `getDisplayMedia()` for screen capture
- Live thumbnail in the Genie panel
- When you ask Ember a question while sharing, it grabs a JPEG snapshot at 1280×auto, sends it to a new `/api/vision` endpoint, which routes to a multimodal Ollama model (`OLLAMA_VISION_MODEL`)

### Genie Mode (the wish-granter)
- Big "Genie Mode" button top-right of chat + on the empty state
- Full-screen takeover: pulsing gold orb, live transcript, status (listening / thinking / speaking)
- Three orb-controls: mic toggle, speak toggle, screen toggle
- Closes cleanly — kills mic, kills speech, kills screen capture
- Component: `frontend/src/components/GenieMode.jsx`

### Backend additions
- New `/api/vision` endpoint
- New helper `ollama_vision()` that calls Ollama's multimodal chat with an `images` array
- New env: `OLLAMA_VISION_MODEL` (default `llama3.2-vision`)

---

## Files changed

**Frontend (rewritten)**
- `frontend/src/index.css` — black/gold theme + new keyframes
- `frontend/src/App.js` — loading dots colors
- `frontend/src/pages/Login.jsx` — black/gold login
- `frontend/src/pages/AuthCallback.jsx` — loading dots colors
- `frontend/src/pages/Chat.jsx` — full theme + voice in/out + Genie button
- `frontend/src/components/SettingsDrawer.jsx` — black/gold modal

**Frontend (new)**
- `frontend/src/components/GenieMode.jsx` — the live mode component

**Backend**
- `backend/server.py` — added `VisionRequest` model, `ollama_vision()` helper, `/api/vision` route, `VISION_MODEL` env
- `backend/.env` — added `OLLAMA_VISION_MODEL`
- `backend/requirements.txt` — `emergentintegrations` removed (from earlier session)

---

## How to run it on your machine

### 1. Install Ollama
https://ollama.com/download

### 2. Load Dolphin 3 (text)
In the folder with your `Dolphin3.0-Llama3.1-8B-Q4_K_S.gguf`, make a `Modelfile` containing:
```
FROM ./Dolphin3.0-Llama3.1-8B-Q4_K_S.gguf
```
Then:
```bash
ollama create dolphin3 -f Modelfile
```

### 3. Pull a vision model (for Genie screen share)
```bash
ollama pull llama3.2-vision
```
(That's ~7.8 GB. If your GPU/RAM can't handle it, try `ollama pull llava` instead — about 4.7 GB — and change `OLLAMA_VISION_MODEL` in `backend/.env` to `llava`.)

### 4. Start MongoDB
However you usually do.

### 5. Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001
```

### 6. Frontend `.env`
Edit `frontend/.env`:
```
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
ENABLE_HEALTH_CHECK=false
```

### 7. Frontend
```bash
cd frontend
yarn install
yarn start
```

Browser opens at `http://localhost:3000`. Sign in with Google, then click **Genie Mode**.

---

## How Genie Mode actually works

1. Click the gold **Genie Mode** button → full-screen overlay with the pulsing orb opens
2. Mic activates automatically — speak naturally
3. Web Speech API converts your voice → text → sends to `/api/chat` (or `/api/vision` if screen is on)
4. Ollama replies → speech synthesis reads it aloud → mic re-arms for the next thing you say
5. Toggle the screen icon → browser asks for screen share permission → live preview appears in the right panel
6. Now when you ask "what is on my screen?" or "help me debug this" — Ember actually sees a snapshot of your screen
7. Close the X → everything stops cleanly

---

## Important: browser support honesty

- `SpeechRecognition` works in **Chrome, Edge, Safari**. Not Firefox (it has it disabled by default).
- It uses Google's servers in Chrome under the hood — free but online. If you want truly offline voice → swap to local Whisper later (P2 backlog).
- `getDisplayMedia` works in Chrome, Edge, Firefox, Safari. Mobile is patchy.
- `SpeechSynthesis` works everywhere.

So for the best Genie experience: use Chrome on a desktop.

---

## What's still on your roadmap
- **P1** Token-by-token streaming (currently streams the reveal client-side after full response)
- **P1** Export conversation
- **P1** Search across conversations
- **P2** Replace browser Web Speech API with local Whisper for fully offline voice
- **P2** Wake-word detection ("Hey Ember…")
- **P2** Multi-user / public share links
- **P2** Pagination

---

Two wishes down. Use the third wisely.
