import React, { useState, useEffect } from 'react';
import { X, BookOpen, ChevronRight, Terminal, ArrowRight, ShieldCheck, Flame } from 'lucide-react';
import { RunbookItem } from '../types';
import { fetchRunbooks } from '../api';

interface RunbooksModalProps {
  onSelectRunbook: (query: string) => void;
  onClose: () => void;
}

export const RunbooksModal: React.FC<RunbooksModalProps> = ({
  onSelectRunbook,
  onClose
}) => {
  const [runbooks, setRunbooks] = useState<RunbookItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRunbooks()
      .then(data => setRunbooks(data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-3xl bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#262626] bg-[#181818]">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <BookOpen size={18} />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">SRE Incident Runbooks Directory</h3>
              <p className="text-xs text-[#A3A3A3]">Pre-indexed incident response workflows from 50-page enterprise manual</p>
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
        <div className="p-6 overflow-y-auto space-y-3 text-left">
          {loading ? (
            <div className="py-12 text-center text-sm text-[#737373]">Loading runbook catalogue...</div>
          ) : (
            runbooks.map((rb) => (
              <div
                key={rb.id}
                className="p-4 bg-[#181818] rounded-xl border border-[#262626] hover:border-[#3B82F6]/50 transition-all flex flex-col justify-between"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase">
                        {rb.category}
                      </span>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border uppercase ${
                        rb.severity === 'SEV-1'
                          ? 'bg-red-500/10 text-red-400 border-red-500/20'
                          : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                      }`}>
                        {rb.severity}
                      </span>
                      <span className="text-xs text-[#737373]">{rb.page_range}</span>
                    </div>
                    <h4 className="text-sm font-semibold text-white">{rb.title}</h4>
                    <p className="text-xs text-[#A3A3A3] mt-1">{rb.summary}</p>
                  </div>

                  <button
                    onClick={() => {
                      onSelectRunbook(rb.title);
                      onClose();
                    }}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#262626] hover:bg-blue-600 text-xs font-medium text-white transition-colors shrink-0 ml-3"
                  >
                    <span>Execute in Chat</span>
                    <ArrowRight size={13} />
                  </button>
                </div>

                {/* Recommended Commands snippet */}
                <div className="mt-3 pt-2 border-t border-[#222222] flex items-center space-x-2 text-[11px] text-[#737373] font-mono overflow-x-auto">
                  <Terminal size={12} className="text-blue-400 shrink-0" />
                  <span className="truncate">Sample CLI: {rb.recommended_commands[0]}</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#262626] bg-[#181818] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[#262626] hover:bg-[#333333] text-sm text-white rounded-lg transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
