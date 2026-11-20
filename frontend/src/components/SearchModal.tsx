import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Search, X, MessageSquare, ArrowRight } from 'lucide-react';
import { ConversationSummary } from '../types';

interface SearchModalProps {
  conversations?: ConversationSummary[];
  onSelectConversation: (id: string) => void;
  onSelectRunbook?: (query: string) => void;
  onClose: () => void;
}

export const SearchModal: React.FC<SearchModalProps> = ({
  conversations = [],
  onSelectConversation,
  onClose
}) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const filteredConversations = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return conversations;
    return conversations.filter(c => c.title.toLowerCase().includes(q));
  }, [conversations, query]);

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/80 backdrop-blur-sm p-4 pt-20"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[75vh]"
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-[#262626] bg-[#181818]">
          <Search size={18} className="text-[#737373] mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search chat history..."
            className="flex-1 bg-transparent text-sm text-white placeholder-[#737373] outline-none font-sans"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 text-[#737373] hover:text-white mr-1"
            >
              <X size={15} />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] bg-[#262626] text-[#A3A3A3] rounded font-mono">
            ESC
          </kbd>
        </div>

        {/* Results Stream - ONLY Chat History */}
        <div className="p-4 overflow-y-auto space-y-4 text-left">
          {filteredConversations.length === 0 ? (
            <div className="py-8 text-center text-xs text-[#737373]">
              {query ? `No chat history found for "${query}".` : 'No chat history available.'}
            </div>
          ) : (
            <div>
              <span className="text-[11px] font-semibold text-[#737373] uppercase tracking-wider block mb-2 px-1">
                {query ? 'Matching Chats' : 'Chat History'}
              </span>
              <div className="space-y-1">
                {filteredConversations.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => {
                      onSelectConversation(c.id);
                      onClose();
                    }}
                    className="p-2.5 rounded-lg bg-[#181818] hover:bg-[#222222] cursor-pointer flex items-center justify-between text-xs transition-colors group"
                  >
                    <div className="flex items-center space-x-2.5 truncate">
                      <MessageSquare size={14} className="text-blue-400 shrink-0" />
                      <span className="text-white font-medium truncate">{c.title}</span>
                    </div>
                    <ArrowRight size={13} className="text-[#737373] group-hover:text-white transition-colors shrink-0 ml-2" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
