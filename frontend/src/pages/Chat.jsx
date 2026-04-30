import { useEffect, useRef, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Plus, Send, Trash2, Pencil, Check, X, Menu, Brain,
  Copy, CopyCheck, MessageSquare, Sparkles, Settings, LogOut,
  Mic, MicOff, Volume2, Wand2,
} from "lucide-react";
import { api } from "@/lib/api";
import { VoiceCapture } from "@/lib/voice";
import SettingsDrawer from "@/components/SettingsDrawer";
import GenieMode from "@/components/GenieMode";

function AiAvatar() {
  return (
    <div
      data-testid="ai-avatar"
      className="w-9 h-9 rounded-full overflow-hidden shrink-0 border border-[#3A3220] bg-gradient-to-br from-[#D4AF37] via-[#A88A28] to-[#5A4A28] flex items-center justify-center shadow-[0_0_12px_rgba(212,175,55,0.35)]"
    >
      <Sparkles size={16} className="text-[#0B0B0E]" />
    </div>
  );
}

function UserMessage({ content }) {
  return (
    <div data-testid="user-message" className="flex justify-end w-full">
      <div className="bg-[#1F1A12] border border-[#2A2420] rounded-2xl rounded-tr-sm px-5 py-3 max-w-[80%] text-[#F5E9C8] font-body text-[15px] leading-relaxed whitespace-pre-wrap">
        {content}
      </div>
    </div>
  );
}

const mdComponents = {
  code({ inline, children, ...props }) {
    return inline ? (
      <code className="bg-[#1F1A12] text-[#F0CB58] px-1.5 py-0.5 rounded font-mono text-[14px]" {...props}>
        {children}
      </code>
    ) : (
      <pre className="bg-[#050507] border border-[#2A2420] text-[#F5E9C8] p-4 rounded-xl overflow-x-auto my-3 font-mono text-[13px] leading-relaxed">
        <code {...props}>{children}</code>
      </pre>
    );
  },
  a: ({ ...props }) => (
    <a {...props} className="text-[#F0CB58] underline underline-offset-2 hover:text-[#D4AF37]" target="_blank" rel="noreferrer" />
  ),
  ul: ({ ...props }) => <ul {...props} className="list-disc pl-6 my-2 space-y-1" />,
  ol: ({ ...props }) => <ol {...props} className="list-decimal pl-6 my-2 space-y-1" />,
  p: ({ ...props }) => <p {...props} className="my-2" />,
  h1: ({ ...props }) => <h1 {...props} className="font-heading text-2xl mt-4 mb-2 text-[#F5E9C8]" />,
  h2: ({ ...props }) => <h2 {...props} className="font-heading text-xl mt-4 mb-2 text-[#F5E9C8]" />,
  h3: ({ ...props }) => <h3 {...props} className="font-heading text-lg mt-3 mb-2 text-[#F5E9C8]" />,
  blockquote: ({ ...props }) => (
    <blockquote {...props} className="border-l-2 border-[#D4AF37] pl-4 italic text-[#C5B689] my-3" />
  ),
};

