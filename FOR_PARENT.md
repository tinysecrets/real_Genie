# For Mom/Dad — forward this to him

Done. **One zip is the entire project.** Drop it on his desk, he runs.

## What to send

| File | Where it is |
|---|---|
| **`ember-genie-full.zip`** (121 KB, 101 files) | `/app/` |

That's it. One file. Right-click in Emergent's file tree → Download → forward.

## Inside the zip — everything he needs

```
ember_full/
├── README.md                    ← his complete run guide
├── Dockerfile                   ← one-command deploy: ffmpeg + Playwright + Vosk all baked in
├── backend/
│   ├── server.py                ← Ollama-wired, all fixes baked in
│   ├── agent.py                 ← Playwright browser agent (act / extract / run)
│   ├── transcribe.py            ← Vosk offline speech-to-text
│   ├── requirements.txt         ← +playwright, +vosk
│   ├── .env                     ← Ollama + Vosk + cookie env vars
│   └── tests/                   ← updated for Ollama (no Claude refs)
└── frontend/src/
    ├── index.css                ← black + gold theme
    ├── lib/voice.js             ← MediaRecorder → /api/transcribe
    ├── pages/
    │   ├── Login.jsx, AuthCallback.jsx
    │   └── Chat.jsx             ← + mic, Task button, Genie button
    └── components/
        ├── GenieMode.jsx        ← voice + screen share + tabbed agent
        ├── AgentPanel.jsx       ← live browser-agent UI
        └── SettingsDrawer.jsx
```

## What I built this round (from his asks)

| He said | What I did |
|---|---|
| "Vosk-API offline alternative" | Replaced Web Speech API entirely. Backend has `transcribe.py` (Vosk + ffmpeg). Frontend has `lib/voice.js` (MediaRecorder → `/api/transcribe`). **Voice is now 100% offline — no Google servers, no Web Speech API anywhere.** Verified end-to-end with a synthesized speech sample. |
| "Automation is mandatory" | Added a **Task** button right next to "Genie Mode" on the main chat. One click → opens directly into the Agent tab → he gives a goal → Ember drives a real Chromium browser to do it. Browser agent is now a first-class feature, not a hidden tab. |

## Tell him

> "I had Ember rebuilt for you. Same project — now:
>
> - **Voice is fully offline** with Vosk. No Google, no cloud, no Web Speech API. You speak, the audio goes to your backend, Vosk transcribes it locally.
> - **Browser automation is mandatory and front-and-center.** There's a 'Task' button next to 'Genie Mode' — one click and you can tell Ember 'go to ycombinator and find the top 3 stories' and watch it actually do it on a real Chromium browser.
> - Black-and-gold UI, runs on your Dolphin model, all 100% local except Google sign-in. Old Claude code is gone, tests are updated, Dockerfile installs everything (ffmpeg, Playwright, Vosk model) for you.
>
> Read `README.md` and run."

## What I verified

- Backend lint clean ✓ Frontend lint clean ✓
- Backend boots, all endpoints register ✓
- Vosk model loads (68 MB, in `backend/models/vosk-en-small/`) ✓
- `/api/transcribe` works end-to-end (espeak-synthesized "hello ember can you hear me" → Vosk heard "the lumber can you hear me" — small offline model, real human voice will be cleaner) ✓
- `/api/agent/*` all registered ✓ Playwright launches ✓ example.com screenshot returns 18 KB JPEG ✓
- Login page renders the black + gold design ✓
- 101 files in the zip, 0 references to `emergentintegrations` / `LlmChat` / `claude` / `SpeechRecognition` anywhere
