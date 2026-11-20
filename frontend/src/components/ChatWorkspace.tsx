import React, { useRef, useEffect } from 'react';
import { Loader2, Sparkles, RefreshCw, PanelLeft } from 'lucide-react';
import { ChatMessage, SourceReference } from '../types';
import { ChatMessageItem } from './ChatMessageItem';
import { ChatInput } from './ChatInput';

interface ChatWorkspaceProps {
  conversationTitle: string;
  messages: ChatMessage[];
  isLoading: boolean;
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  onOpenDocuments: () => void;
  onOpenSource: (source: SourceReference) => void;
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  onNewChat: () => void;
}

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  conversationTitle,
  messages,
  isLoading,
  input,
  setInput,
  onSend,
  onOpenDocuments,
  onOpenSource,
  isSidebarCollapsed,
  onToggleSidebar,
  onNewChat
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const isInitial = messages.length === 0;

  return (
    <main className="flex-1 h-screen bg-black flex flex-col justify-between overflow-hidden relative font-sans">
      {/* Top Header Bar */}
      <div className="h-14 px-6 flex items-center justify-between border-b border-transparent z-10">
        <div className="flex items-center space-x-3">
          {isSidebarCollapsed && (
            <button
              onClick={onToggleSidebar}
              title="Expand Sidebar"
              className="p-1.5 text-[#A3A3A3] hover:text-white hover:bg-[#141414] rounded-lg transition-colors"
            >
              <PanelLeft size={18} />
            </button>
          )}
          <span className="text-[14.5px] font-medium text-[#A3A3A3] truncate max-w-[400px]">
            {isInitial ? 'TitanOps AI' : conversationTitle}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={onNewChat}
            title="Reset Chat / New Session"
            className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#141414] rounded-lg transition-colors"
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {isInitial ? (
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
            onOpenDocuments={onOpenDocuments}
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
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-[850px] mx-auto w-full">
            {messages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                message={msg}
                onOpenSource={onOpenSource}
              />
            ))}

            {/* AI Loading State */}
            {isLoading && (
              <div className="flex items-center space-x-3 mb-6 text-[#A3A3A3] text-sm animate-pulse">
                <div className="w-7 h-7 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
                  <Loader2 size={15} className="animate-spin" />
                </div>
                <div className="flex items-center space-x-2">
                  <span>Analyzing runbook...</span>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping"></span>
                </div>
              </div>
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
            onOpenDocuments={onOpenDocuments}
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
