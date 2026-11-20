import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatWorkspace } from './components/ChatWorkspace';
import { SourceModal } from './components/SourceModal';
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
  fetchDocuments,
  uploadDocument,
  indexDocument,
  fetchDocumentStage,
  retryDocumentProcessing,
  attachDocumentToConversation,
  detachDocumentFromConversation
} from './api';
import {
  ConversationSummary,
  ConversationDetail,
  ChatMessage,
  SourceReference,
  DocumentMetadata,
  AttachedDocument
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
  const [sidebarWidth, setSidebarWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('inframind_sidebar_width');
      if (saved) {
        const parsed = parseInt(saved, 10);
        if (!isNaN(parsed) && parsed >= 240 && parsed <= 720) {
          return parsed;
        }
      }
    } catch {}
    return 388;
  });

  const handleSidebarWidthChange = (newWidth: number) => {
    setSidebarWidth(newWidth);
    try {
      localStorage.setItem('inframind_sidebar_width', newWidth.toString());
    } catch {}
  };

  // Modals state
  const [activeSource, setActiveSource] = useState<SourceReference | null>(null);
  const [showRunbooksModal, setShowRunbooksModal] = useState(false);
  const [showIncidentsModal, setShowIncidentsModal] = useState(false);
  const [showKnowledgeModal, setShowKnowledgeModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<AttachedDocument[]>([]);
  const [conversationDocuments, setConversationDocuments] = useState<AttachedDocument[]>([]);

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
      // Restore persistent attached documents for this conversation
      setConversationDocuments(conv.documents || []);
      setPendingAttachments([]);
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
    setPendingAttachments([]);
    setConversationDocuments([]);
  };

  const [isRefreshingChat, setIsRefreshingChat] = useState(false);

  const handleRefreshChat = async () => {
    if (isRefreshingChat) return;
    setIsRefreshingChat(true);
    const minWait = new Promise(resolve => setTimeout(resolve, 800));
    try {
      if (activeConvId) {
        await Promise.all([
          loadConversation(activeConvId),
          loadInitialData(),
          minWait
        ]);
      } else {
        await Promise.all([
          loadInitialData(),
          minWait
        ]);
      }
    } catch (err) {
      console.error('Failed to refresh chat data:', err);
    } finally {
      setIsRefreshingChat(false);
    }
  };

  const pollPipelineStage = async (
    tempId: string,
    docId: string,
    filename: string,
    fileSize: number,
    fileObj?: File
  ) => {
    let isDone = false;
    const pollStartTime = Date.now();
    const MAX_TIMEOUT_MS = 180000; // 3 minutes timeout

    await new Promise<void>((resolve, reject) => {
      const timer = setInterval(async () => {
        if (isDone) {
          clearInterval(timer);
          return;
        }

        if (Date.now() - pollStartTime > MAX_TIMEOUT_MS) {
          isDone = true;
          clearInterval(timer);
          reject(new Error('Document processing timed out after 3 minutes. Please click Retry.'));
          return;
        }

        try {
          const stageInfo = await fetchDocumentStage(docId);
          if (!stageInfo || isDone) return;

          setPendingAttachments(prev =>
            prev.map(f => (f.id === tempId || f.document_id === docId ? {
              ...f,
              document_id: docId,
              stage: stageInfo.stage,
              stageLabel: stageInfo.message,
              progress: stageInfo.progress,
              status: stageInfo.stage === 'failed' ? 'failed' : (stageInfo.stage === 'ready' ? 'ready' : 'indexing'),
              error_message: stageInfo.error || f.error_message,
              failed_stage: stageInfo.failed_stage || f.failed_stage,
              isUploading: false
            } : f))
          );

          if (stageInfo.stage === 'ready') {
            isDone = true;
            clearInterval(timer);
            resolve();
          } else if (stageInfo.stage === 'failed') {
            isDone = true;
            clearInterval(timer);
            reject(new Error(stageInfo.error || 'Document processing failed'));
          }
        } catch (pollErr) {
          console.warn('Polling check warn:', pollErr);
        }
      }, 250);
    });

    // Mark as ready
    const readyAttach: AttachedDocument = {
      id: docId,
      document_id: docId,
      name: filename,
      size_bytes: fileSize,
      status: 'ready',
      stage: 'ready',
      stageLabel: 'Document ready!',
      progress: 100,
      isUploading: false,
      fileObj
    };

    setPendingAttachments(prev =>
      prev.map(f => (f.id === tempId || f.document_id === docId ? readyAttach : f))
    );

    if (activeConvId) {
      try {
        await attachDocumentToConversation(activeConvId, docId);
        const updatedConv = await fetchConversation(activeConvId);
        setConversationDocuments(updatedConv.documents || []);
        const updatedConvs = await fetchConversations();
        setConversations(updatedConvs);
      } catch (ce) {
        console.error('Failed to associate doc with conversation:', ce);
      }
    }

    const updatedDocs = await fetchDocuments();
    setDocuments(updatedDocs);
  };

  const runAttachmentProcessingPipeline = async (tempId: string, file: File, existingDocId?: string) => {
    let docId = existingDocId;

    try {
      if (!docId) {
        // Stage 1: Uploading PDF...
        setPendingAttachments(prev =>
          prev.map(f => (f.id === tempId ? {
            ...f,
            status: 'uploading',
            stage: 'uploading',
            stageLabel: 'Uploading PDF...',
            progress: 10,
            isUploading: true
          } : f))
        );

        const uploadRes = await uploadDocument(file);
        docId = uploadRes.document_id;
      }

      await pollPipelineStage(tempId, docId, file.name, file.size, file);
    } catch (err: any) {
      console.error('File upload/indexing failed:', err);
      setPendingAttachments(prev =>
        prev.map(f => (f.id === tempId || f.document_id === docId ? {
          ...f,
          document_id: docId,
          status: 'failed',
          stage: 'failed',
          stageLabel: 'Processing failed',
          progress: 0,
          isUploading: false,
          error_message: err.message || 'Processing failed'
        } : f))
      );
    }
  };

  const handleAttachFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return;
    }
    const tempId = `file-${Date.now()}`;
    const newAttach: AttachedDocument = {
      id: tempId,
      name: file.name,
      size_bytes: file.size,
      status: 'uploading',
      stage: 'uploading',
      stageLabel: 'Uploading PDF...',
      progress: 10,
      isUploading: true,
      fileObj: file
    };
    setPendingAttachments(prev => [...prev, newAttach]);

    await runAttachmentProcessingPipeline(tempId, file);
  };

  const handleRetryAttachment = async (id: string) => {
    const item = pendingAttachments.find(f => f.id === id);
    if (!item) return;

    if (item.document_id) {
      // Fast path: retry existing document without re-uploading file
      try {
        setPendingAttachments(prev =>
          prev.map(f => (f.id === id ? {
            ...f,
            status: 'indexing',
            stage: 'validating',
            stageLabel: 'Validating PDF...',
            progress: 20,
            error_message: undefined,
            failed_stage: undefined
          } : f))
        );

        await retryDocumentProcessing(item.document_id);
        await pollPipelineStage(item.id, item.document_id, item.name, item.size_bytes || 0, item.fileObj);
      } catch (err: any) {
        console.error('Retry failed:', err);
        setPendingAttachments(prev =>
          prev.map(f => (f.id === id ? {
            ...f,
            status: 'failed',
            stage: 'failed',
            stageLabel: 'Processing failed',
            progress: 0,
            isUploading: false,
            error_message: err.message || 'Processing retry failed'
          } : f))
        );
      }
    } else if (item.fileObj) {
      runAttachmentProcessingPipeline(item.id, item.fileObj);
    }
  };

  const handleRemovePendingAttachment = (id: string) => {
    setPendingAttachments(prev => prev.filter(f => f.id !== id));
  };

  const handleRemoveConversationDocument = async (id: string) => {
    const fileToRemove = conversationDocuments.find(f => f.id === id || f.document_id === id);
    const docId = fileToRemove?.document_id || id;
    setConversationDocuments(prev => prev.filter(f => f.id !== id && f.document_id !== id));

    if (activeConvId && docId) {
      try {
        await detachDocumentFromConversation(activeConvId, docId);
        const updatedConvs = await fetchConversations();
        setConversations(updatedConvs);
      } catch (e) {
        console.error('Failed to detach document on backend:', e);
      }
    }
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
    const isAnyPendingProcessing = pendingAttachments.some(
      f => f.status === 'uploading' || f.status === 'indexing' || f.isUploading
    );
    if (isAnyPendingProcessing || isLoading) return;

    const trimmed = input.trim();
    if (!trimmed && pendingAttachments.length === 0 && conversationDocuments.length === 0) return;

    // Combine pending new attachments with existing conversation documents so context is never lost across turns
    const allDocIds = Array.from(
      new Set(
        [
          ...pendingAttachments.map(f => f.document_id),
          ...conversationDocuments.map(f => f.document_id || f.id)
        ].filter((id): id is string => Boolean(id))
      )
    );

    const promptText = trimmed || (pendingAttachments.length > 0
      ? `Please analyze and summarize the attached document: ${pendingAttachments.map(f => f.name).join(', ')}`
      : '');

    // Snapshot pending attachments for user message bubble
    const msgAttachments = pendingAttachments.length > 0 ? [...pendingAttachments] : undefined;

    // Clear pending attachment immediately from the input box
    setPendingAttachments([]);
    setInput('');
    setIsLoading(true);

    const tempUserMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: promptText,
      timestamp: new Date().toISOString(),
      attachedFiles: msgAttachments
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const res = await sendChatMessage(
        promptText,
        activeConvId || undefined,
        allDocIds.length > 0 ? allDocIds : undefined
      );
      setMessages(prev => [...prev, res.message]);
      setActiveConvId(res.conversation_id);

      // Persist attached files in conversation context so user can continue asking questions
      if (res.attached_documents && res.attached_documents.length > 0) {
        setConversationDocuments(res.attached_documents);
      } else if (allDocIds.length > 0 && conversationDocuments.length === 0) {
        setConversationDocuments(pendingAttachments.filter(f => Boolean(f.document_id)));
      }

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
    <div className="flex h-screen w-screen overflow-hidden bg-black text-[#F5F5F5] font-sans">
      {/* Left Sidebar */}
      <Sidebar
        conversations={conversations}
        activeConvId={activeConvId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        onOpenRunbooks={() => setShowRunbooksModal(true)}
        onOpenIncidents={() => setShowIncidentsModal(true)}
        onOpenKnowledgeBase={() => setShowKnowledgeModal(true)}
        onOpenSettings={() => setShowSettingsModal(true)}
        onOpenSearch={() => setShowSearchModal(true)}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        width={sidebarWidth}
        onWidthChange={handleSidebarWidthChange}
        activeNavView={
          showRunbooksModal
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
        isRefreshing={isRefreshingChat}
        input={input}
        setInput={setInput}
        onSend={handleSend}
        onOpenSource={(src) => setActiveSource(src)}
        isSidebarCollapsed={isSidebarCollapsed}
        onToggleSidebar={() => setIsSidebarCollapsed(false)}
        onNewChat={handleNewChat}
        onRefreshChat={handleRefreshChat}
        pendingAttachments={pendingAttachments}
        conversationDocuments={conversationDocuments}
        onAttachFile={handleAttachFile}
        onRemovePendingAttachment={handleRemovePendingAttachment}
        onRetryAttachment={handleRetryAttachment}
        onRemoveConversationDocument={handleRemoveConversationDocument}
      />

      {/* Modals & Overlays */}
      {activeSource && (
        <SourceModal
          source={activeSource}
          documents={documents}
          onClose={() => setActiveSource(null)}
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
          conversations={conversations}
          onSelectConversation={handleSelectConversation}
          onClose={() => setShowSearchModal(false)}
        />
      )}
    </div>
  );
};
