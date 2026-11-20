import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatWorkspace } from './components/ChatWorkspace';
import { SourceModal } from './components/SourceModal';
import { DocumentsModal } from './components/DocumentsModal';
import { RunbooksModal } from './components/RunbooksModal';
import { IncidentsModal } from './components/IncidentsModal';
import { KnowledgeBaseModal } from './components/KnowledgeBaseModal';
import { SettingsModal } from './components/SettingsModal';
import { SearchModal } from './components/SearchModal';
import {
  fetchConversations,
  fetchConversation,
  createConversation,
  deleteConversation,
  sendChatMessage,
  fetchDocuments
} from './api';
import {
  ConversationSummary,
  ConversationDetail,
  ChatMessage,
  SourceReference,
  DocumentMetadata
} from './types';

export const App: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [activeConversation, setActiveConversation] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Modals state
  const [activeSource, setActiveSource] = useState<SourceReference | null>(null);
  const [showDocumentsModal, setShowDocumentsModal] = useState(false);
  const [showRunbooksModal, setShowRunbooksModal] = useState(false);
  const [showIncidentsModal, setShowIncidentsModal] = useState(false);
  const [showKnowledgeModal, setShowKnowledgeModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [showSearchModal, setShowSearchModal] = useState(false);

  // Load conversations & documents
  const loadInitialData = useCallback(async () => {
    try {
      const [convs, docs] = await Promise.all([
        fetchConversations(),
        fetchDocuments()
      ]);
      setConversations(convs);
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load initial data:', err);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Load active conversation details
  const loadConversation = async (id: string) => {
    try {
      const conv = await fetchConversation(id);
      setActiveConvId(conv.id);
      setActiveConversation(conv);
      setMessages(conv.messages);
    } catch (err) {
      console.error('Failed to load conversation:', err);
    }
  };

  const handleSelectConversation = (id: string) => {
    loadConversation(id);
  };

  const handleNewChat = () => {
    setActiveConvId(null);
    setActiveConversation(null);
    setMessages([]);
    setInput('');
  };

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteConversation(id);
      const remaining = conversations.filter(c => c.id !== id);
      setConversations(remaining);
      if (activeConvId === id) {
        handleNewChat();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    setInput('');
    setIsLoading(true);

    const tempUserMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const res = await sendChatMessage(trimmed, activeConvId || undefined);
      setMessages(prev => [...prev, res.message]);
      setActiveConvId(res.conversation_id);

      // Refresh conversations list to update titles/timestamps
      const updatedConvs = await fetchConversations();
      setConversations(updatedConvs);
    } catch (err: any) {
      console.error('Chat error:', err);
      const errorMsg: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `**Error:** Failed to analyze documentation. ${err.message || 'Please check your connection and try again.'}`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExecutePromptInChat = (queryText: string) => {
    handleNewChat();
    setInput(queryText);
  };

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K for Search
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setShowSearchModal(prev => !prev);
      }
      // Cmd+N or Ctrl+N for New Chat
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        handleNewChat();
      }
      // Escape closes open modals
      if (e.key === 'Escape') {
        setActiveSource(null);
        setShowDocumentsModal(false);
        setShowRunbooksModal(false);
        setShowIncidentsModal(false);
        setShowKnowledgeModal(false);
        setShowSettingsModal(false);
        setShowSearchModal(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-black text-[#F5F5F5] select-none font-sans">
      {/* Left Sidebar */}
      <Sidebar
        conversations={conversations}
        activeConvId={activeConvId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        onOpenDocuments={() => setShowDocumentsModal(true)}
        onOpenRunbooks={() => setShowRunbooksModal(true)}
        onOpenIncidents={() => setShowIncidentsModal(true)}
        onOpenKnowledgeBase={() => setShowKnowledgeModal(true)}
        onOpenSettings={() => setShowSettingsModal(true)}
        onOpenSearch={() => setShowSearchModal(true)}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        activeNavView={
          showDocumentsModal
            ? 'documents'
            : showRunbooksModal
            ? 'runbooks'
            : showIncidentsModal
            ? 'incidents'
            : showKnowledgeModal
            ? 'knowledge'
            : 'chat'
        }
      />

      {/* Main Chat Workspace */}
      <ChatWorkspace
        conversationTitle={activeConversation?.title || 'New Chat'}
        messages={messages}
        isLoading={isLoading}
        input={input}
        setInput={setInput}
        onSend={handleSend}
        onOpenDocuments={() => setShowDocumentsModal(true)}
        onOpenSource={(src) => setActiveSource(src)}
        isSidebarCollapsed={isSidebarCollapsed}
        onToggleSidebar={() => setIsSidebarCollapsed(false)}
        onNewChat={handleNewChat}
      />

      {/* Modals & Overlays */}
      {activeSource && (
        <SourceModal
          source={activeSource}
          documents={documents}
          onClose={() => setActiveSource(null)}
        />
      )}

      {showDocumentsModal && (
        <DocumentsModal
          documents={documents}
          onRefresh={loadInitialData}
          onClose={() => setShowDocumentsModal(false)}
        />
      )}

      {showRunbooksModal && (
        <RunbooksModal
          onSelectRunbook={handleExecutePromptInChat}
          onClose={() => setShowRunbooksModal(false)}
        />
      )}

      {showIncidentsModal && (
        <IncidentsModal
          onSelectIncident={handleExecutePromptInChat}
          onClose={() => setShowIncidentsModal(false)}
        />
      )}

      {showKnowledgeModal && (
        <KnowledgeBaseModal
          documents={documents}
          onOpenDocuments={() => setShowDocumentsModal(true)}
          onClose={() => setShowKnowledgeModal(false)}
        />
      )}

      {showSettingsModal && (
        <SettingsModal
          onClose={() => setShowSettingsModal(false)}
        />
      )}

      {showSearchModal && (
        <SearchModal
          onSelectConversation={handleSelectConversation}
          onSelectRunbook={handleExecutePromptInChat}
          onClose={() => setShowSearchModal(false)}
        />
      )}
    </div>
  );
};
