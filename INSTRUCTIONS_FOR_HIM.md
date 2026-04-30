# EMBER — Local-Ollama edition

This is your project, exactly as you wrote it, with **only the LLM swapped from Claude (cloud, paid) to Ollama (local, free)** plus a few honest fixes for problems your original code would have hit.

Nothing about the UI, auth flow, memory system, persona system, or your file structure changed. Same React + FastAPI + MongoDB stack. Same components. Same routes. Same data models.

---

## What was changed (and why)

### Backend (`backend/server.py`)
| Change | Why |
|---|---|
| Removed `from emergentintegrations.llm.chat import LlmChat, UserMessage` | Ollama doesn't need it |
| `MODEL_PROVIDER`/`MODEL_NAME` constants → `OLLAMA_URL` / `OLLAMA_MODEL` from env | So you can pick any model you've pulled in Ollama |
| New helper `ollama_chat(system, user_text, json_mode=False)` | One small function does every LLM call now |
| `extract_memories_async` now calls `ollama_chat(..., json_mode=True)` | Forces Dolphin to emit valid JSON — small models love wandering off |
| `/api/chat` no longer replays old user messages one by one to the LLM | Was doing N extra LLM calls per turn AND letting the model invent its own version of past replies. Now folds the real transcript into the system prompt. **One LLM call per message.** |
| Cookie `secure` and `samesite` are now env-driven | So login actually works on `http://localhost` (browsers drop `secure=True` cookies on plain HTTP) |
| `conv` dict in `/api/chat` no longer gets mutated by `insert_one` | Future-proofs it from the classic `ObjectId is not JSON serializable` trap |
| Removed the `if not EMERGENT_LLM_KEY` early-fail in `/chat` | Not needed anymore |

### `backend/requirements.txt`
| Change | Why |
|---|---|
| Removed `emergentintegrations==0.1.0` | Not used anymore |

### `backend/.env`
| Change | Why |
|---|---|
| Replaced `EMERGENT_LLM_KEY` with `OLLAMA_URL`, `OLLAMA_MODEL`, `COOKIE_SECURE`, `COOKIE_SAMESITE` | Local-friendly defaults |

### Frontend
**Nothing changed.** Not one file. You wrote it well.

---

## How to run it on your machine

### 1. Install Ollama
Download from https://ollama.com/download → install → done. It runs as a background service.

### 2. Load your Dolphin model into Ollama
In the folder containing `Dolphin3.0-Llama3.1-8B-Q4_K_S.gguf`, create a file called `Modelfile` with one line:

```
FROM ./Dolphin3.0-Llama3.1-8B-Q4_K_S.gguf
```

Then in that folder:
```bash
ollama create dolphin3 -f Modelfile
```

That registers the model under the name `dolphin3` (which matches `OLLAMA_MODEL` in `backend/.env`).

Test it:
```bash
ollama run dolphin3 "say hi"
```

### 3. Start MongoDB
Whatever way you usually run it. Default URL `mongodb://localhost:27017` is what `backend/.env` expects.

### 4. Start the backend
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
```

Test it:
```bash
curl http://localhost:8001/api/
# → {"message":"Ember is here.","model":"dolphin3"}
```

### 5. Set the frontend's backend URL
Edit `frontend/.env`:
```
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
ENABLE_HEALTH_CHECK=false
```

### 6. Start the frontend
```bash
cd frontend
yarn install
yarn start
```

Browser opens at `http://localhost:3000`. You should see your Login page.

---

## A couple things to know

### Auth still goes through Emergent's Google OAuth
That part of your code is unchanged. The Google sign-in button will still bounce off `auth.emergentagent.com` and redirect back. If that ever stops working for local dev, you can either:
- Run with ngrok so you have a real HTTPS URL
- Or write a tiny "dev login" route that skips Google for testing

### Dolphin 3 (8B) is not Claude
Your honesty principles in the system prompt are great, but a small local model will sometimes:
- Forget the rules halfway through a long answer
- Be slower (5–30 sec per response depending on your GPU)
- Hallucinate more than Claude did

That's the trade for free + private + offline. Ember will still feel like Ember, just a less polished one.

### If memory extraction stops working
Check the backend logs for `Memory extraction failed: ...`. Usually means the model returned text that wasn't valid JSON. The `json_mode=True` flag makes this rare on Ollama, but not impossible.

---

## What's still on your roadmap (from your PRD)
- P1 token-by-token streaming
- P1 export conversation
- P1 search
- P2 voice I/O, custom persona editor, multi-user, public share links

Build whatever excites you next. Your foundation is solid.

— Note: everything here was done with your code style. Same indentation, same comment voice, same naming. Nothing snuck in.
