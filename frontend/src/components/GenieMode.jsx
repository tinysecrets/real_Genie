import { useEffect, useRef, useState, useCallback } from "react";
import { X, Mic, MicOff, Monitor, MonitorOff, Volume2, VolumeX, Sparkles, Camera } from "lucide-react";
import { api } from "@/lib/api";

/**
 * Genie Mode — hands-free, eyes-shared conversation.
 *  - Voice in: Web Speech API (free, browser-native)
 *  - Voice out: SpeechSynthesis (free, browser-native)
 *  - Screen share: getDisplayMedia + canvas snapshot → /api/vision
 */
export default function GenieMode({ open, onClose, onAssistantMessage, conversationId, setConversationId }) {
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [interim, setInterim] = useState("");
  const [transcript, setTranscript] = useState([]);   // {role, text}
  const [voiceOn, setVoiceOn] = useState(true);
  const [screenOn, setScreenOn] = useState(false);
  const [error, setError] = useState("");

  const recogRef = useRef(null);
  const streamRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const restartRef = useRef(true);   // auto-restart STT after each utterance

  // ---------- Speech Recognition (voice IN) ----------
  const setupRecognition = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setError("Voice input isn't supported in this browser. Try Chrome.");
      return null;
    }
    const r = new SR();
    r.lang = "en-US";
    r.continuous = false;        // one utterance at a time, then we restart
    r.interimResults = true;

    r.onresult = (e) => {
      let finalText = "";
      let interimText = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalText += t;
        else interimText += t;
      }
      setInterim(interimText);
      if (finalText.trim()) {
        setInterim("");
        sendUtterance(finalText.trim());
      }
    };

    r.onerror = (e) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        setError("Microphone permission denied.");
        setListening(false);
        restartRef.current = false;
      }
    };

    r.onend = () => {
      // auto-restart while genie is open and voice is on
      if (restartRef.current && voiceOn) {
        try { r.start(); } catch {}
      } else {
        setListening(false);
      }
    };

    return r;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voiceOn]);

  // ---------- Speech Synthesis (voice OUT) ----------
  const speak = (text) => {
    if (!voiceOn || !text) return;
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.02;
    u.pitch = 1.0;
    u.volume = 1.0;
    // pick a warmer voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => /samantha|google.*us|natural/i.test(v.name)) || voices[0];
    if (preferred) u.voice = preferred;
    u.onstart = () => setSpeaking(true);
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(u);
  };

  // ---------- Screen capture ----------
  const startScreen = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: 5 }, audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setScreenOn(true);
      stream.getVideoTracks()[0].onended = () => stopScreen();
    } catch {
      setError("Screen share canceled or denied.");
    }
  };

  const stopScreen = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setScreenOn(false);
  };

  const captureFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth) return null;
    const w = Math.min(1280, video.videoWidth);
    const h = Math.round((video.videoHeight / video.videoWidth) * w);
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, w, h);
    return canvas.toDataURL("image/jpeg", 0.7);
  };

  // ---------- Send a spoken/typed utterance ----------
  const sendUtterance = async (text) => {
    setTranscript(t => [...t, { role: "user", text }]);
    setThinking(true);

    try {
      let reply;
      if (screenOn) {
        const image = captureFrame();
        if (image) {
          const { data } = await api.post("/vision", {
            conversation_id: conversationId,
            message: text,
            image,
          });
          if (!conversationId) setConversationId(data.conversation_id);
          reply = data.assistant_message.content;
          onAssistantMessage?.(data);
        }
      }
      if (!reply) {
        const { data } = await api.post("/chat", {
          conversation_id: conversationId,
          message: text,
        });
        if (!conversationId) setConversationId(data.conversation_id);
        reply = data.assistant_message.content;
        onAssistantMessage?.(data);
      }
      setTranscript(t => [...t, { role: "assistant", text: reply }]);
      speak(reply);
    } catch (e) {
      const msg = "Something went wrong. Try again?";
      setTranscript(t => [...t, { role: "assistant", text: msg }]);
      speak(msg);
    } finally {
      setThinking(false);
    }
  };

  // ---------- Lifecycle ----------
  useEffect(() => {
    if (!open) return;
    restartRef.current = true;
    if (voiceOn) {
      const r = setupRecognition();
      if (r) {
        recogRef.current = r;
        try { r.start(); setListening(true); } catch {}
      }
    }
    // load voices early (Chrome quirk)
    if ("speechSynthesis" in window) window.speechSynthesis.getVoices();

    return () => {
      restartRef.current = false;
      try { recogRef.current?.stop(); } catch {}
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
      stopScreen();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // toggle voice on/off mid-session
  useEffect(() => {
    if (!open) return;
    if (voiceOn) {
      if (!recogRef.current) {
        const r = setupRecognition();
        if (r) recogRef.current = r;
      }
      restartRef.current = true;
      try { recogRef.current?.start(); setListening(true); } catch {}
    } else {
      restartRef.current = false;
      try { recogRef.current?.stop(); } catch {}
      window.speechSynthesis?.cancel();
      setListening(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voiceOn]);

  if (!open) return null;

  return (
    <div data-testid="genie-mode" className="fixed inset-0 z-50 bg-[#050507]/95 backdrop-blur-md flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#2A2420]">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-[#D4AF37]" />
          <span className="font-body text-xs uppercase tracking-[0.4em] gold-shimmer font-semibold">Genie Mode</span>
        </div>
        <button
          data-testid="close-genie"
          onClick={onClose}
          className="text-[#9A8868] hover:text-[#F0CB58] p-2"
          aria-label="Close Genie Mode"
        >
          <X size={20} />
        </button>
      </div>

      {/* Main stage */}
      <div className="flex-1 grid md:grid-cols-2 overflow-hidden">
        {/* Left — orb + status */}
        <div className="flex flex-col items-center justify-center p-8 relative">
          <div className="relative flex items-center justify-center">
            <div
              data-testid="genie-orb"
              className={`w-48 h-48 md:w-64 md:h-64 rounded-full bg-gradient-to-br from-[#F0CB58] via-[#D4AF37] to-[#5A4A28] genie-pulse flex items-center justify-center ${listening ? "listen-pulse" : ""}`}
            >
              <Sparkles size={56} className="text-[#0B0B0E]" />
            </div>
          </div>

          <div className="mt-10 text-center">
            <div className="font-heading text-3xl text-[#F5E9C8]">
              {speaking ? "Ember speaking…" : thinking ? "Ember thinking…" : listening ? "Listening…" : "Paused"}
            </div>
            {interim && (
              <div data-testid="interim-text" className="mt-3 font-ai text-lg text-[#C5B689] italic max-w-md mx-auto">
                "{interim}"
              </div>
            )}
            {error && (
              <div data-testid="genie-error" className="mt-4 text-sm text-[#E5715E] font-body">{error}</div>
            )}
          </div>

          {/* Controls */}
          <div className="mt-10 flex items-center gap-3">
            <button
              data-testid="toggle-voice"
              onClick={() => setVoiceOn(v => !v)}
              className={`w-12 h-12 rounded-full border flex items-center justify-center transition-all ${
                voiceOn
                  ? "bg-[#D4AF37] border-[#D4AF37] text-[#0B0B0E] shadow-[0_0_20px_rgba(212,175,55,0.5)]"
                  : "bg-transparent border-[#3A3220] text-[#9A8868] hover:border-[#D4AF37]"
              }`}
              aria-label={voiceOn ? "Mute mic & speech" : "Unmute"}
            >
              {voiceOn ? <Mic size={18} /> : <MicOff size={18} />}
            </button>
            <button
              data-testid="toggle-mute-output"
              onClick={() => window.speechSynthesis?.cancel()}
              className="w-12 h-12 rounded-full border border-[#3A3220] flex items-center justify-center text-[#9A8868] hover:text-[#F0CB58] hover:border-[#D4AF37]"
              aria-label="Stop speaking"
            >
              {speaking ? <Volume2 size={18} className="text-[#F0CB58]" /> : <VolumeX size={18} />}
            </button>
            <button
              data-testid="toggle-screen"
              onClick={() => screenOn ? stopScreen() : startScreen()}
              className={`w-12 h-12 rounded-full border flex items-center justify-center transition-all ${
                screenOn
                  ? "bg-[#D4AF37] border-[#D4AF37] text-[#0B0B0E] shadow-[0_0_20px_rgba(212,175,55,0.5)]"
                  : "bg-transparent border-[#3A3220] text-[#9A8868] hover:border-[#D4AF37]"
              }`}
              aria-label={screenOn ? "Stop sharing screen" : "Share screen"}
            >
              {screenOn ? <Monitor size={18} /> : <MonitorOff size={18} />}
            </button>
          </div>
          <p className="mt-6 text-[11px] text-[#6B5F45] font-body uppercase tracking-[0.2em] text-center">
            Speak naturally · Tap mic to pause · Tap screen to share
          </p>
        </div>

        {/* Right — transcript + screen preview */}
        <div className="border-l border-[#2A2420] flex flex-col overflow-hidden">
          {screenOn && (
            <div className="relative bg-[#0B0B0E] border-b border-[#2A2420] p-3">
              <video
                ref={videoRef}
                muted
                playsInline
                className="w-full max-h-[260px] object-contain rounded-md border border-[#2A2420]"
              />
              <div className="absolute top-5 left-5 flex items-center gap-1.5 text-[10px] uppercase tracking-[0.2em] text-[#D4AF37] bg-[#0B0B0E]/80 px-2 py-1 rounded">
                <Camera size={10} /> live
              </div>
            </div>
          )}
          <canvas ref={canvasRef} className="hidden" />

          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            <div className="text-xs uppercase tracking-[0.3em] text-[#6B5F45] font-body mb-2">
              Transcript
            </div>
            {transcript.length === 0 && (
              <div className="text-[#6B5F45] font-ai italic text-sm">
                Say anything to begin. Ember is listening.
              </div>
            )}
            {transcript.map((m, i) => (
              <div key={i} data-testid={m.role === "user" ? "live-user-msg" : "live-ai-msg"}>
                <div className={`text-[10px] uppercase tracking-[0.2em] mb-1 ${m.role === "user" ? "text-[#9A8868]" : "text-[#D4AF37]"}`}>
                  {m.role === "user" ? "You" : "Ember"}
                </div>
                <div className={`font-ai text-[16px] leading-relaxed ${m.role === "user" ? "text-[#C5B689]" : "text-[#F5E9C8]"}`}>
                  {m.text}
                </div>
              </div>
            ))}
            {thinking && (
              <div className="flex items-center gap-2 text-[#D4AF37] mt-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#D4AF37] animate-pulse" />
                <span className="w-1.5 h-1.5 rounded-full bg-[#D4AF37] animate-pulse [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-[#D4AF37] animate-pulse [animation-delay:300ms]" />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
