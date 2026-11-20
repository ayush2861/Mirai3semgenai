import React, { useState } from 'react';
import { AlertTriangle, Trash2, X, MessageSquare, FileText, Loader2 } from 'lucide-react';
import { ConversationSummary } from '../types';

interface ChatLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  conversations: ConversationSummary[];
  onDeleteConversation: (id: string, e: React.MouseEvent) => Promise<void> | void;
}

export const ChatLimitModal: React.FC<ChatLimitModalProps> = ({
  isOpen,
  onClose,
  conversations,
  onDeleteConversation
}) => {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setDeletingId(id);
      await onDeleteConversation(id, e);
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg bg-[#141414] border border-[#2E2E2E] rounded-2xl shadow-2xl overflow-hidden flex flex-col text-white"
      >
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-[#242424] flex items-start justify-between">
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/25 flex items-center justify-center text-amber-400 shrink-0">
              <AlertTriangle size={20} />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-[17px] font-semibold text-white tracking-tight">
                  Conversation Limit Reached
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  5/5 Max
                </span>
              </div>
              <p className="text-xs text-[#8E8E8E] mt-0.5">
                Maximum active conversations reached
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#888888] hover:text-white hover:bg-[#222222] rounded-lg transition-colors -mr-1 -mt-1"
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Informational Notice */}
        <div className="px-6 py-4 bg-[#1A1A1A]/60 border-b border-[#242424] text-xs text-[#B5B5B5] space-y-2">
          <p className="leading-relaxed">
            TitanOps AI supports up to <span className="text-white font-medium">5 active conversations</span> at a time. To start or continue with a new chat, please delete an existing conversation below.
          </p>
          <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300/90 text-[11.5px] leading-relaxed flex items-start space-x-2">
            <span className="shrink-0 mt-0.5">⚠️</span>
            <span>
              <strong className="text-amber-200 font-semibold">Data Folder Cleanup:</strong> Deleting a chat will permanently remove its attached PDF runbooks, indexed chunks, and embeddings from your storage (<code className="text-amber-100 bg-amber-950/40 px-1 py-0.5 rounded text-[10.5px]">data/</code> folder).
            </span>
          </div>
        </div>

        {/* Existing Conversations List */}
        <div className="p-4 max-h-[320px] overflow-y-auto space-y-2">
          <div className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wider text-[#737373]">
            Select a chat to delete ({conversations.length}/5)
          </div>

          {conversations.length === 0 ? (
            <div className="py-6 text-center text-xs text-[#737373]">
              No active conversations found.
            </div>
          ) : (
            conversations.map((conv) => {
              const hasPdf = (conv.documents && conv.documents.length > 0) || (conv.document_count && conv.document_count > 0);
              const isDeleting = deletingId === conv.id;

              return (
                <div
                  key={conv.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-[#181818] border border-[#262626] hover:border-[#383838] transition-colors group"
                >
                  <div className="flex items-center space-x-3 min-w-0 pr-3">
                    <div className="w-8 h-8 rounded-lg bg-[#222222] flex items-center justify-center text-[#8E8E8E] shrink-0">
                      {hasPdf ? (
                        <FileText size={16} className="text-red-400" />
                      ) : (
                        <MessageSquare size={16} className="text-[#8E8E8E]" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="text-[13.5px] font-medium text-[#E5E5E5] truncate">
                        {conv.title || 'Untitled Chat'}
                      </div>
                      <div className="flex items-center space-x-2 text-[11px] text-[#737373] mt-0.5">
                        <span>{conv.message_count ?? 0} messages</span>
                        {hasPdf && (
                          <>
                            <span>•</span>
                            <span className="text-red-400/90 font-medium flex items-center gap-1">
                              PDF Attached
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={(e) => handleDelete(conv.id, e)}
                    disabled={isDeleting}
                    className={`shrink-0 flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                      isDeleting
                        ? 'bg-red-500/10 text-red-400/70 border-red-500/20 cursor-not-allowed'
                        : 'bg-[#222222] text-[#A3A3A3] border-[#2E2E2E] hover:bg-red-500/15 hover:text-red-400 hover:border-red-500/30'
                    }`}
                    title="Delete this chat and clean up data folder"
                  >
                    {isDeleting ? (
                      <>
                        <Loader2 size={13} className="animate-spin" />
                        <span>Deleting...</span>
                      </>
                    ) : (
                      <>
                        <Trash2 size={13} />
                        <span>Delete</span>
                      </>
                    )}
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-[#242424] bg-[#111111] flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-[#A3A3A3] hover:text-white bg-[#1F1F1F] hover:bg-[#282828] border border-[#2E2E2E] rounded-lg transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
