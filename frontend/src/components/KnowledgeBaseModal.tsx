import React from 'react';
import { X, Database, CheckCircle2, Cpu, HardDrive, FileText, Search } from 'lucide-react';
import { DocumentMetadata } from '../types';

interface KnowledgeBaseModalProps {
  documents: DocumentMetadata[];
  onClose: () => void;
}

export const KnowledgeBaseModal: React.FC<KnowledgeBaseModalProps> = ({
  documents,
  onClose
}) => {
  const totalPages = documents.reduce((acc, d) => acc + d.pages, 0);
  const totalChunks = documents.reduce((acc, d) => acc + d.chunks, 0);

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#262626] bg-[#181818]">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Database size={18} />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">SRE Knowledge Base & Index Status</h3>
              <p className="text-xs text-[#A3A3A3]">High-performance hybrid vector & keyword retrieval index</p>
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
          {/* Key Metric Stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-4 bg-[#1E1E1E] rounded-xl border border-[#262626]">
              <span className="text-[11px] text-[#737373] uppercase tracking-wider block">Indexed Runbooks</span>
              <span className="text-2xl font-bold text-white mt-1 block">{documents.length}</span>
              <span className="text-[11px] text-green-400 mt-1 block flex items-center space-x-1">
                <CheckCircle2 size={12} />
                <span>Active & Online</span>
              </span>
            </div>

            <div className="p-4 bg-[#1E1E1E] rounded-xl border border-[#262626]">
              <span className="text-[11px] text-[#737373] uppercase tracking-wider block">Total Pages</span>
              <span className="text-2xl font-bold text-blue-400 mt-1 block">{totalPages}</span>
              <span className="text-[11px] text-[#A3A3A3] mt-1 block">50-Page Enterprise Spec</span>
            </div>

            <div className="p-4 bg-[#1E1E1E] rounded-xl border border-[#262626]">
              <span className="text-[11px] text-[#737373] uppercase tracking-wider block">Vector Chunks</span>
              <span className="text-2xl font-bold text-emerald-400 mt-1 block">{totalChunks}</span>
              <span className="text-[11px] text-[#A3A3A3] mt-1 block">Full-Text Inverted Index</span>
            </div>
          </div>

          {/* Architecture Summary */}
          <div className="p-4 bg-[#181818] rounded-xl border border-[#262626] space-y-3">
            <h4 className="text-xs font-semibold text-[#F5F5F5] uppercase tracking-wider">
              Retrieval Engine Architecture
            </h4>
            <div className="space-y-2 text-xs text-[#A3A3A3] leading-relaxed">
              <div className="flex items-start space-x-2">
                <CheckCircle2 size={14} className="text-blue-400 shrink-0 mt-0.5" />
                <span><strong>Parser:</strong> PyMuPDF (fitz) with deterministic layout preservation and exact page-number extraction.</span>
              </div>
              <div className="flex items-start space-x-2">
                <CheckCircle2 size={14} className="text-blue-400 shrink-0 mt-0.5" />
                <span><strong>Vector Store:</strong> ChromaDB with dense embeddings + BM25/TF-IDF hybrid ranking.</span>
              </div>
              <div className="flex items-start space-x-2">
                <CheckCircle2 size={14} className="text-blue-400 shrink-0 mt-0.5" />
                <span><strong>Grounding:</strong> Strict page-level citations guaranteeing zero fabricated page numbers.</span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between p-3.5 bg-[#181818] rounded-xl border border-[#262626]">
            <div>
              <span className="text-sm font-medium text-white block">Need to query a runbook or architecture PDF?</span>
              <span className="text-xs text-[#737373]">Attach your technical documents directly in the chat input using the (+) button</span>
            </div>
          </div>
        </div>

        {/* Footer */}
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
