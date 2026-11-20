import React, { useState, useRef } from 'react';
import {
  X,
  UploadCloud,
  FileText,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
  Layers
} from 'lucide-react';
import { DocumentMetadata } from '../types';
import { uploadDocument, deleteDocument } from '../api';

interface DocumentsModalProps {
  documents: DocumentMetadata[];
  onRefresh: () => void;
  onClose: () => void;
}

export const DocumentsModal: React.FC<DocumentsModalProps> = ({
  documents,
  onRefresh,
  onClose
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Only PDF files are supported for technical runbook indexing.');
      return;
    }
    setUploadError(null);
    setIsUploading(true);
    try {
      await uploadDocument(file);
      onRefresh();
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete and unindex this document?')) return;
    try {
      await deleteDocument(id);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to delete');
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-3xl bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[88vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#262626] bg-[#181818]">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <FileText size={18} />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Document Management</h3>
              <p className="text-xs text-[#A3A3A3]">Upload and index enterprise PDF runbooks for RAG retrieval</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#A3A3A3] hover:text-white rounded-lg hover:bg-[#262626] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-left">
          {/* Drag & Drop Area */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-7 text-center cursor-pointer transition-all ${
              isDragging
                ? 'border-blue-500 bg-blue-500/5'
                : 'border-[#262626] hover:border-[#3B82F6]/50 bg-[#181818]/60 hover:bg-[#181818]'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFile(e.target.files[0]);
                }
              }}
            />
            <div className="flex flex-col items-center">
              {isUploading ? (
                <>
                  <Loader2 size={36} className="text-blue-400 animate-spin mb-3" />
                  <span className="text-sm font-medium text-white">Extracting & indexing document chunks...</span>
                  <span className="text-xs text-[#737373] mt-1">PyMuPDF text extraction in progress</span>
                </>
              ) : (
                <>
                  <UploadCloud size={36} className="text-[#A3A3A3] mb-3 group-hover:text-blue-400" />
                  <span className="text-sm font-medium text-white">
                    Drag and drop your SRE Runbook PDF here, or <span className="text-blue-400 underline">browse</span>
                  </span>
                  <span className="text-xs text-[#737373] mt-1.5">
                    Supports technical runbooks, architecture specs, and incident escalation manuals (.pdf)
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Upload Error Banner */}
          {uploadError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center space-x-2 text-xs text-red-400">
              <AlertCircle size={15} />
              <span>{uploadError}</span>
            </div>
          )}

          {/* Indexed Documents Table */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-[#A3A3A3] uppercase tracking-wider flex items-center space-x-1.5">
                <Layers size={14} className="text-blue-400" />
                <span>Indexed Runbook Documents ({documents.length})</span>
              </span>
            </div>

            <div className="space-y-2">
              {documents.length === 0 ? (
                <div className="p-6 text-center text-sm text-[#737373] bg-[#181818] rounded-xl border border-[#262626]">
                  No documents indexed yet. Upload `titancloud_sre_incident_runbook_50p.pdf` above to begin.
                </div>
              ) : (
                documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-4 bg-[#181818] rounded-xl border border-[#262626] flex items-center justify-between hover:border-[#333333] transition-colors"
                  >
                    <div className="flex items-center space-x-3.5 overflow-hidden">
                      <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 shrink-0">
                        <FileText size={18} />
                      </div>
                      <div className="truncate">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-medium text-white truncate">{doc.filename}</span>
                          <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20">
                            {doc.status}
                          </span>
                        </div>
                        <div className="flex items-center space-x-3 text-xs text-[#737373] mt-1">
                          <span>{formatSize(doc.size_bytes)}</span>
                          <span>•</span>
                          <span>{doc.pages} pages</span>
                          <span>•</span>
                          <span>{doc.chunks} vector chunks</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      <a
                        href={`/api/documents/${doc.id}/raw`}
                        target="_blank"
                        rel="noreferrer"
                        title="View raw PDF"
                        className="p-2 text-[#A3A3A3] hover:text-white hover:bg-[#262626] rounded-lg transition-colors"
                      >
                        <ExternalLink size={16} />
                      </a>
                      <button
                        onClick={(e) => handleDelete(doc.id, e)}
                        title="Delete document"
                        className="p-2 text-[#A3A3A3] hover:text-red-400 hover:bg-[#262626] rounded-lg transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#262626] bg-[#181818] flex justify-between items-center">
          <span className="text-xs text-[#737373]">
            Automatic text extraction powered by PyMuPDF engine
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[#262626] hover:bg-[#333333] text-sm text-white rounded-lg transition-colors font-medium"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
