.PHONY: setup install backend frontend test build run

# One-time setup: create venv, install backend + frontend deps.
setup: install

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd frontend && npm install

# Run the backend (dev, auto-reload) on :8000.
backend:
	.venv/bin/uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload

# Run the frontend dev server.
frontend:
	cd frontend && npm start

# Unit tests (no live Mongo/Ollama required).
test:
	.venv/bin/pytest

# Production frontend build.
build:
	cd frontend && npm run build