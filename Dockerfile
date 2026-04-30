FROM python:3.11-slim

# System deps: Playwright/Chromium + ffmpeg (for Vosk audio conversion)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip gnupg ca-certificates fonts-liberation ffmpeg \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    libcups2 libdbus-1-3 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN python -m playwright install --with-deps chromium

# Vosk speech-to-text model (~68 MB) — pulled once at build time
RUN mkdir -p /app/backend/models && cd /app/backend/models && \
    wget -q https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip && \
    unzip -q vosk-model-small-en-us-0.15.zip && \
    rm vosk-model-small-en-us-0.15.zip && \
    mv vosk-model-small-en-us-0.15 vosk-en-small

COPY . .

CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8080"]
