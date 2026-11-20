import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Maximize2,
  Minimize2,
  ExternalLink,
  Download,
  FileText,
  Loader2,
  AlertCircle
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
  onClose: () => void;
  width: number;
  onWidthChange: (newWidth: number) => void;
}

export const PdfViewerPanel: React.FC<PdfViewerPanelProps> = ({
  doc,
  pageNumber,
  onClose,
  width,
  onWidthChange
}) => {
  const [isMaximized, setIsMaximized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const isDraggingRef = useRef(false);

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

  // Determine source URL: prefer instant local blobUrl if available, otherwise backend file stream
  const rawFileUrl = blobUrl || (docId ? getDocumentFileUrl(docId) : '');
  const iframeSrc = rawFileUrl ? `${rawFileUrl}#page=${pageNumber || 1}&view=FitH` : '';

  return (
    <aside
      style={{ width: isMaximized ? '100%' : `${width}px` }}
      className={`relative h-screen bg-[#111111] border-l border-[#222222] flex flex-col z-20 transition-[width] duration-150 ease-out shrink-0 select-none ${
        isMaximized ? 'fixed inset-y-0 right-0 z-50 w-full' : ''
      }`}
    >
      {/* Draggable resize handle on left border */}
      {!isMaximized && (
        <div
          onMouseDown={handleStartResize}
          title="Drag to resize PDF viewer"
          className="absolute -left-1.5 top-0 bottom-0 w-3 cursor-col-resize z-30 group flex items-center justify-center hover:bg-blue-500/20 transition-colors"
        >
          <div className="w-0.5 h-12 rounded-full bg-[#333333] group-hover:bg-blue-400 transition-colors" />
        </div>
      )}

      {/* Top Header Bar (Antigravity breadcrumb style) */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-[#1E1E1E] bg-[#141414] shrink-0">
        <div className="flex items-center space-x-2 overflow-hidden pr-2">
          <span className="text-xs font-semibold text-[#888888] tracking-wide shrink-0">
            InfraMind
          </span>
          <span className="text-xs text-[#444444] shrink-0">&gt;</span>
          <div className="flex items-center space-x-1.5 truncate">
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
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-1 shrink-0">
          {rawFileUrl && (
            <a
              href={rawFileUrl}
              target="_blank"
              rel="noopener noreferrer"
              title="Open in new window"
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

          <button
            type="button"
            onClick={() => setIsMaximized(!isMaximized)}
            title={isMaximized ? 'Restore split view' : 'Maximize viewer'}
            className="p-1.5 text-[#A3A3A3] hover:text-white hover:bg-[#222222] rounded-lg transition-colors"
          >
            {isMaximized ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>

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
