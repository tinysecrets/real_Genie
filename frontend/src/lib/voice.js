// Browser MediaRecorder → backend /api/transcribe (Vosk, fully offline).
// Drop-in replacement for the old Web Speech API helper.

import { api } from "@/lib/api";

export class VoiceCapture {
  constructor() {
    this.stream = null;
    this.recorder = null;
    this.chunks = [];
    this.recording = false;
  }

  isSupported() {
    return typeof window !== "undefined"
      && !!navigator.mediaDevices?.getUserMedia
      && typeof MediaRecorder !== "undefined";
  }

  async start() {
    if (this.recording) return;
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";
    this.recorder = new MediaRecorder(this.stream, { mimeType: mime });
    this.chunks = [];
    this.recorder.ondataavailable = (e) => { if (e.data.size > 0) this.chunks.push(e.data); };
    this.recorder.start();
    this.recording = true;
  }

  /** Stop, send to backend, return transcript text. */
  async stopAndTranscribe() {
    if (!this.recording) return "";
    this.recording = false;

    const stopped = new Promise((resolve) => {
      this.recorder.onstop = () => resolve();
    });
    this.recorder.stop();
    await stopped;

    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;

    if (this.chunks.length === 0) return "";
    const blob = new Blob(this.chunks, { type: this.recorder.mimeType });
    const fd = new FormData();
    fd.append("audio", blob, "audio.webm");
    try {
      const { data } = await api.post("/transcribe", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return (data.text || "").trim();
    } catch {
      return "";
    }
  }

  /** Hard-cancel without transcribing. */
  abort() {
    try { this.recorder?.stop(); } catch {}
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.recorder = null;
    this.chunks = [];
    this.recording = false;
  }
}
