# Ember — Frontend

React 19 single-page app for the Ember AI companion: a warm, editorial 3-column chat layout with a persistent memory panel and an N-gram persona editor.

## Tech

- React 19 + Create React App (via CRACO)
- Tailwind CSS + shadcn/ui components
- react-markdown + remark-gfm for AI responses
- React Router, Axios, lucide-react

## Scripts

```bash
yarn start      # dev server (port 3000)
yarn build      # production build to /build
yarn test       # test runner
```

## Environment

Create `.env.local` in `frontend/`:

```
REACT_APP_BACKEND_URL=http://localhost:8001
```

All API calls go to `${REACT_APP_BACKEND_URL}/api`.

PostHog analytics are **off by default**. To enable basic product analytics at
build time, add `REACT_APP_POSTHOG_ENABLED=true` (optionally
`REACT_APP_POSTHOG_KEY` / `REACT_APP_POSTHOG_HOST`). Session recording is never
enabled, and nothing is ever sent from `localhost`.

## Structure

```
src/
  pages/          # Login, AuthCallback, Chat
  components/     # SettingsDrawer + shadcn/ui primitives
  lib/            # api.js (axios client), utils.js
  hooks/          # use-toast
  App.js          # routing + auth guard
public/           # index.html, manifest, service worker
plugins/          # optional webpack health-check plugin (enable via ENABLE_HEALTH_CHECK=true)
```

See the repository root `README.md` for full setup instructions.