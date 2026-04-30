import { useEffect, useRef, useState } from "react";
import { Globe, Play, Square, Send, Sparkles, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";

/**
 * AgentPanel — the "hands" of the Genie.
 * Lives inside Genie Mode. Drives a backend Playwright browser via /api/agent/*.
 * Shows live screenshots and the running action trace.
 */
export default function AgentPanel({ active, onAssistantSay }) {
  const [running, setRunning] = useState(false);
  const [url, setUrl] = useState("");
  const [shot, setShot] = useState("");
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [trace, setTrace] = useState([]);
  const pollRef = useRef(null);

  // ---------- screenshot polling while active ----------
  useEffect(() => {
    if (!active || !running) return;
    let cancel = false;
    const tick = async () => {
      try {
        const { data } = await api.get("/agent/screenshot");
        if (cancel) return;
        setShot(data.image);
        setUrl(data.url);
      } catch {}
      pollRef.current = setTimeout(tick, 1500);
    };
    tick();
    return () => {
      cancel = true;
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [active, running]);

  // ---------- controls ----------
  const start = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/agent/start");
      setRunning(data.running);
      setUrl(data.url || "");
      pushTrace("agent", "browser launched");
    } catch {
      pushTrace("error", "failed to start agent");
    } finally { setBusy(false); }
  };

  const stop = async () => {
    setBusy(true);
    try {
      await api.post("/agent/stop");
      setRunning(false);
      setShot("");
      pushTrace("agent", "browser stopped");
    } finally { setBusy(false); }
  };

  const goto = async (u) => {
    if (!u) return;
    setBusy(true);
    try {
      const { data } = await api.post("/agent/goto", { url: u });
      setUrl(data.url || u);
      pushTrace("goto", data.url || u);
    } catch (e) {
      pushTrace("error", e?.response?.data?.detail || "navigation failed");
    } finally { setBusy(false); }
  };

  const runGoal = async () => {
    const g = goal.trim();
    if (!g) return;
    setGoal("");
    setBusy(true);
    pushTrace("goal", g);
    try {
      const { data } = await api.post("/agent/run", { goal: g, max_steps: 8 });
      (data.steps || []).forEach((s) => {
        const a = s.action || {};
        pushTrace(a.type || "step", JSON.stringify(a).slice(0, 140));
      });
      pushTrace("done", `final url: ${data.final_url}`);
      onAssistantSay?.(`Done. Ended at ${data.final_url}.`);
    } catch (e) {
      pushTrace("error", e?.response?.data?.detail || "run failed");
    } finally { setBusy(false); }
  };

  const pushTrace = (kind, text) => {
    setTrace((t) => [...t.slice(-60), { kind, text, ts: Date.now() }]);
  };

  if (!active) return null;

  return (
    <div data-testid="agent-panel" className="flex flex-col h-full">
      {/* URL bar + controls */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[#2A2420] bg-[#0F0F12]">
        <Globe size={14} className="text-[#D4AF37]" />
        <input
          data-testid="agent-url-input"
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") goto(url); }}
          placeholder="https://..."
          className="flex-1 bg-transparent border-none focus:outline-none text-sm font-mono text-[#F5E9C8] placeholder:text-[#6B5F45]"
        />
        <button
          onClick={() => goto(url)}
          disabled={busy || !running}
          data-testid="agent-go-button"
          className="text-[10px] uppercase tracking-[0.15em] px-2 py-1 rounded text-[#D4AF37] hover:text-[#F0CB58] hover:bg-[#1F1A12] disabled:opacity-30"
        >
          go
        </button>
        {!running ? (
          <button
            data-testid="agent-start-button"
            onClick={start}
            disabled={busy}
            className="ml-1 inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gradient-to-b from-[#D4AF37] to-[#A88A28] text-[#0B0B0E] text-[10px] uppercase tracking-[0.15em] font-medium hover:from-[#F0CB58] disabled:opacity-50"
          >
            <Play size={10} /> launch
          </button>
        ) : (
          <button
            data-testid="agent-stop-button"
            onClick={stop}
            disabled={busy}
            className="ml-1 inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-[#3A3220] text-[#F5E9C8] hover:border-[#D4AF37] text-[10px] uppercase tracking-[0.15em] disabled:opacity-50"
          >
            <Square size={10} /> stop
          </button>
        )}
      </div>

      {/* Live screenshot */}
      <div className="flex-1 bg-[#050507] overflow-hidden flex items-center justify-center p-3">
        {!running ? (
          <div className="text-center text-[#6B5F45] font-body text-sm">
            Click <span className="text-[#D4AF37] font-semibold">launch</span> to start the browser.
          </div>
        ) : shot ? (
          <img
            data-testid="agent-screenshot"
            src={`data:image/jpeg;base64,${shot}`}
            alt="live page"
            className="max-w-full max-h-full rounded-md border border-[#2A2420] shadow-[0_0_30px_rgba(212,175,55,0.12)]"
          />
        ) : (
          <div className="flex items-center gap-2 text-[#9A8868]">
            <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse" />
            <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse [animation-delay:150ms]" />
            <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse [animation-delay:300ms]" />
            <span className="ml-2 text-xs font-body">loading…</span>
          </div>
        )}
      </div>

      {/* Goal input */}
      <div className="border-t border-[#2A2420] bg-[#0F0F12] px-4 py-3">
        <div className="flex items-end gap-2">
          <Sparkles size={14} className="text-[#D4AF37] mb-2.5" />
          <textarea
            data-testid="agent-goal-input"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); runGoal(); } }}
            placeholder="Tell Ember what to do — 'find latest news on Ollama, summarize top 3'"
            rows={1}
            className="flex-1 bg-transparent border-none focus:outline-none resize-none font-body text-[14px] text-[#F5E9C8] placeholder:text-[#6B5F45] py-2"
          />
          <button
            onClick={runGoal}
            disabled={busy || !running || !goal.trim()}
            data-testid="agent-run-button"
            className="w-9 h-9 rounded-full bg-gradient-to-b from-[#D4AF37] to-[#A88A28] text-[#0B0B0E] flex items-center justify-center hover:from-[#F0CB58] disabled:opacity-30"
            aria-label="Run goal"
          >
            <Send size={14} />
          </button>
        </div>
      </div>

      {/* Trace */}
      <div className="border-t border-[#2A2420] max-h-[180px] overflow-y-auto px-4 py-3 bg-[#0B0B0E]">
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#6B5F45] font-body mb-2">Trace</div>
        {trace.length === 0 && (
          <div className="text-xs text-[#6B5F45] italic font-body">no actions yet</div>
        )}
        {trace.map((t, i) => (
          <div key={i} data-testid="agent-trace-line" className="text-xs font-mono text-[#C5B689] flex gap-2 py-0.5">
            <span className="text-[#D4AF37] uppercase shrink-0 min-w-[44px]">{t.kind}</span>
            <ArrowRight size={10} className="mt-1 text-[#6B5F45] shrink-0" />
            <span className="break-all">{t.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
