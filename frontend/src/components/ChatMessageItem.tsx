import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, FileText, ChevronRight, Sparkles } from 'lucide-react';
import { ChatMessage, SourceReference } from '../types';

interface ChatMessageItemProps {
  message: ChatMessage;
  onOpenSource: (source: SourceReference) => void;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  onOpenSource
}) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-6">
        <div className="max-w-[75%] bg-[#1E1E1E] text-[#F5F5F5] rounded-3xl px-5 py-3.5 text-[15px] leading-relaxed shadow-sm border border-[#262626]">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col mb-10 text-left">
      {/* AI Header & Content */}
      <div className="flex items-start space-x-3 mb-2">
        <div className="w-7 h-7 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0 mt-1">
          <Sparkles size={15} />
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

          <div className="markdown-body text-[15px] text-[#E5E5E5] leading-relaxed">
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
              {message.content}
            </ReactMarkdown>
          </div>

          {/* Sources Section */}
          {message.sources && message.sources.length > 0 && (
            <div className="mt-5 pt-3.5 border-t border-[#262626]">
              <div className="text-[12px] font-semibold text-[#A3A3A3] uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                <FileText size={14} className="text-blue-400" />
                <span>Sources:</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {message.sources.map((src, idx) => (
                  <button
                    key={idx}
                    onClick={() => onOpenSource(src)}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-[#141414] hover:bg-[#1C1C1C] border border-[#262626] text-left transition-all group"
                  >
                    <div className="flex items-center space-x-2.5 overflow-hidden">
                      <div className="w-6 h-6 rounded bg-blue-500/10 flex items-center justify-center text-blue-400 shrink-0 text-xs font-semibold">
                        P{src.page_number}
                      </div>
                      <div className="truncate">
                        <div className="text-[13px] font-medium text-[#F5F5F5] group-hover:text-blue-400 truncate">
                          {src.document_name}
                        </div>
                        <div className="text-[11px] text-[#737373]">
                          Page {src.page_number}
                        </div>
                      </div>
                    </div>
                    <ChevronRight size={14} className="text-[#737373] group-hover:text-white shrink-0 ml-1" />
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
