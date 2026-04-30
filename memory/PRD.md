# Ember — AI companion (real_Genie)

## Original problem statement
Parent asked help fixing their son's GitHub project (https://github.com/tinysecrets/real_Genie.git).
The son is building a personal AI assistant ("AI dolphin"). Goal: make sure the app runs correctly, keep everything the same so the son can mimic/learn, use placeholders for API keys.

## Architecture (as built by the son)
- Frontend: React 19 + CRACO + Tailwind + react-markdown + lucide-react
- Backend: FastAPI + Motor (MongoDB async)
- LLM: Claude Sonnet 4.5 via `emergentintegrations` + Emergent Universal Key
- Memory extractor: Claude Haiku 4.5 (background task)
- Auth: Emergent Google OAuth (session cookie based)
- DB collections: users, user_sessions, user_settings, conversations, messages, memories

## What was done in this session (2026-01)
- Cloned https://github.com/tinysecrets/real_Genie.git into /app
- Preserved existing frontend/.env and backend/.env (protected vars kept as-is)
- Added EMERGENT_LLM_KEY to /app/backend/.env (uses Emergent Universal Key placeholder)
- Installed backend Python deps and frontend yarn deps
- Restarted backend + frontend via supervisor
- Verified: backend `/api/` returns {"message":"Ember is here.","model":"anthropic/claude-sonnet-4-5-20250929"}
- Verified: frontend renders the Login page ("A real one. Not a script.") with Continue-with-Google button

## Notes for the son
- Nothing in his code was changed — files copied 1:1 from GitHub
- Only config added: EMERGENT_LLM_KEY in backend/.env (required for Claude calls)
- Start flow: open app → redirected to /login → Google sign-in → back to chat
- Chat, memory auto-extraction, persona settings, conversation rename/delete all wired

## Backlog (from son's original PRD)
- P1 Token-by-token streaming, export conversation, search
- P2 Voice I/O, custom persona, multi-user, share links, pagination

