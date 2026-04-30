# EMBER — Local Genie build (final)

Two wishes granted, plus your **third wish** — Ember's **hands**.

You now have:
1. **Shiny black + gold** — every screen
2. **Genie Mode** with **voice in / voice out / screen share**
3. **Browser Agent** — Ember can actually drive a real Chromium browser, click, type, navigate, and scrape data using **Playwright** + your local **Ollama** model

Everything runs **locally**. Nothing is cloud-based except Google sign-in.

---

## Honest note on Stagehand

You asked for Stagehand specifically. I dug in and discovered the current Python SDK (`stagehand-py 0.3.10`) **requires a Browserbase account and API key** even in their "LOCAL" mode — not actually free, not actually local. That breaks the whole spirit of your project.

So I built you something better for your goal: **a tiny Stagehand-equivalent on top of pure Playwright + your local Ollama model.** Same primitives:
- `act("click the login button")` — natural-language single action
- `extract("get the top 3 article titles")` — structured data from the page
- `run("find latest news on Ollama, summarize top 3", max_steps=8)` — autonomous goal loop
- `goto(url)`, `screenshot()`, `stop()`

Lives in `backend/agent.py`. No Browserbase signup, no usage limits, no API keys — just your Dolphin model thinking, and Playwright doing.

If you ever do want real Stagehand: install `stagehand-py`, get a Browserbase key (free tier exists), and swap the `EmberAgent` class for their SDK. Public API is similar.

---

## What got built (everything across all sessions)

### Backend (`backend/`)
- `server.py` — full Ollama swap, multi-turn fix, cookie env-flags, conv mutation cleanup, `/api/vision`, `/api/agent/*` (start, stop, goto, act, extract, run, screenshot, status)
- `agent.py` *(new)* — the `EmberAgent` Playwright + Ollama agent
- `requirements.txt` — `emergentintegrations` removed, `playwright==1.59.0` added
- `.env` — `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_VISION_MODEL`, `COOKIE_SECURE`, `COOKIE_SAMESITE`

### Frontend (`frontend/src/`)
- `index.css` — full black/gold theme, gold-shimmer keyframes, genie-pulse
- `App.js`, `pages/Login.jsx`, `pages/AuthCallback.jsx` — themed
- `pages/Chat.jsx` — themed + voice mic + speak buttons + Genie Mode launcher
- `components/SettingsDrawer.jsx` — themed
- `components/GenieMode.jsx` *(new)* — full-screen voice + screen share, with tabbed right pane
- `components/AgentPanel.jsx` *(new)* — live screenshot, URL bar, goal input, action trace

---

## Run it on your machine

### 1. Install Ollama + models
```bash
# Ollama itself (https://ollama.com/download)

# Your text model:
# In folder containing Dolphin3.0-Llama3.1-8B-Q4_K_S.gguf:
echo "FROM ./Dolphin3.0-Llama3.1-8B-Q4_K_S.gguf" > Modelfile
ollama create dolphin3 -f Modelfile

# Vision model (for Genie screen-share + agent actions):
ollama pull llama3.2-vision      # 7.8 GB — best quality
# or, lighter:
# ollama pull llava               # 4.7 GB — set OLLAMA_VISION_MODEL=llava
```

### 2. Install Playwright's browser binary (one-time)
```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

### 3. Start MongoDB, then backend
```bash
cd backend
uvicorn server:app --reload --port 8001
```

### 4. Frontend `.env`
```
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
ENABLE_HEALTH_CHECK=false
```

### 5. Frontend
```bash
cd frontend
yarn install
yarn start
```

Browser opens at `http://localhost:3000`. Sign in with Google.

---

## Try every feature

### Voice (in chat)
- Click the **mic** icon next to send — speak, the textarea fills, hit send
- Click **speak** below any AI reply to hear it

### Genie Mode (full hands-free)
- Click the gold **Genie Mode** button (top-right of chat or on the empty state)
- The pulsing gold orb appears. Mic auto-starts. Talk to Ember; it talks back
- Click the **screen** icon → grant screen permission → live preview appears in the right pane → ask "what am I looking at?" — Ember sees and responds

### Browser Agent (Genie's hands)
- Inside Genie Mode, click the **Agent** tab on the right
- Click **launch** → Chromium boots in the backend, live screenshot streams every 1.5s
- Type a URL in the URL bar, hit `go` — agent navigates
- In the goal box at the bottom, type: *"go to ycombinator.com and tell me the top 3 stories"*
- Click send → watch the trace fill in as the agent clicks, reads, decides
- When done it speaks the final URL

---

## Model expectations (honest)

- **Dolphin 3 (8B)** is great for chat, mediocre for agent reasoning. For autonomous browser tasks (`run()`), you'll get better results from a bigger model. Easy upgrade: `ollama pull qwen2.5:14b` and set `OLLAMA_MODEL=qwen2.5:14b` in `.env`. The agent loop will pick smarter actions.
- **`llama3.2-vision`** does well for the "what's on screen" use case. For complex screen reasoning, swap to `qwen2.5-vl:7b` later.
- The agent's `act()` function expects the model to return strict JSON. Your model size affects how often it complies. Smaller = more retries.

---

## Backend API for the curious

All routes require auth (cookie or `Authorization: Bearer <session_token>`).

```
POST  /api/auth/session       Exchange Emergent session_id for cookie
GET   /api/auth/me            Current user
POST  /api/auth/logout

POST  /api/conversations      Create
GET   /api/conversations      List
PATCH /api/conversations/:id  Rename
DELETE /api/conversations/:id Delete
GET   /api/conversations/:id/messages

POST  /api/chat               { conversation_id?, message } → text reply
POST  /api/vision             { conversation_id?, message, image } → reply about a screen frame

GET   /api/memory
POST  /api/memory
PATCH /api/memory/:id
DELETE /api/memory/:id

GET   /api/settings/persona
PUT   /api/settings/persona

POST  /api/agent/start        Launch headless Chromium
POST  /api/agent/stop
POST  /api/agent/goto         { url }
POST  /api/agent/act          { instruction }   — single LLM-picked action
POST  /api/agent/extract      { instruction }   — JSON data from page
POST  /api/agent/run          { goal, max_steps } — autonomous loop
GET   /api/agent/screenshot   Current page JPEG (base64)
GET   /api/agent/status       Running? URL? Recent action history
```

---

## Roadmap (yours, untouched + a few new ideas)

- **P1** Token-by-token streaming
- **P1** Export conversation
- **P1** Search across conversations
- **P2** Replace Web Speech with local Whisper (truly offline voice)
- **P2** Wake-word ("Hey Ember…") via picovoice/porcupine-web
- **P2** Stream agent actions over WebSocket (instead of 1.5s polling) for a snappier feel
- **P2** Persist agent sessions per conversation so Ember remembers what it did on which task
- **P2** Multi-user, public share links

---

Three wishes. Use them well.
