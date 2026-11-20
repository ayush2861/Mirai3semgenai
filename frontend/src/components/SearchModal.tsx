import React, { useState, useEffect, useRef } from 'react';
import { Search, X, MessageSquare, BookOpen, FileText, ArrowRight } from 'lucide-react';
import { globalSearch } from '../api';

interface SearchModalProps {
  onSelectConversation: (id: string) => void;
  onSelectRunbook: (query: string) => void;
  onClose: () => void;
}

export const SearchModal: React.FC<SearchModalProps> = ({
  onSelectConversation,
  onSelectRunbook,
  onClose
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<{
    conversations: any[];
    runbooks: any[];
    documents: any[];
  }>({ conversations: [], runbooks: [], documents: [] });
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!query.trim()) {
      setResults({ conversations: [], runbooks: [], documents: [] });
      return;
    }

    const timer = setTimeout(() => {
      setLoading(true);
      globalSearch(query)
        .then(data => setResults(data))
        .catch(err => console.error(err))
        .finally(() => setLoading(false));
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/80 backdrop-blur-sm p-4 pt-20">
      <div className="w-full max-w-2xl bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[75vh]">
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-[#262626] bg-[#181818]">
          <Search size={18} className="text-[#737373] mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search conversations, runbooks, or document pages..."
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

        {/* Results Stream */}
        <div className="p-4 overflow-y-auto space-y-4 text-left">
          {loading && (
            <div className="py-6 text-center text-xs text-[#737373]">Searching index...</div>
          )}

          {!loading && !query && (
            <div className="py-8 text-center text-xs text-[#737373]">
              Type a keyword like <em>etcd</em>, <em>Postgres</em>, <em>502</em>, <em>SLA</em>, or <em>cgroup</em>...
            </div>
          )}

          {!loading && query && results.conversations.length === 0 && results.runbooks.length === 0 && results.documents.length === 0 && (
            <div className="py-8 text-center text-xs text-[#737373]">
              No results found for &ldquo;{query}&rdquo;.
            </div>
          )}

          {/* Conversations */}
          {results.conversations.length > 0 && (
            <div>
              <span className="text-[11px] font-semibold text-[#737373] uppercase tracking-wider block mb-2 px-1">
                Conversations
              </span>
              <div className="space-y-1">
                {results.conversations.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => {
                      onSelectConversation(c.id);
                      onClose();
                    }}
                    className="p-2.5 rounded-lg bg-[#181818] hover:bg-[#222222] cursor-pointer flex items-center justify-between text-xs transition-colors"
                  >
                    <div className="flex items-center space-x-2.5">
                      <MessageSquare size={14} className="text-blue-400" />
                      <span className="text-white font-medium">{c.title}</span>
                    </div>
                    <ArrowRight size={13} className="text-[#737373]" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Runbooks */}
          {results.runbooks.length > 0 && (
            <div>
              <span className="text-[11px] font-semibold text-[#737373] uppercase tracking-wider block mb-2 px-1">
                Runbook Procedures
              </span>
              <div className="space-y-1">
                {results.runbooks.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => {
                      onSelectRunbook(r.title);
                      onClose();
                    }}
                    className="p-2.5 rounded-lg bg-[#181818] hover:bg-[#222222] cursor-pointer flex items-center justify-between text-xs transition-colors"
                  >
                    <div className="flex items-center space-x-2.5">
                      <BookOpen size={14} className="text-emerald-400" />
                      <span className="text-white font-medium">{r.title}</span>
                      <span className="text-[10px] text-[#737373]">{r.page_range}</span>
                    </div>
                    <ArrowRight size={13} className="text-[#737373]" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Document Snippets */}
          {results.documents.length > 0 && (
            <div>
              <span className="text-[11px] font-semibold text-[#737373] uppercase tracking-wider block mb-2 px-1">
                Runbook Document Chunks
              </span>
              <div className="space-y-1.5">
                {results.documents.map((d, i) => (
                  <div
                    key={i}
                    onClick={() => {
                      onSelectRunbook(`Analyze page ${d.page_number} of ${d.document_name}: ${d.section}`);
                      onClose();
                    }}
                    className="p-2.5 rounded-lg bg-[#181818] hover:bg-[#222222] cursor-pointer text-xs space-y-1 transition-colors"
                  >
                    <div className="flex items-center justify-between text-blue-400 font-medium">
                      <span>{d.document_name} — Page {d.page_number}</span>
                      <span className="text-[11px] text-[#737373]">{d.section}</span>
                    </div>
                    <p className="text-[#A3A3A3] line-clamp-2 text-[11.5px] leading-relaxed">
                      {d.snippet}
                    </p>
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
