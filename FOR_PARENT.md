# For Mom/Dad — forward this to him

## What to send him

1. **The zip**: `/app/ember-genie-build.zip` (37 KB)
2. **This file**: `/app/FOR_PARENT.md` (which you're reading)
3. **The full guide**: `/app/INSTRUCTIONS_FOR_HIM.md` (everything he needs)

That's it. Three things. He unzips, drops the files into his GitHub clone, and runs.

---

## What's in the zip

```
ember_handoff/
├── README_GENIE_BUILD.md          ← his run guide
├── backend/
│   ├── server.py                  ← REPLACE his existing one
│   ├── agent.py                   ← NEW file
│   ├── requirements.txt           ← REPLACE
│   └── .env                       ← REPLACE
└── frontend/src/
    ├── index.css                  ← REPLACE
    ├── App.js                     ← REPLACE
    ├── pages/
    │   ├── Login.jsx              ← REPLACE
    │   ├── AuthCallback.jsx       ← REPLACE
    │   └── Chat.jsx               ← REPLACE
    └── components/
        ├── SettingsDrawer.jsx     ← REPLACE
        ├── GenieMode.jsx          ← NEW file
        └── AgentPanel.jsx         ← NEW file
```

10 files he replaces, 3 brand-new files. Same folder structure as his GitHub repo — drop them in, overwrite, done.

---

## Tell him this in plain English

> "I had Ember rebuilt for you. Same project, same auth, same look-and-feel structure — but now it's:
>
> - **Black and gold** instead of cream and terracotta (your wish)
> - Runs on **your local Dolphin model** instead of paid Claude
> - Has **voice input + voice output** (you talk, it listens, it talks back)
> - Has **screen share** (it sees what you're doing)
> - Has a **browser agent** — it can actually click, type, and navigate websites for you
>
> Just unzip, drop the files into your project, and follow `README_GENIE_BUILD.md`."

---

## If he asks "what about Stagehand specifically?"

Tell him the truth: I tried `stagehand-py 0.3.10`, but it requires a paid Browserbase API key even in their "LOCAL" mode. So I built him a custom equivalent on top of pure Playwright + his Ollama model — same `act()`, `extract()`, `run()` primitives, no signups, no bills. Lives in `backend/agent.py`. He can swap it for the real Stagehand later if he ever decides to pay for Browserbase.

---

## How to send the zip

Right-click `ember-genie-build.zip` in the Emergent file tree → Download → email or AirDrop to him.

If you can't find the file tree: ask me "give me the download link" and I'll tell you exactly where to click.