function AiMessage({ content, thinking, streaming, onSpeak }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(content || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (thinking) {
    return (
      <div data-testid="ai-message" className="flex justify-start w-full gap-3">
        <AiAvatar />
        <div className="flex items-center gap-2 py-3">
          <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse" />
          <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse [animation-delay:150ms]" />
          <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse [animation-delay:300ms]" />
        </div>
      </div>
    );
  }

  return (
    <div data-testid="ai-message" className="flex justify-start w-full group gap-3">
      <AiAvatar />
      <div className="flex-1 min-w-0">
        <div className="font-ai text-[18px] leading-[1.7] text-[#F5E9C8] max-w-[85%] prose-ember">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {content}
          </ReactMarkdown>
          {streaming && (
            <span
              data-testid="streaming-cursor"
              className="inline-block w-[2px] h-[1em] bg-[#D4AF37] align-baseline ml-0.5 animate-pulse"
            />
          )}
        </div>
        {!streaming && (
          <div className="mt-2 flex gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              data-testid="copy-message-button"
              onClick={copy}
              className="text-xs text-[#9A8868] hover:text-[#F0CB58] flex items-center gap-1.5 font-body"
            >
              {copied ? <CopyCheck size={14} /> : <Copy size={14} />}
              {copied ? "copied" : "copy"}
            </button>
            <button
              data-testid="speak-message-button"
              onClick={() => onSpeak?.(content)}
              className="text-xs text-[#9A8868] hover:text-[#F0CB58] flex items-center gap-1.5 font-body"
              aria-label="Speak this message"
            >
              <Volume2 size={14} /> speak
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyState({ name, onQuickStart, onOpenGenie }) {
  const prompts = [
    "What have I told you about myself so far?",
    "Be honest — is this idea any good?",
    "Help me think through something hard.",
    "Just talk to me for a minute.",
  ];
  const greet = name ? `Hi ${name}.` : "Hi.";
  return (
    <div data-testid="empty-state" className="flex-1 flex flex-col items-center justify-center text-center px-6 py-12">
      <div className="mb-6 inline-flex items-center gap-2 font-body text-xs uppercase tracking-[0.4em]">
        <Sparkles size={14} className="text-[#D4AF37]" />
        <span className="gold-shimmer font-semibold">Ember</span>
      </div>
      <h1 className="font-heading font-light text-4xl md:text-5xl text-[#F5E9C8] leading-tight max-w-2xl">
        {greet} I'm not a script.
      </h1>
      <p className="font-ai text-[19px] text-[#C5B689] mt-6 max-w-xl leading-relaxed">
        I'll remember you, push back when you're wrong, and say "I don't know" when I don't.
        <br />Start anywhere — type, talk, or open Genie Mode.
      </p>

      <button
        data-testid="open-genie-cta"
        onClick={onOpenGenie}
        className="mt-8 inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-b from-[#D4AF37] to-[#A88A28] text-[#0B0B0E] hover:from-[#F0CB58] hover:to-[#D4AF37] font-body text-sm font-medium shadow-[0_0_28px_rgba(212,175,55,0.4)]"
      >
        <Sparkles size={15} /> Enter Genie Mode
      </button>

      <div className="mt-10 grid sm:grid-cols-2 gap-3 w-full max-w-xl">
        {prompts.map((p) => (
          <button
            key={p}
            data-testid="quick-start-prompt"
            onClick={() => onQuickStart(p)}
            className="text-left text-[14px] font-body text-[#F5E9C8] bg-[#141417] border border-[#2A2420] rounded-xl px-4 py-3 hover:border-[#D4AF37] hover:shadow-[0_0_18px_rgba(212,175,55,0.18)] transition-all"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

function Sidebar({ user, conversations, currentId, onSelect, onNew, onDelete, onRename, onLogout, onOpenSettings, mobileOpen, onCloseMobile }) {
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState("");

  const startEdit = (c) => { setEditingId(c.id); setEditValue(c.title); };
  const commitEdit = () => {
    if (editingId && editValue.trim()) onRename(editingId, editValue.trim());
    setEditingId(null);
  };

  return (
    <aside
      data-testid="sidebar"
      className={`${mobileOpen ? "translate-x-0" : "-translate-x-full"} md:translate-x-0 fixed md:static z-40 top-0 left-0 w-72 md:w-64 border-r border-[#2A2420] bg-[#141417] h-screen flex flex-col transition-transform duration-300`}
    >
      <div className="p-6 flex items-center justify-between">
        <div className="font-heading text-2xl gold-shimmer tracking-tight font-medium">Ember</div>
        <button className="md:hidden text-[#9A8868]" onClick={onCloseMobile} data-testid="close-sidebar" aria-label="Close sidebar">
          <X size={18} />
        </button>
      </div>

      <div className="px-4">
        <button
          data-testid="new-conversation-button"
          onClick={() => { onNew(); onCloseMobile(); }}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg bg-gradient-to-b from-[#D4AF37] to-[#A88A28] text-[#0B0B0E] hover:from-[#F0CB58] hover:to-[#D4AF37] transition-colors font-body text-sm font-medium shadow-[0_0_18px_rgba(212,175,55,0.3)]"
        >
          <Plus size={16} /> New conversation
        </button>
      </div>

      <h2 className="mt-8 mb-3 px-6 text-xs font-semibold uppercase tracking-[0.3em] text-[#6B5F45] font-body">
        History
      </h2>

      <div className="flex-1 overflow-y-auto px-3 pb-6">
        {conversations.length === 0 && (
          <div className="px-3 py-2 text-xs text-[#6B5F45] font-body italic">nothing here yet</div>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            data-testid="sidebar-history-item"
            className={`group relative rounded-lg mb-1 ${currentId === c.id ? "bg-[#1F1A12] border border-[#3A3220]" : "hover:bg-[#1C1C20]"}`}
          >
            {editingId === c.id ? (
              <div className="flex items-center gap-1 p-2">
                <input
                  data-testid="rename-input"
                  className="flex-1 bg-[#0B0B0E] border border-[#2A2420] rounded-md px-2 py-1 text-sm font-body text-[#F5E9C8] focus:outline-none focus:border-[#D4AF37]"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") commitEdit(); if (e.key === "Escape") setEditingId(null); }}
                  autoFocus
                />
                <button onClick={commitEdit} data-testid="confirm-rename" className="text-[#9A8868] hover:text-[#F0CB58] p-1"><Check size={14} /></button>
                <button onClick={() => setEditingId(null)} className="text-[#9A8868] hover:text-[#F5E9C8] p-1"><X size={14} /></button>
              </div>
            ) : (
              <button
                onClick={() => { onSelect(c.id); onCloseMobile(); }}
                className="w-full text-left px-3 py-2 pr-14 rounded-lg text-sm text-[#F5E9C8] font-body truncate flex items-center gap-2"
                title={c.title}
              >
                <MessageSquare size={13} className="text-[#9A8868] shrink-0" />
                <span className="truncate">{c.title}</span>
              </button>
            )}
            {editingId !== c.id && (
              <div className="absolute right-1 top-1/2 -translate-y-1/2 flex opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={(e) => { e.stopPropagation(); startEdit(c); }} className="p-1.5 text-[#9A8868] hover:text-[#F0CB58]" data-testid="rename-conversation" aria-label="Rename"><Pencil size={12} /></button>
                <button onClick={(e) => { e.stopPropagation(); onDelete(c.id); }} className="p-1.5 text-[#9A8868] hover:text-[#F0CB58]" data-testid="delete-conversation" aria-label="Delete"><Trash2 size={12} /></button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="border-t border-[#2A2420] p-3">
        <div className="flex items-center gap-3 px-2 py-2">
          {user?.picture ? (
            <img src={user.picture} alt="" className="w-8 h-8 rounded-full border border-[#3A3220]" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#D4AF37] to-[#5A4A28] text-[#0B0B0E] flex items-center justify-center font-body text-sm font-semibold">
              {(user?.name || "?").charAt(0).toUpperCase()}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="text-sm font-body text-[#F5E9C8] truncate" data-testid="user-name">{user?.name || "You"}</div>
            <div className="text-[11px] text-[#6B5F45] truncate">{user?.email || ""}</div>
          </div>
        </div>
        <div className="flex gap-1 mt-1">
          <button
            onClick={onOpenSettings}
            data-testid="open-settings"
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-[12px] text-[#F5E9C8] hover:bg-[#1F1A12] font-body"
          >
            <Settings size={14} /> Persona
          </button>
          <button
            onClick={onLogout}
            data-testid="logout-button"
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-[12px] text-[#F5E9C8] hover:bg-[#1F1A12] font-body"
          >
            <LogOut size={14} /> Logout
          </button>
        </div>
      </div>
    </aside>
  );
}

function MemoryPanel({ memories, onAdd, onDelete, onEdit, mobileOpen, onCloseMobile }) {
  const [newMem, setNewMem] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState("");

  const submit = () => {
    if (!newMem.trim()) return;
    onAdd(newMem.trim());
    setNewMem("");
  };
  const commitEdit = () => {
    if (editingId && editValue.trim()) onEdit(editingId, editValue.trim());
    setEditingId(null);
  };

  return (
    <aside
      data-testid="memory-panel"
      className={`${mobileOpen ? "translate-x-0" : "translate-x-full"} md:translate-x-0 fixed md:static z-40 top-0 right-0 w-80 md:w-72 border-l border-[#2A2420] bg-[#141417] h-screen flex flex-col transition-transform duration-300`}
    >
      <div className="p-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-[#D4AF37]" />
          <h3 className="font-heading text-lg text-[#F5E9C8]">Memory</h3>
        </div>
        <button className="md:hidden text-[#9A8868]" onClick={onCloseMobile} aria-label="Close memory" data-testid="close-memory">
          <X size={18} />
        </button>
      </div>

      <p className="px-6 text-xs text-[#9A8868] font-body leading-relaxed -mt-2 mb-4">
        What Ember remembers about you. Edit or delete freely — this is yours.
      </p>

      <div className="px-6 pb-4">
        <div className="flex gap-2">
          <input
            data-testid="memory-input"
            value={newMem}
            onChange={(e) => setNewMem(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
            placeholder="Add a fact..."
            className="flex-1 bg-[#0B0B0E] border border-[#2A2420] rounded-lg px-3 py-2 text-sm font-body text-[#F5E9C8] focus:outline-none focus:border-[#D4AF37] placeholder:text-[#6B5F45]"
          />
          <button data-testid="add-memory-button" onClick={submit} className="px-3 py-2 rounded-lg bg-gradient-to-b from-[#D4AF37] to-[#A88A28] text-[#0B0B0E] hover:from-[#F0CB58] hover:to-[#D4AF37] transition-colors text-sm font-body">
            <Plus size={14} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {memories.length === 0 && (
          <div className="text-sm text-[#6B5F45] italic font-body">Nothing remembered yet. Start a conversation.</div>
        )}
        {memories.map((m) => (
          <div key={m.id} data-testid="memory-card" className="bg-[#1C1C20] border border-[#2A2420] rounded-xl p-3 mb-2 hover:border-[#3A3220] transition-colors group relative">
            {editingId === m.id ? (
              <div className="flex flex-col gap-2">
                <textarea
                  data-testid="memory-edit-input"
                  className="w-full bg-[#0B0B0E] border border-[#2A2420] rounded-md px-2 py-1 text-sm font-body text-[#F5E9C8] focus:outline-none focus:border-[#D4AF37] resize-none"
                  rows={2}
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                />
                <div className="flex gap-2 justify-end">
                  <button onClick={() => setEditingId(null)} className="text-xs text-[#9A8868] px-2 py-1">Cancel</button>
                  <button onClick={commitEdit} data-testid="confirm-memory-edit" className="text-xs text-[#0B0B0E] bg-[#D4AF37] hover:bg-[#F0CB58] px-2 py-1 rounded font-medium">Save</button>
                </div>
              </div>
            ) : (
              <>
                <div className="text-sm text-[#F5E9C8] font-body leading-relaxed pr-12">{m.content}</div>
                <div className="absolute right-2 top-2 flex opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => { setEditingId(m.id); setEditValue(m.content); }} className="p-1.5 text-[#9A8868] hover:text-[#F0CB58]" data-testid="edit-memory" aria-label="Edit"><Pencil size={12} /></button>
                  <button onClick={() => onDelete(m.id)} className="p-1.5 text-[#9A8868] hover:text-[#F0CB58]" data-testid="delete-memory" aria-label="Delete"><Trash2 size={12} /></button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}

function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");
  const [recording, setRecording] = useState(false);
  const [busyMic, setBusyMic] = useState(false);
  const taRef = useRef(null);
  const voiceRef = useRef(null);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }, [value]);

  const submit = () => {
    const v = value.trim();
    if (!v || disabled) return;
    onSend(v);
    setValue("");
  };

  const toggleMic = async () => {
    if (busyMic) return;
    if (!voiceRef.current) voiceRef.current = new VoiceCapture();
    if (!voiceRef.current.isSupported()) return;

    if (recording) {
      setBusyMic(true);
      try {
        const text = await voiceRef.current.stopAndTranscribe();
        if (text) setValue((v) => (v ? v + " " + text : text));
      } finally {
        setRecording(false);
        setBusyMic(false);
      }
    } else {
      try {
        await voiceRef.current.start();
        setRecording(true);
      } catch {
        setRecording(false);
      }
    }
  };

  const supportsMic = typeof window !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

  return (
    <div className="max-w-3xl mx-auto w-full px-4 md:px-8 pb-6 pt-2">
      <div className="relative flex items-end w-full bg-[#141417] rounded-3xl border border-[#2A2420] focus-within:ring-2 focus-within:ring-[#D4AF37]/25 focus-within:border-[#D4AF37] transition-all p-2 pl-5">
        <textarea
          ref={taRef}
          data-testid="chat-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={1}
          placeholder="Say anything. I'm here."
          className="flex-1 max-h-40 min-h-[44px] bg-transparent border-none focus:outline-none resize-none py-3 font-body text-[15px] text-[#F5E9C8] placeholder:text-[#6B5F45]"
        />
        {supportsMic && (
          <button
            data-testid="mic-button"
            onClick={toggleMic}
            disabled={disabled || busyMic}
            className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 m-1 transition-all ${
              recording
                ? "bg-[#D4AF37] text-[#0B0B0E] listen-pulse"
                : "bg-transparent border border-[#3A3220] text-[#9A8868] hover:text-[#F0CB58] hover:border-[#D4AF37]"
            }`}
            aria-label={recording ? "Stop and transcribe" : "Voice input (Vosk, offline)"}
            title={recording ? "tap to stop & transcribe" : "tap to talk"}
          >
            {recording ? <Mic size={16} /> : <MicOff size={16} />}
          </button>
        )}
        <button
          data-testid="send-button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="w-10 h-10 rounded-full bg-gradient-to-b from-[#D4AF37] to-[#A88A28] text-[#0B0B0E] flex items-center justify-center hover:from-[#F0CB58] hover:to-[#D4AF37] transition-colors shrink-0 m-1 disabled:opacity-30 disabled:cursor-not-allowed shadow-[0_0_18px_rgba(212,175,55,0.35)]"
          aria-label="Send"
        >
          <Send size={16} />
        </button>
      </div>
      <div className="text-[11px] text-[#6B5F45] font-body mt-2 text-center">
        Ember speaks honestly and can still be wrong. Verify anything important.
      </div>
    </div>
  );
}

export default function Chat({ user, onLogout }) {
  const [conversations, setConversations] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [memories, setMemories] = useState([]);
  const [sending, setSending] = useState(false);
  const [streamingId, setStreamingId] = useState(null);
  const [streamingText, setStreamingText] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [genieOpen, setGenieOpen] = useState(false);
  const [genieInitialPane, setGenieInitialPane] = useState("transcript");
  const [persona, setPersona] = useState("");
  const [defaultPersona, setDefaultPersona] = useState("");
  const scrollRef = useRef(null);

  const loadConversations = useCallback(async () => {
    const { data } = await api.get("/conversations");
    setConversations(data);
  }, []);

  const loadMessages = useCallback(async (id) => {
    if (!id) { setMessages([]); return; }
    const { data } = await api.get(`/conversations/${id}/messages`);
    setMessages(data);
  }, []);

  const loadMemories = useCallback(async () => {
    const { data } = await api.get("/memory");
    setMemories(data);
  }, []);

  const loadPersona = useCallback(async () => {
    const { data } = await api.get("/settings/persona");
    setPersona(data.persona);
    setDefaultPersona(data.default);
  }, []);

  useEffect(() => {
    loadConversations();
    loadMemories();
    loadPersona();
  }, [loadConversations, loadMemories, loadPersona]);

  useEffect(() => { loadMessages(currentId); }, [currentId, loadMessages]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending, streamingText]);

  const handleNew = () => { setCurrentId(null); setMessages([]); };

  const handleDelete = async (id) => {
    await api.delete(`/conversations/${id}`);
    if (currentId === id) { setCurrentId(null); setMessages([]); }
    loadConversations();
  };

  const handleRename = async (id, title) => {
    await api.patch(`/conversations/${id}`, { title });
    loadConversations();
  };

  // Stream an existing string into state — feels like real streaming
  const streamReveal = (id, fullText) => {
    return new Promise((resolve) => {
      setStreamingId(id);
      setStreamingText("");
      let i = 0;
      const chunk = Math.max(2, Math.ceil(fullText.length / 80));
      const tick = () => {
        if (i >= fullText.length) {
          setStreamingId(null);
          setStreamingText("");
          resolve();
          return;
        }
        i = Math.min(i + chunk, fullText.length);
        setStreamingText(fullText.slice(0, i));
        setTimeout(tick, 18);
      };
      tick();
    });
  };

  const speak = (text) => {
    if (!("speechSynthesis" in window) || !text) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.02;
    window.speechSynthesis.speak(u);
  };

  const sendMessage = async (text) => {
    if (sending) return;
    setSending(true);
    const optimisticUser = {
      id: `temp-${Date.now()}`,
      conversation_id: currentId || "new",
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, optimisticUser]);

    try {
      const { data } = await api.post("/chat", {
        conversation_id: currentId,
        message: text,
      });
      const newConvId = data.conversation_id;
      if (!currentId) setCurrentId(newConvId);

      setMessages((m) => {
        const without = m.filter((x) => x.id !== optimisticUser.id);
        return [...without, data.user_message];
      });

      await streamReveal(data.assistant_message.id, data.assistant_message.content);
      setMessages((m) => [...m, data.assistant_message]);

      loadConversations();
      setTimeout(loadMemories, 2500);
    } catch (e) {
      console.error(e);
      if (e?.response?.status === 401) {
        onLogout?.();
        return;
      }
      setMessages((m) => [
        ...m,
        {
          id: `err-${Date.now()}`,
          conversation_id: currentId || "new",
          role: "assistant",
          content: "Something went wrong on my end. Try again?",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const addMemory = async (content) => {
    const { data } = await api.post("/memory", { content });
    setMemories((m) => [data, ...m]);
  };
  const deleteMemory = async (id) => {
    await api.delete(`/memory/${id}`);
    setMemories((m) => m.filter((x) => x.id !== id));
  };
  const editMemory = async (id, content) => {
    const { data } = await api.patch(`/memory/${id}`, { content });
    setMemories((m) => m.map((x) => (x.id === id ? data : x)));
  };

  const onGenieAssistant = (data) => {
    if (!currentId) setCurrentId(data.conversation_id);
    setMessages((m) => [...m, data.user_message, data.assistant_message]);
    loadConversations();
    setTimeout(loadMemories, 2500);
  };

  return (
    <div className="App flex h-screen w-screen bg-[#0B0B0E] overflow-hidden font-body text-[#F5E9C8] relative">
      <Sidebar
        user={user}
        conversations={conversations}
        currentId={currentId}
        onSelect={setCurrentId}
        onNew={handleNew}
        onDelete={handleDelete}
        onRename={handleRename}
        onLogout={onLogout}
        onOpenSettings={() => setSettingsOpen(true)}
        mobileOpen={sidebarOpen}
        onCloseMobile={() => setSidebarOpen(false)}
      />

      <main className="flex-1 flex flex-col h-screen relative min-w-0">
        {/* Mobile header */}
        <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-[#2A2420] bg-[#0B0B0E]">
          <button onClick={() => setSidebarOpen(true)} className="text-[#F5E9C8]" data-testid="open-sidebar" aria-label="Open sidebar">
            <Menu size={20} />
          </button>
          <div className="font-heading text-lg gold-shimmer">Ember</div>
          <button onClick={() => setMemoryOpen(true)} className="text-[#F5E9C8]" data-testid="open-memory" aria-label="Open memory">
            <Brain size={20} />
          </button>
        </div>

        {/* Genie quick-launch + Task launcher */}
        <div className="absolute top-4 right-6 z-20 hidden md:flex items-center gap-2">
          <button
            data-testid="open-task-fab"
            onClick={() => { setGenieInitialPane("agent"); setGenieOpen(true); }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-transparent border border-[#3A3220] text-[#F5E9C8] hover:border-[#D4AF37] hover:text-[#F0CB58] font-body text-xs font-medium"
            title="Give Ember a task — it'll do it for you"
          >
            <Wand2 size={13} /> Task
          </button>
          <button
            data-testid="open-genie-fab"
            onClick={() => { setGenieInitialPane("transcript"); setGenieOpen(true); }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-b from-[#D4AF37] to-[#A88A28] text-[#0B0B0E] hover:from-[#F0CB58] hover:to-[#D4AF37] font-body text-xs font-medium shadow-[0_0_22px_rgba(212,175,55,0.4)]"
          >
            <Sparkles size={13} /> Genie Mode
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {messages.length === 0 && !sending ? (
            <EmptyState
              name={user?.name?.split(" ")[0]}
              onQuickStart={sendMessage}
              onOpenGenie={() => setGenieOpen(true)}
            />
          ) : (
            <div className="max-w-3xl mx-auto w-full px-4 md:px-8 py-10 flex flex-col gap-7">
              {messages.map((m) =>
                m.role === "user" ? (
                  <UserMessage key={m.id} content={m.content} />
                ) : (
                  <AiMessage key={m.id} content={m.content} onSpeak={speak} />
                )
              )}
              {sending && !streamingId && <AiMessage thinking />}
              {streamingId && <AiMessage content={streamingText} streaming />}
            </div>
          )}
        </div>

        <ChatInput onSend={sendMessage} disabled={sending} />
      </main>

      <MemoryPanel
        memories={memories}
        onAdd={addMemory}
        onDelete={deleteMemory}
        onEdit={editMemory}
        mobileOpen={memoryOpen}
        onCloseMobile={() => setMemoryOpen(false)}
      />

      {(sidebarOpen || memoryOpen) && (
        <div
          className="md:hidden fixed inset-0 bg-black/40 z-30"
          onClick={() => { setSidebarOpen(false); setMemoryOpen(false); }}
        />
      )}

      <SettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        persona={persona}
        defaultPersona={defaultPersona}
        onSaved={(p) => setPersona(p)}
      />

      <GenieMode
        open={genieOpen}
        onClose={() => setGenieOpen(false)}
        conversationId={currentId}
        setConversationId={setCurrentId}
        onAssistantMessage={onGenieAssistant}
        initialPane={genieInitialPane}
      />
    </div>
  );
}
