import React, { useEffect, useState } from 'react';
import { X, FileText, ExternalLink, BookOpen, Layers, CheckCircle2 } from 'lucide-react';
import { SourceReference, DocumentMetadata } from '../types';
import { fetchDocumentPage, getDocumentFileUrl } from '../api';

interface SourceModalProps {
  source: SourceReference | null;
  documents: DocumentMetadata[];
  onClose: () => void;
  onOpenSidePanel?: (doc: { id: string; name: string }, page?: number) => void;
}

export const SourceModal: React.FC<SourceModalProps> = ({
  source,
  documents,
  onClose,
  onOpenSidePanel
}) => {
  const [pageDetails, setPageDetails] = useState<{ text?: string; total_pages?: number } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!source) return;

    const matchedDoc = documents.find(d => d.filename === source.document_name);
    if (matchedDoc) {
      setLoading(true);
      fetchDocumentPage(matchedDoc.id, source.page_number)
        .then(data => setPageDetails(data))
        .catch(err => console.error(err))
        .finally(() => setLoading(false));
    }
  }, [source, documents]);

  if (!source) return null;

  const matchedDoc = documents.find(d => d.filename === source.document_name);
  const rawPdfUrl = matchedDoc ? `${getDocumentFileUrl(matchedDoc.id)}#page=${source.page_number}` : '#';

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#262626] bg-[#181818]">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <FileText size={18} />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Document Source Reference</h3>
              <p className="text-xs text-[#A3A3A3]">Ground truth extracted from verified technical runbook</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#A3A3A3] hover:text-white rounded-lg hover:bg-[#262626] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-left">
          {/* Metadata Cards */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-[#1E1E1E] rounded-xl border border-[#262626]">
              <span className="text-[11px] text-[#737373] uppercase tracking-wider block">Document</span>
              <span className="text-sm font-medium text-[#F5F5F5] truncate block mt-0.5">
                {source.document_name}
              </span>
            </div>
            <div className="p-3 bg-[#1E1E1E] rounded-xl border border-[#262626] flex items-center justify-between">
              <div>
                <span className="text-[11px] text-[#737373] uppercase tracking-wider block">Citation</span>
                <span className="text-sm font-semibold text-blue-400 block mt-0.5">
                  Page {source.page_number} {pageDetails?.total_pages ? `of ${pageDetails.total_pages}` : ''}
                </span>
              </div>
              <span className="text-xs px-2 py-1 bg-green-500/10 text-green-400 border border-green-500/20 rounded font-mono">
                Score: {source.score}
              </span>
            </div>
          </div>

          {/* Full Page Content */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-[#A3A3A3] uppercase tracking-wider flex items-center space-x-1.5">
                <BookOpen size={14} className="text-blue-400" />
                <span>Exact Text Content (Page {source.page_number})</span>
              </span>
              {matchedDoc && (
                <div className="flex items-center space-x-3">
                  {onOpenSidePanel && (
                    <button
                      type="button"
                      onClick={() => {
                        onOpenSidePanel({ id: matchedDoc.id, name: matchedDoc.filename }, source.page_number);
                        onClose();
                      }}
                      className="text-xs text-blue-400 hover:text-blue-300 hover:underline flex items-center space-x-1 font-medium"
                    >
                      <Layers size={13} />
                      <span>Open in Side Panel</span>
                    </button>
                  )}
                  <a
                    href={rawPdfUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-[#888888] hover:text-[#CCCCCC] flex items-center space-x-1"
                  >
                    <span>Raw PDF</span>
                    <ExternalLink size={11} />
                  </a>
                </div>
              )}
            </div>

            <div className="p-4 bg-[#0F0F0F] rounded-xl border border-[#262626] max-h-72 overflow-y-auto text-xs text-[#CBD5E1] font-mono leading-relaxed whitespace-pre-wrap selection:bg-blue-600">
              {loading ? (
                <div className="py-8 text-center text-[#737373]">Loading page text from PDF...</div>
              ) : pageDetails?.text ? (
                pageDetails.text
              ) : (
                source.snippet
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2 text-xs text-[#737373]">
            <CheckCircle2 size={14} className="text-green-400" />
            <span>Extracted via PyMuPDF (fitz) parser from official SRE runbook index.</span>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-[#262626] bg-[#181818] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[#262626] hover:bg-[#333333] text-sm text-white rounded-lg transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
