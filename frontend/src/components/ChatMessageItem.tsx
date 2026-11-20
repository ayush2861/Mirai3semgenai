import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, FileText, ChevronRight } from 'lucide-react';
import { ChatMessage, SourceReference, AttachedDocument } from '../types';

interface ChatMessageItemProps {
  message: ChatMessage;
  onOpenSource: (source: SourceReference) => void;
  onOpenDocument?: (doc: AttachedDocument) => void;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  onOpenSource,
  onOpenDocument
}) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Strip verbose "Document Citations" and trailing raw citation lines from markdown
  const cleanContent = React.useMemo(() => {
    if (!message.content) return '';
    return message.content
      // Strip "### Document Citations" or "Document Citations" and anything after it
      .replace(/(?:\r?\n)*#{0,4}\s*Document Citations[\s\S]*$/i, '')
      // Strip trailing "Source: ... Page: ..." lines
      .replace(/(?:(?:\r?\n)+(?:\*\*Source:\*\*|Source:)\s*[^\n]+(?:\r?\n)+(?:\*\*Page:\*\*|Page:)\s*\d+[\s\S]*)+$/i, '')
      // Strip trailing "- Source: ... Page: ..."
      .replace(/(?:(?:\r?\n)+[-*]\s*(?:\*\*Source:\*\*|Source:)\s*[^\n]+(?:\r?\n)+\s*(?:\*\*Page:\*\*|Page:)\s*\d+)+$/i, '')
      .trim();
  }, [message.content]);

  // Deduplicate sources by (document_name, page_number)
  const uniqueSources = React.useMemo(() => {
    if (!message.sources || message.sources.length === 0) return [];
    if (/insufficient information/i.test(message.content)) return [];

    const seen = new Set<string>();
    const result: SourceReference[] = [];
    for (const src of message.sources) {
      if (!src.document_name || src.page_number === undefined || src.page_number === null) continue;
      const key = `${src.document_name.trim().toLowerCase()}::${src.page_number}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push(src);
      }
    }
    return result;
  }, [message.sources, message.content]);

  if (isUser) {
    return (
      <div className="flex justify-end mb-6">
        <div className="max-w-[75%] bg-[#1E1E1E] text-[#F5F5F5] rounded-3xl px-5 py-3.5 text-[15px] leading-relaxed shadow-sm border border-[#262626] select-text">
          {message.attachedFiles && message.attachedFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {message.attachedFiles.map((file) => {
                const displayName = file.name || file.document_name || 'Document.pdf';
                return (
                  <div
                    key={file.id || file.document_id || displayName}
                    onClick={() => onOpenDocument?.(file)}
                    className="w-[96px] h-[88px] rounded-2xl bg-[#141414] border border-[#2f2f2f] hover:border-blue-500/60 p-2 flex flex-col justify-between shadow-sm cursor-pointer transition-all hover:scale-[1.03] group"
                    title={`Click to open ${displayName} in PDF viewer`}
                  >
                    <div className="flex-1 w-full rounded-lg bg-[#0F0F0F] flex items-center justify-center group-hover:bg-[#181818] transition-colors">
                      <FileText size={20} className="text-[#888888] group-hover:text-blue-400 transition-colors" />
                    </div>
                    <div className="flex items-center space-x-1.5 mt-1 pt-0.5">
                      <span className="text-[9px] font-black tracking-wider px-1 py-0.5 rounded bg-[#DC2626] text-white leading-none">
                        PDF
                      </span>
                      <span className="text-[11px] font-medium text-[#E5E5E5] group-hover:text-white truncate flex-1 leading-tight">
                        {displayName}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col mb-10 text-left">
      {/* AI Header & Content */}
      <div className="flex items-start space-x-3 mb-2">
        <div className="w-7 h-7 shrink-0 mt-0.5 flex items-center justify-center mascot-avatar-glowing" title="InfraMind AI">
          <img
            src="/flame-mascot.png"
            alt="InfraMind Flame Mascot"
            className="w-6 h-6 object-contain select-none pointer-events-none"
          />
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="flex items-center justify-between pb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#737373]">
              TitanOps SRE Assistant
            </span>
            <button
              onClick={handleCopyMessage}
              title="Copy answer"
              className="p-1 text-[#737373] hover:text-[#A3A3A3] rounded transition-colors"
            >
              {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
            </button>
          </div>

          <div className="markdown-body text-[15px] text-[#E5E5E5] leading-relaxed select-text">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || '');
                  const codeString = String(children).replace(/\n$/, '');

                  if (!inline) {
                    return (
                      <div className="relative group my-3 rounded-lg overflow-hidden border border-[#262626] bg-[#121212]">
                        <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#181818] border-b border-[#262626] text-xs text-[#A3A3A3] font-mono">
                          <span>{match ? match[1] : 'bash'}</span>
                          <button
                            onClick={() => navigator.clipboard.writeText(codeString)}
                            className="flex items-center space-x-1 hover:text-white transition-colors"
                          >
                            <Copy size={12} />
                            <span>Copy</span>
                          </button>
                        </div>
                        <pre className="p-3.5 overflow-x-auto text-xs text-[#E2E8F0] font-mono leading-relaxed bg-[#0F0F0F]">
                          <code>{children}</code>
                        </pre>
                      </div>
                    );
                  }
                  return (
                    <code className="bg-[#1C1C1C] text-blue-300 px-1.5 py-0.5 rounded text-[13px] font-mono" {...props}>
                      {children}
                    </code>
                  );
                }
              }}
            >
              {cleanContent}
            </ReactMarkdown>
          </div>

          {/* Compact Sources Section matching Reference Image 3 */}
          {uniqueSources.length > 0 && (
            <div className="mt-5 pt-3.5 border-t border-[#262626]">
              <div className="text-[12px] font-semibold text-[#A3A3A3] uppercase tracking-wider mb-2.5 flex items-center space-x-1.5">
                <FileText size={14} className="text-blue-400" />
                <span>SOURCES:</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {uniqueSources.map((src, idx) => (
                  <button
                    key={`${src.document_name}-${src.page_number}-${idx}`}
                    onClick={() => onOpenSource(src)}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-[#141414] hover:bg-[#1C1C1C] border border-[#262626] hover:border-[#3A3A3A] text-left transition-all group shadow-sm"
                  >
                    <div className="flex items-center space-x-2.5 overflow-hidden">
                      <div className="w-7 h-7 rounded-md bg-[#132337] border border-blue-500/20 flex items-center justify-center text-blue-400 shrink-0 text-xs font-semibold">
                        P{src.page_number}
                      </div>
                      <div className="truncate">
                        <div className="text-[13px] font-medium text-[#F5F5F5] group-hover:text-blue-400 truncate" title={src.document_name}>
                          {src.document_name}
                        </div>
                        <div className="text-[11px] text-[#737373]">
                          Page {src.page_number}
                        </div>
                      </div>
                    </div>
                    <ChevronRight size={14} className="text-[#737373] group-hover:text-white shrink-0 ml-1 transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
