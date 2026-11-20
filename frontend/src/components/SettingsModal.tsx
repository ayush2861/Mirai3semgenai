import React, { useState, useEffect } from 'react';
import { X, Settings as SettingsIcon, Key, Sliders, CheckCircle2, Shield, Eye, EyeOff } from 'lucide-react';
import { SettingsPayload } from '../types';
import { fetchSettings, saveSettings } from '../api';

interface SettingsModalProps {
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ onClose }) => {
  const [settings, setSettings] = useState<SettingsPayload>({
    model_name: 'gemini-2.0-flash',
    api_key: '',
    temperature: 0.2,
    top_k_chunks: 4,
    response_style: 'enterprise_sre'
  });
  const [showKey, setShowKey] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings()
      .then(data => setSettings(data))
      .catch(err => console.error(err));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveSettings(settings);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (err) {
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-xl bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#262626] bg-[#181818]">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <SettingsIcon size={18} />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">System & AI Settings</h3>
              <p className="text-xs text-[#A3A3A3]">Configure LLM reasoning provider, API keys, and RAG preferences</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#A3A3A3] hover:text-white rounded-lg hover:bg-[#262626] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-5 text-left">
          {savedSuccess && (
            <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-xl flex items-center space-x-2 text-xs text-green-400">
              <CheckCircle2 size={15} />
              <span>Settings updated successfully!</span>
            </div>
          )}

          {/* AI Model */}
          <div>
            <label className="text-xs font-semibold text-[#A3A3A3] uppercase tracking-wider block mb-2">
              Inference Model
            </label>
            <select
              value={settings.model_name}
              onChange={(e) => setSettings({ ...settings, model_name: e.target.value })}
              className="w-full bg-[#181818] border border-[#262626] rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
            >
              <option value="gemini-2.0-flash">Google Gemini 2.0 Flash (Recommended)</option>
              <option value="gemini-1.5-pro">Google Gemini 1.5 Pro</option>
              <option value="gpt-4o">OpenAI GPT-4o</option>
              <option value="local-sre-engine">Local Built-in SRE Reasoning Engine</option>
            </select>
            <span className="text-[11px] text-[#737373] mt-1 block">
              Default fallback automatically utilizes high-precision local SRE extraction if no external API key is configured.
            </span>
          </div>

          {/* API Key */}
          <div>
            <label className="text-xs font-semibold text-[#A3A3A3] uppercase tracking-wider block mb-2 flex items-center space-x-1.5">
              <Key size={13} className="text-blue-400" />
              <span>Gemini / OpenAI API Key</span>
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={settings.api_key || ''}
                onChange={(e) => setSettings({ ...settings, api_key: e.target.value })}
                placeholder="AIzaSy... (leave blank to use built-in engine)"
                className="w-full bg-[#181818] border border-[#262626] rounded-xl px-3.5 py-2.5 text-sm text-white pr-10 focus:outline-none focus:border-blue-500 font-mono transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-2.5 text-[#737373] hover:text-[#A3A3A3]"
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <span className="text-[11px] text-[#737373] mt-1 block">
              Keys remain stored in local memory and are never transmitted to third-party tracking services.
            </span>
          </div>

          {/* Temperature */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-[#A3A3A3] uppercase tracking-wider">
                Temperature (Hallucination Control)
              </label>
              <span className="text-xs font-mono text-blue-400">{settings.temperature}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={settings.temperature}
              onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
              className="w-full accent-blue-500 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-[#737373] mt-1">
              <span>0.0 (Strict / Factual)</span>
              <span>1.0 (Creative)</span>
            </div>
          </div>

          {/* Top K Chunks */}
          <div>
            <label className="text-xs font-semibold text-[#A3A3A3] uppercase tracking-wider block mb-2">
              Retrieved Context Chunks (Top-K)
            </label>
            <div className="grid grid-cols-4 gap-2">
              {[2, 3, 4, 6].map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setSettings({ ...settings, top_k_chunks: k })}
                  className={`py-2 rounded-xl text-xs font-medium border transition-colors ${
                    settings.top_k_chunks === k
                      ? 'bg-blue-600/20 text-blue-400 border-blue-500'
                      : 'bg-[#181818] text-[#A3A3A3] border-[#262626] hover:bg-[#222222]'
                  }`}
                >
                  {k} Chunks
                </button>
              ))}
            </div>
          </div>

          {/* UI Color Scheme */}
          <div className="pt-2 border-t border-[#262626]">
            <span className="text-xs font-semibold text-[#A3A3A3] uppercase tracking-wider block mb-1">
              Design Specification
            </span>
            <div className="p-3 bg-[#181818] rounded-xl border border-[#262626] flex items-center justify-between text-xs">
              <span className="text-[#A3A3A3]">ChatGPT Minimal Dark Interface</span>
              <span className="font-mono text-green-400 flex items-center space-x-1">
                <CheckCircle2 size={13} />
                <span>#000000 Enforced</span>
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#262626] bg-[#181818] flex justify-between items-center">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-transparent text-sm text-[#A3A3A3] hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white rounded-lg transition-colors flex items-center space-x-1.5"
          >
            <span>{saving ? 'Saving...' : 'Save Preferences'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
