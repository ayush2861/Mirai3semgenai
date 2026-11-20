import React, { useRef, useEffect, useState } from 'react';
import { Plus, ArrowUp, Loader2, Sparkles, FileText, X, CheckCircle2, AlertCircle } from 'lucide-react';
import { AttachedDocument } from '../types';
import { PdfIndexingAnimation } from './PdfIndexingAnimation';

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  isLoading: boolean;
  pendingAttachments?: AttachedDocument[];
  onAttachFile?: (file: File) => Promise<void>;
  onRemovePendingAttachment?: (id: string) => void;
  onRetryAttachment?: (id: string) => void;
  placeholder?: string;
  isInitial?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  input,
  setInput,
  onSend,
  isLoading,
  pendingAttachments = [],
  onAttachFile,
  onRemovePendingAttachment,
  onRetryAttachment,
  placeholder = "Ask TitanOps anything about your infrastructure...",
  isInitial = false
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!containerRef.current) return;
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight
        });
      }
    };
    updateSize();

    const ro = new ResizeObserver(() => {
      updateSize();
    });
    ro.observe(containerRef.current);
    window.addEventListener('resize', updateSize);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', updateSize);
    };
  }, []);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 180)}px`;
    }
  }, [input]);

  const isAnyProcessing = pendingAttachments.some(
    (f) => f.status === 'uploading' || f.status === 'indexing' || f.isUploading
  );

  const canSend = !isLoading && !isAnyProcessing && (input.trim() || pendingAttachments.length > 0);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (canSend) {
        onSend();
      }
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (onAttachFile) {
        await onAttachFile(file);
      }
      e.target.value = '';
    }
  };

  const hasAttachments = pendingAttachments.length > 0;

  return (
    <div className={`w-full flex justify-center transition-all duration-300 ${isInitial ? 'px-4' : 'px-4'}`}>
      <div 
        ref={containerRef}
        className={`relative w-[84%] max-w-[1050px] bg-[#1E1E1E] transition-all duration-200 shadow-2xl border border-[#2E2E2E] focus-within:border-[#444444] ${
          hasAttachments ? 'rounded-[26px] p-3 flex flex-col' : 'min-h-[64px] rounded-[36px] px-4 py-2 flex flex-col justify-center'
        }`}
      >
        {/* Animated Moving Blue Border Line */}
        {dimensions.width > 0 && dimensions.height > 0 && (
          <svg
            className="absolute inset-0 pointer-events-none w-full h-full overflow-visible z-10"
            style={{
              filter: 'drop-shadow(0 0 5px #60A5FA) drop-shadow(0 0 12px rgba(59, 130, 246, 0.7))'
            }}
          >
            <defs>
              <linearGradient id="chatBarBlueBeam" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#93C5FD" stopOpacity="1" />
                <stop offset="60%" stopColor="#3B82F6" stopOpacity="0.9" />
                <stop offset="100%" stopColor="#1D4ED8" stopOpacity="0.4" />
              </linearGradient>
            </defs>
            <rect
              x="0.5"
              y="0.5"
              width={Math.max(0, dimensions.width - 1)}
              height={Math.max(0, dimensions.height - 1)}
              rx={hasAttachments ? 26 : 36}
              fill="none"
              stroke="url(#chatBarBlueBeam)"
              strokeWidth="2.5"
              strokeLinecap="round"
              pathLength="1000"
              className="chat-bar-moving-beam"
            />
          </svg>
        )}

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Pending Attachments Gallery */}
        {hasAttachments && (
          <div className="relative z-20 flex flex-wrap items-center gap-2.5 mb-2 pl-1 pt-1">
            {pendingAttachments.map((file) => {
              const isProcessing = file.status === 'uploading' || file.status === 'indexing' || file.isUploading;
              const isFailed = file.status === 'failed';
              const isReady = file.status === 'ready' || (!isProcessing && !isFailed);

              // Map real backend stage to display text in correct order
              const getStageText = () => {
                if (file.stageLabel) return file.stageLabel;
                switch (file.stage) {
                  case 'uploading':
                    return 'Uploading PDF...';
                  case 'extracting_text':
                    return 'Extracting text...';
                  case 'analyzing_pages':
                    return 'Analyzing pages...';
                  case 'chunking_document':
                    return 'Chunking document...';
                  case 'generating_embeddings':
                    return 'Generating embeddings...';
                  case 'indexing_document':
                    return 'Indexing document...';
                  case 'ready':
                    return 'Ready to chat';
                  case 'failed':
                    return 'Processing failed';
                  default:
                    return file.status === 'indexing' ? 'Indexing document...' : 'Uploading PDF...';
                }
              };

              const stageText = getStageText();

              return (
                <div
                  key={file.id}
                  className="relative group w-[100px] h-[92px] rounded-2xl bg-[#141414] border border-[#2f2f2f] hover:border-[#444444] p-2 flex flex-col justify-between shadow-md transition-all"
                >
                  {/* Remove button */}
                  {onRemovePendingAttachment && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemovePendingAttachment(file.id);
                      }}
                      className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-[#2A2A2A] hover:bg-[#404040] text-[#A3A3A3] hover:text-white flex items-center justify-center transition-all shadow-md z-10 border border-[#3A3A3A]"
                      title="Remove attached file"
                    >
                      <X size={12} strokeWidth={2.5} />
                    </button>
                  )}

                  {/* Dark preview thumbnail with full-square animation */}
                  <div className="flex-1 w-full rounded-lg bg-[#000000] flex flex-col items-center justify-center overflow-hidden relative border border-[#1f1f1f]">
                    {isProcessing ? (
                      <PdfIndexingAnimation progress={file.progress} />
                    ) : isFailed ? (
                      <div
                        className="flex flex-col items-center justify-center space-y-1 p-1 text-center bg-[#0F0F0F] w-full h-full"
                        title={file.error_message || 'Indexing failed'}
                      >
                        <AlertCircle size={18} className="text-red-400 shrink-0" />
                        <span className="text-[9px] text-red-400 font-medium leading-tight">Error</span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center relative w-full h-full bg-[#0F0F0F]">
                        <FileText size={22} className="text-[#666666] group-hover:text-[#888888] transition-colors" />
                        <div className="absolute top-1 right-1">
                          <CheckCircle2 size={12} className="text-emerald-400" />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Processing stages / status below the animation */}
                  <div className="w-full mt-1 pt-0.5 overflow-hidden">
                    {isProcessing ? (
                      <div
                        className="flex items-center space-x-1 w-full overflow-hidden"
                        title={`${file.name} — ${stageText}`}
                      >
                        <span className="text-[8.5px] font-black tracking-wider px-1 py-0.5 rounded bg-[#DC2626] text-white leading-none shrink-0">
                          PDF
                        </span>
                        <div className="flex-1 min-w-0 flex items-center space-x-1">
                          {/* Animated pulsing indicator */}
                          <span className="relative flex h-1.5 w-1.5 shrink-0">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-blue-500"></span>
                          </span>
                          <span
                            key={stageText}
                            className="text-[9.5px] font-medium text-blue-300 truncate leading-tight animate-fade-in"
                          >
                            {stageText}
                          </span>
                        </div>
                      </div>
                    ) : isFailed ? (
                      <div className="flex items-center justify-between w-full">
                        <div
                          className="flex items-center space-x-1 min-w-0 flex-1 overflow-hidden"
                          title={file.error_message || 'Indexing failed'}
                        >
                          <span className="text-[8.5px] font-black tracking-wider px-1 py-0.5 rounded bg-[#DC2626] text-white leading-none shrink-0">
                            PDF
                          </span>
                          <span className="text-[9.5px] font-medium text-red-400 truncate leading-tight">
                            Failed
                          </span>
                        </div>
                        {onRetryAttachment && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onRetryAttachment(file.id);
                            }}
                            className="text-[9px] text-blue-400 hover:text-blue-300 font-semibold underline shrink-0 ml-1 cursor-pointer"
                            title="Retry processing"
                          >
                            Retry
                          </button>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center space-x-1.5 w-full">
                        <span className="text-[9px] font-black tracking-wider px-1 py-0.5 rounded bg-[#DC2626] text-white leading-none shrink-0">
                          PDF
                        </span>
                        <span
                          className="text-[11px] font-medium text-[#E5E5E5] truncate flex-1 leading-tight"
                          title={file.name}
                        >
                          {file.name}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Text Input Row */}
        <div className="relative z-20 flex items-center w-full">
          {!hasAttachments && (
            <button
              onClick={() => fileInputRef.current?.click()}
              type="button"
              title="Attach PDF Document"
              className="w-9 h-9 rounded-full hover:bg-[#2A2A2A] text-[#A3A3A3] hover:text-white flex items-center justify-center shrink-0 transition-colors mr-2"
            >
              <Plus size={20} />
            </button>
          )}

          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={placeholder}
            disabled={isLoading}
            className="flex-1 bg-transparent text-[#F5F5F5] placeholder-[#737373] text-[15.5px] leading-relaxed resize-none outline-none max-h-[180px] py-1 px-1 font-sans"
          />

          {!hasAttachments && (
            <div className="flex items-center space-x-2 shrink-0 ml-2">
              <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-[#2A2A2A]/70 text-[#A3A3A3] text-xs font-medium cursor-default">
                <Sparkles size={13} className="text-blue-400" />
                <span>SRE RAG</span>
              </div>

              <button
                onClick={onSend}
                disabled={!canSend}
                title={isAnyProcessing ? 'Processing PDF embeddings...' : 'Send (Enter)'}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-all ${
                  canSend
                    ? 'bg-[#3B82F6] hover:bg-blue-600 text-white cursor-pointer shadow-md shadow-blue-500/20'
                    : 'bg-[#2A2A2A] text-[#737373] cursor-not-allowed'
                }`}
              >
                {isLoading ? (
                  <Loader2 size={16} className="animate-spin text-white" />
                ) : (
                  <ArrowUp size={18} strokeWidth={2.5} />
                )}
              </button>
            </div>
          )}
        </div>

        {/* Bottom controls row when attachments exist */}
        {hasAttachments && (
          <div className="relative z-20 flex items-center justify-between pt-2 mt-1 border-t border-[#2A2A2A]/40">
            <button
              onClick={() => fileInputRef.current?.click()}
              type="button"
              title="Attach Another PDF Document"
              className="w-8 h-8 rounded-full hover:bg-[#2A2A2A] text-[#A3A3A3] hover:text-white flex items-center justify-center shrink-0 transition-colors"
            >
              <Plus size={19} />
            </button>

            <div className="flex items-center space-x-2">
              <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#2A2A2A]/70 text-[#A3A3A3] text-xs font-medium cursor-default">
                <Sparkles size={13} className="text-blue-400" />
                <span>SRE RAG</span>
              </div>

              <button
                onClick={onSend}
                disabled={!canSend}
                title={isAnyProcessing ? 'Processing PDF embeddings...' : 'Send (Enter)'}
                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                  canSend
                    ? 'bg-[#3B82F6] hover:bg-blue-600 text-white cursor-pointer shadow-md shadow-blue-500/20'
                    : 'bg-[#2A2A2A] text-[#737373] cursor-not-allowed'
                }`}
              >
                {isLoading ? (
                  <Loader2 size={15} className="animate-spin text-white" />
                ) : (
                  <ArrowUp size={17} strokeWidth={2.5} />
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
