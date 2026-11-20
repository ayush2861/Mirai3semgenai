import React, { useRef, useEffect } from 'react';
import { Loader2, Sparkles, RefreshCw, PanelLeft, X } from 'lucide-react';
import { ChatMessage, SourceReference, AttachedDocument } from '../types';
import { ChatMessageItem } from './ChatMessageItem';
import { ChatInput } from './ChatInput';
import { FlameMascotLoading } from './FlameMascotLoading';

interface ChatWorkspaceProps {
  conversationTitle: string;
  messages: ChatMessage[];
  isLoading: boolean;
  isRefreshing?: boolean;
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  onOpenSource: (source: SourceReference) => void;
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  onNewChat: () => void;
  onRefreshChat?: () => void;
  pendingAttachments?: AttachedDocument[];
  conversationDocuments?: AttachedDocument[];
  onAttachFile?: (file: File) => Promise<void>;
  onRemovePendingAttachment?: (id: string) => void;
  onRemoveConversationDocument?: (id: string) => void;
}

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  conversationTitle,
  messages,
  isLoading,
  isRefreshing = false,
  input,
  setInput,
  onSend,
  onOpenSource,
  isSidebarCollapsed,
  onToggleSidebar,
  onNewChat,
  onRefreshChat,
  pendingAttachments = [],
  conversationDocuments = [],
  onAttachFile,
  onRemovePendingAttachment,
  onRemoveConversationDocument
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const isInitial = messages.length === 0;

  const inputPlaceholder = conversationDocuments && conversationDocuments.length > 0
    ? (conversationDocuments.length === 1 ? "Ask anything about this document..." : `Ask anything about these ${conversationDocuments.length} documents...`)
    : "Ask TitanOps anything about your infrastructure...";

  return (
    <main className="flex-1 h-screen bg-black flex flex-col justify-between overflow-hidden relative font-sans">
      {/* Top Header Bar */}
      <div className="h-14 px-6 flex items-center justify-between border-b border-[#1E1E1E] z-10 bg-black/40 backdrop-blur-md">
        <div className="flex items-center space-x-3 overflow-hidden">
          {isSidebarCollapsed && (
            <button
              onClick={onToggleSidebar}
              title="Expand Sidebar"
              className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#141414] rounded-lg transition-colors shrink-0"
            >
              <PanelLeft size={19} />
            </button>
          )}
          <div className="flex items-center space-x-2 overflow-hidden">
            <span className="text-sm font-medium text-[#E5E5E5] tracking-wide truncate max-w-[240px]">
              {conversationTitle}
            </span>

            {/* Persistent Conversation Documents Context Chip */}
            {conversationDocuments && conversationDocuments.length > 0 && (
              <div className="flex items-center space-x-2 ml-2 sm:ml-4 shrink-0">
                <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-[#181818] border border-[#2E2E2E] text-xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  <span className="text-[#888888] font-normal hidden sm:inline">Active Context:</span>
                  <div className="flex items-center gap-1.5 max-w-[420px] overflow-x-auto no-scrollbar">
                    {conversationDocuments.map((doc) => (
                      <span
                        key={doc.id || doc.document_id}
                        className="inline-flex items-center space-x-1.5 bg-[#222222] text-[#E5E5E5] px-2 py-0.5 rounded-md text-[11px] font-medium border border-[#333333]"
                        title={doc.name}
                      >
                        <span className="text-[8px] font-black tracking-wider px-1 py-0.2 rounded bg-[#DC2626] text-white">
                          PDF
                        </span>
                        <span className="truncate max-w-[130px]">{doc.name}</span>
                        {onRemoveConversationDocument && (
                          <button
                            type="button"
                            onClick={() => onRemoveConversationDocument(doc.id || doc.document_id || '')}
                            title={`Detach ${doc.name} from conversation`}
                            className="text-[#888888] hover:text-white p-0.5 rounded hover:bg-[#333333] transition-colors ml-0.5"
                          >
                            <X size={11} strokeWidth={2.5} />
                          </button>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={onRefreshChat || onNewChat}
            disabled={isRefreshing}
            title="Refresh Chat Data"
            className={`p-2 text-[#A3A3A3] hover:text-white hover:bg-[#141414] rounded-lg transition-colors ${
              isRefreshing ? 'opacity-70 cursor-not-allowed' : ''
            }`}
          >
            <RefreshCw size={17} className={isRefreshing ? 'animate-spin text-blue-400' : ''} />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {isRefreshing ? (
        <div className="flex-1 flex flex-col items-center justify-center -mt-16 px-4">
          <div className="flex flex-col items-center space-y-3.5 text-[#A3A3A3] text-sm animate-pulse">
            <div className="w-10 h-10 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Loader2 size={20} className="animate-spin" />
            </div>
            <span className="text-[#E5E5E5] font-medium text-sm">Loading chat data...</span>
            <span className="text-xs text-[#737373]">Syncing messages and runbook attachments</span>
          </div>
        </div>
      ) : isInitial ? (
        /* Initial Welcome Screen matching ChatGPT dark reference screenshot */
        <div className="flex-1 flex flex-col items-center justify-center -mt-16 px-4">
          <div className="text-center mb-8 max-w-[700px]">
            <h1 className="text-[32px] sm:text-[34px] font-semibold text-white tracking-tight mb-2.5">
              Your Cloud Operations, Under Control.
            </h1>
            <p className="text-[15.5px] sm:text-[16px] text-[#A3A3A3] font-normal">
              Ask anything about your infrastructure, incidents, runbooks, and service reliability.
            </p>
          </div>

          {/* Centered Chat Input Component */}
          <ChatInput
            input={input}
            setInput={setInput}
            onSend={onSend}
            isLoading={isLoading}
            pendingAttachments={pendingAttachments}
            onAttachFile={onAttachFile}
            onRemovePendingAttachment={onRemovePendingAttachment}
            placeholder={inputPlaceholder}
            isInitial={true}
          />

          {/* Quick starter suggestion chips */}
          <div className="mt-8 flex flex-wrap justify-center gap-2 max-w-[850px] px-4">
            {[
              "Kubernetes cluster outage etcd quorum loss",
              "Database PostgreSQL replication lag > 60s",
              "Envoy API gateway 502/504 errors mitigation",
              "SLA downtime formula and 25% credit tier"
            ].map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setInput(prompt);
                }}
                className="px-3.5 py-1.5 rounded-full bg-[#141414] hover:bg-[#1E1E1E] border border-[#262626] text-xs text-[#A3A3A3] hover:text-white transition-all text-left"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      ) : (
        /* Active Conversation Interface */
        <div className="flex-1 overflow-y-auto px-4 py-6 select-text">
          <div className="max-w-[850px] mx-auto w-full">
            {messages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                message={msg}
                onOpenSource={onOpenSource}
              />
            ))}

            {/* AI Analysis Loading State with Animated InfraMind Flame Mascot */}
            {isLoading && (
              <FlameMascotLoading hasDocument={conversationDocuments.length > 0} />
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      )}

      {/* Bottom Sticky Chat Input for active conversation */}
      {!isInitial && (
        <div className="w-full pb-6 pt-2 bg-gradient-to-t from-black via-black/90 to-transparent">
          <ChatInput
            input={input}
            setInput={setInput}
            onSend={onSend}
            isLoading={isLoading}
            pendingAttachments={pendingAttachments}
            onAttachFile={onAttachFile}
            onRemovePendingAttachment={onRemovePendingAttachment}
            placeholder={inputPlaceholder}
            isInitial={false}
          />
          <div className="text-center mt-2">
            <span className="text-[11px] text-[#555555]">
              TitanOps AI can make mistakes. Verify critical commands in your staging environment before executing in production.
            </span>
          </div>
        </div>
      )}
    </main>
  );
};
