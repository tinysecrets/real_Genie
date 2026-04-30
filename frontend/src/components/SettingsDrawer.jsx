import { useState } from "react";
import { X, Settings, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";

export default function SettingsDrawer({ open, onClose, persona, defaultPersona, onSaved }) {
  const [value, setValue] = useState(persona || "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put("/settings/persona", { persona: value });
      onSaved(data.persona);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const resetDefault = () => setValue(defaultPersona || "");

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div
        data-testid="settings-drawer"
        className="relative bg-[#141417] border border-[#3A3220] rounded-2xl shadow-[0_0_60px_rgba(212,175,55,0.18)] max-w-lg w-full p-6 md:p-8"
      >
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-[#F5E9C8]">
            <Settings size={18} className="text-[#D4AF37]" />
            <h2 className="font-heading text-2xl">Shape Ember</h2>
          </div>
          <button onClick={onClose} className="text-[#9A8868] hover:text-[#F0CB58]" aria-label="Close" data-testid="close-settings">
            <X size={18} />
          </button>
        </div>
        <p className="text-sm text-[#9A8868] font-body mb-5 leading-relaxed">
          Tell Ember how to be with you. Tone, style, what to call you, what to avoid.
          <br />
          The honesty rules are non-negotiable — they apply on top of whatever you write here.
        </p>

        <textarea
          data-testid="persona-textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          rows={6}
          maxLength={1000}
          placeholder={defaultPersona}
          className="w-full bg-[#0B0B0E] border border-[#2A2420] rounded-xl px-4 py-3 font-body text-[15px] text-[#F5E9C8] placeholder:text-[#6B5F45] focus:outline-none focus:border-[#D4AF37] focus:ring-2 focus:ring-[#D4AF37]/20 resize-none"
        />
        <div className="flex items-center justify-between mt-1">
          <button
            onClick={resetDefault}
            className="text-xs text-[#9A8868] hover:text-[#F0CB58] font-body flex items-center gap-1"
            data-testid="reset-persona"
          >
            <RotateCcw size={12} /> reset to default
          </button>
          <span className="text-xs text-[#6B5F45] font-body">{value.length}/1000</span>
        </div>

        <div className="flex gap-2 mt-6 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-body text-[#9A8868] hover:text-[#F5E9C8]"
          >
            Cancel
          </button>
          <button
            data-testid="save-persona"
            onClick={save}
            disabled={saving}
            className="px-5 py-2 rounded-full bg-gradient-to-b from-[#D4AF37] to-[#A88A28] text-[#0B0B0E] hover:from-[#F0CB58] hover:to-[#D4AF37] transition-colors text-sm font-body font-medium disabled:opacity-50 shadow-[0_0_20px_rgba(212,175,55,0.35)]"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
