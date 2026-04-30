"""
Offline speech-to-text using Vosk.
Browser sends audio (webm/opus from MediaRecorder), we shell out to ffmpeg
to convert to 16 kHz mono PCM, then Vosk decodes it locally.
No cloud, no API key.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

import vosk

logger = logging.getLogger(__name__)

VOSK_MODEL_PATH = os.environ.get(
    "VOSK_MODEL_PATH",
    str(Path(__file__).parent / "models" / "vosk-en-small"),
)

_model: Optional[vosk.Model] = None


def get_model() -> Optional[vosk.Model]:
    global _model
    if _model is not None:
        return _model
    if not Path(VOSK_MODEL_PATH).exists():
        logger.warning(f"Vosk model not found at {VOSK_MODEL_PATH} — voice transcription disabled")
        return None
    try:
        vosk.SetLogLevel(-1)
        _model = vosk.Model(VOSK_MODEL_PATH)
        logger.info(f"Vosk model loaded from {VOSK_MODEL_PATH}")
        return _model
    except Exception as e:
        logger.error(f"Failed to load Vosk model: {e}")
        return None


async def transcribe_bytes(audio_bytes: bytes) -> str:
    """Convert any browser audio blob → 16kHz mono PCM → Vosk transcript."""
    model = get_model()
    if model is None:
        return ""

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-loglevel", "error",
        "-i", "pipe:0",
        "-ar", "16000",
        "-ac", "1",
        "-f", "s16le",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    pcm, err = await proc.communicate(audio_bytes)
    if proc.returncode != 0:
        logger.warning(f"ffmpeg failed: {err.decode(errors='ignore')[:200]}")
        return ""

    rec = vosk.KaldiRecognizer(model, 16000)
    rec.SetWords(False)
    # feed in chunks so very long audio doesn't choke the recognizer
    chunk = 4000 * 2  # 4000 samples * 2 bytes
    for i in range(0, len(pcm), chunk):
        rec.AcceptWaveform(pcm[i:i + chunk])
    final = json.loads(rec.FinalResult() or "{}")
    return (final.get("text") or "").strip()
