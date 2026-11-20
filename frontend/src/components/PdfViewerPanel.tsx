import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Maximize2,
  Minimize2,
  ExternalLink,
  Download,
  FileText,
  Loader2,
  AlertCircle,
  ArrowLeft,
  Highlighter,
  Copy,
  Check,
  Search
} from 'lucide-react';
import { getDocumentFileUrl } from '../api';

export interface PdfViewerDocument {
  id?: string;
  document_id?: string;
  name?: string;
  filename?: string;
  document_name?: string;
  fileObj?: File | Blob;
}

interface PdfViewerPanelProps {
  doc: PdfViewerDocument | null;
  pageNumber?: number;
  highlightSnippet?: string;
  onClose: () => void;
  width: number;
  onWidthChange: (newWidth: number) => void;
}

/**
 * Extracts a clean 3 to 6 word search phrase from a citation snippet
 * to enable native PDFium / browser search highlighting and jumping.
 */
function extractHighlightPhrase(snippet?: string): string {
  if (!snippet) return '';
  // Split lines and strip markdown bullet points, hashes, quotes
  const lines = snippet
    .split('\n')
    .map(line => line.replace(/^[#*\-•\s"'>:]+/, '').trim())
    .filter(line => line.length > 0);

  if (lines.length === 0) return '';
  const firstLine = lines[0];

  // Strip punctuation that could break exact regex matches in PDF engines
  const clean = firstLine.replace(/[^\w\s\-]/g, ' ').replace(/\s+/g, ' ').trim();
  const words = clean.split(' ').filter(w => w.length > 0);
  if (words.length === 0) return '';

  const takeWords = Math.min(words.length, 5);
  return words.slice(0, takeWords).join(' ');
}

export const PdfViewerPanel: React.FC<PdfViewerPanelProps> = ({
  doc,
  pageNumber,
  highlightSnippet,
  onClose,
  width,
  onWidthChange
}) => {
  const [isMaximized, setIsMaximized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [showSnippetBanner, setShowSnippetBanner] = useState(true);
  const [copied, setCopied] = useState(false);
  const isDraggingRef = useRef(false);

  // Re-open snippet banner when a new snippet is selected
  useEffect(() => {
    if (highlightSnippet) {
      setShowSnippetBanner(true);
    }
  }, [highlightSnippet, pageNumber]);

  // Manage local Blob URL if a local File object is available
  useEffect(() => {
    if (doc?.fileObj) {
      try {
        const url = URL.createObjectURL(doc.fileObj);
        setBlobUrl(url);
        setIsLoading(true);
        setHasError(false);
        return () => {
          URL.revokeObjectURL(url);
        };
      } catch (e) {
        console.error('Failed to create object URL for file:', e);
      }
    } else {
      setBlobUrl(null);
      setIsLoading(true);
      setHasError(false);
    }
  }, [doc?.fileObj, doc?.id, doc?.document_id]);

  // Keyboard shortcut: Escape to go back / restore split / close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isMaximized) {
          setIsMaximized(false);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMaximized, onClose]);

  // Handle draggable left border resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      e.preventDefault();
      const newWidth = window.innerWidth - e.clientX;
      const minWidth = 360;
      const maxWidth = Math.max(minWidth, window.innerWidth * 0.85);
      const clamped = Math.max(minWidth, Math.min(maxWidth, newWidth));
      onWidthChange(clamped);
    };

    const handleMouseUp = () => {
      if (isDraggingRef.current) {
        isDraggingRef.current = false;
        window.document.body.style.cursor = '';
        window.document.body.style.userSelect = '';
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [onWidthChange]);

  const handleStartResize = (e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingRef.current = true;
    window.document.body.style.cursor = 'col-resize';
    window.document.body.style.userSelect = 'none';
  };

  const handleCopySnippet = () => {
    if (highlightSnippet) {
      navigator.clipboard.writeText(highlightSnippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!doc) return null;

  // Resolve document ID (prioritizing real backend document_id over temporary frontend ID)
  const docId =
    doc.document_id ||
    (doc.id && !doc.id.startsWith('file-') ? doc.id : undefined);

  // Resolve human-readable document name
  const docName =
    doc.name ||
    doc.filename ||
    doc.document_name ||
    (doc.fileObj instanceof File ? doc.fileObj.name : 'Document.pdf');

  // Extract clean phrase for native search and line highlighting
  const highlightPhrase = extractHighlightPhrase(highlightSnippet);

  // Determine source URL: prefer instant local blobUrl if available, otherwise backend file stream
  const rawFileUrl = blobUrl || (docId ? getDocumentFileUrl(docId) : '');
  const searchParam = highlightPhrase ? `&search=${encodeURIComponent(highlightPhrase)}` : '';
  const iframeSrc = rawFileUrl ? `${rawFileUrl}#page=${pageNumber || 1}${searchParam}&view=FitH` : '';

  return (
    <aside
      style={{ width: isMaximized ? '100vw' : `${width}px` }}
      className={`h-screen bg-[#111111] border-l border-[#222222] flex flex-col z-40 transition-all duration-150 ease-out shrink-0 select-none ${
        isMaximized
          ? 'fixed inset-0 z-50 w-screen h-screen max-w-[100vw] overflow-hidden'
          : 'relative'
      }`}
    >
      {/* Draggable resize handle on left border (in split mode) */}
      {!isMaximized && (
        <div
          onMouseDown={handleStartResize}
          title="Drag to resize PDF viewer"
          className="absolute -left-1.5 top-0 bottom-0 w-3 cursor-col-resize z-30 group flex items-center justify-center hover:bg-blue-500/20 transition-colors"
        >
          <div className="w-0.5 h-12 rounded-full bg-[#333333] group-hover:bg-blue-400 transition-colors" />
        </div>
      )}

      {/* Top Header Bar with prominent Back to Chat button */}
      <div className="h-14 w-full px-4 sm:px-6 flex items-center justify-between border-b border-[#1E1E1E] bg-[#141414] shrink-0 z-20">
        <div className="flex items-center space-x-2 min-w-0 pr-2">
          {/* Prominent Back to Chat button */}
          <button
            type="button"
            onClick={() => {
              if (isMaximized) {
                setIsMaximized(false);
              } else {
                onClose();
              }
            }}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#222222] hover:bg-[#2F2F2F] active:bg-[#1A1A1A] text-white border border-[#3A3A3A] hover:border-[#555555] text-xs font-semibold transition-all shrink-0 mr-2 shadow-sm group"
            title={isMaximized ? 'Return to split view with chat (Esc)' : 'Close viewer and back to chat (Esc)'}
          >
            <ArrowLeft size={14} className="group-hover:-translate-x-0.5 transition-transform text-[#A3A3A3] group-hover:text-white" />
            <span>Back to Chat</span>
          </button>

          <span className="text-xs font-semibold text-[#888888] tracking-wide shrink-0 hidden md:inline">
            InfraMind
          </span>
          <span className="text-xs text-[#444444] shrink-0 hidden md:inline">&gt;</span>
          <div className="flex items-center space-x-1.5 min-w-0 truncate">
            <span className="text-[9px] font-black tracking-wider px-1 py-0.5 rounded bg-[#DC2626] text-white shrink-0">
              PDF
            </span>
            <span
              className="text-xs font-medium text-[#E5E5E5] truncate"
              title={docName}
            >
              {docName}
            </span>
          </div>

          {/* Current Page Badge */}
          {pageNumber && (
            <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/30 text-blue-400 text-[11px] font-medium shrink-0 ml-1">
              Page {pageNumber}
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-1 sm:space-x-1.5 shrink-0 ml-2">
          {highlightPhrase && (
            <div
              className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/25 text-amber-300 text-xs"
              title={`Highlighting: "${highlightPhrase}"`}
            >
              <Search size={12} className="text-amber-400 shrink-0" />
              <span className="text-[11px] font-medium truncate max-w-[120px]">
                {highlightPhrase}
              </span>
            </div>
          )}

          {rawFileUrl && (
            <a
              href={rawFileUrl}
              target="_blank"
              rel="noopener noreferrer"
              title="Open in new browser tab"
              className="p-1.5 text-[#A3A3A3] hover:text-white hover:bg-[#222222] rounded-lg transition-colors"
            >
              <ExternalLink size={15} />
            </a>
          )}

          {rawFileUrl && (
            <a
              href={rawFileUrl}
              download={docName}
              title="Download PDF"
              className="p-1.5 text-[#A3A3A3] hover:text-white hover:bg-[#222222] rounded-lg transition-colors"
            >
              <Download size={15} />
            </a>
          )}

          {/* Toggle Full Screen / Split View */}
          <button
            type="button"
            onClick={() => setIsMaximized(!isMaximized)}
            title={isMaximized ? 'Restore split view with chat' : 'Full screen view'}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 text-[#A3A3A3] hover:text-white hover:bg-[#222222] rounded-lg transition-colors text-xs font-medium border border-transparent hover:border-[#333333]"
          >
            {isMaximized ? (
              <>
                <Minimize2 size={15} />
                <span className="hidden sm:inline">Split View</span>
              </>
            ) : (
              <>
                <Maximize2 size={15} />
                <span className="hidden sm:inline">Expand</span>
              </>
            )}
          </button>

          {/* Close button */}
          <button
            type="button"
            onClick={onClose}
            title="Close PDF Viewer"
            className="p-1.5 text-[#A3A3A3] hover:text-white hover:bg-[#262626] rounded-lg transition-colors ml-1"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Floating Citation Excerpt Banner (Interactive Highlight Line HUD) */}
      {showSnippetBanner && highlightSnippet && (
        <div className="bg-[#17140B] border-b border-amber-500/35 px-4 py-2.5 shadow-lg z-20 shrink-0 transition-all animate-fadeIn">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start space-x-2.5 min-w-0">
              <div className="w-6 h-6 rounded-md bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 shrink-0 mt-0.5 shadow-[0_0_10px_rgba(245,158,11,0.2)]">
                <Highlighter size={13} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider">
                    Cited Excerpt • Page {pageNumber || 1}
                  </span>
                  {highlightPhrase && (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-200 border border-amber-500/30 font-medium">
                      Line: "{highlightPhrase}"
                    </span>
                  )}
                </div>
                <p className="text-xs text-[#E5E5E5] leading-relaxed bg-[#201B0F] px-2.5 py-1.5 rounded border border-amber-500/25 italic font-normal line-clamp-3 select-text">
                  "{highlightSnippet}"
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-1.5 shrink-0 ml-2 mt-0.5">
              <button
                type="button"
                onClick={handleCopySnippet}
                className="flex items-center space-x-1 px-2.5 py-1 rounded bg-[#2A2314] hover:bg-[#382E1A] text-amber-300 hover:text-white text-xs font-medium border border-amber-500/30 transition-colors shadow-sm"
                title="Copy cited excerpt text"
              >
                {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
              <button
                type="button"
                onClick={() => setShowSnippetBanner(false)}
                className="p-1 text-[#888888] hover:text-white hover:bg-[#2A2314] rounded transition-colors"
                title="Dismiss highlight preview"
              >
                <X size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Viewer Body */}
      <div className="relative flex-1 w-full h-full bg-[#0D0D0D] overflow-hidden">
        {isLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0D0D0D] z-10 text-[#888888] space-y-2">
            <Loader2 size={24} className="animate-spin text-blue-400" />
            <span className="text-xs text-[#A3A3A3]">Rendering document...</span>
          </div>
        )}

        {hasError || !rawFileUrl ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-6 text-[#A3A3A3] space-y-3">
            <div className="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400">
              <AlertCircle size={20} />
            </div>
            <div className="text-sm font-medium text-white">Document is processing or unavailable</div>
            <p className="text-xs text-[#737373] max-w-sm">
              Please wait while the PDF finishes uploading, or click below to retry opening the file.
            </p>
            {rawFileUrl && (
              <a
                href={rawFileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors"
              >
                <ExternalLink size={13} />
                <span>Open in new tab</span>
              </a>
            )}
          </div>
        ) : (
          <iframe
            key={iframeSrc}
            src={iframeSrc}
            title={docName}
            onLoad={() => setIsLoading(false)}
            onError={() => {
              setIsLoading(false);
              setHasError(true);
            }}
            className="w-full h-full border-0 bg-[#0D0D0D]"
          />
        )}
      </div>
    </aside>
  );
};
