import React, { useState, useEffect } from 'react';
import { X, AlertTriangle, CheckCircle2, Clock, ShieldAlert, Award, FileText } from 'lucide-react';
import { IncidentRecord } from '../types';
import { fetchIncidents } from '../api';

interface IncidentsModalProps {
  onSelectIncident: (query: string) => void;
  onClose: () => void;
}

export const IncidentsModal: React.FC<IncidentsModalProps> = ({
  onSelectIncident,
  onClose
}) => {
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchIncidents()
      .then(data => setIncidents(data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-3xl bg-[#141414] border border-[#262626] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#262626] bg-[#181818]">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center text-yellow-400">
              <AlertTriangle size={18} />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Incident History & SLA Compliance</h3>
              <p className="text-xs text-[#A3A3A3]">Production postmortems, MTTR performance, and financial service credits</p>
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
        <div className="p-6 overflow-y-auto space-y-3 text-left">
          {loading ? (
            <div className="py-12 text-center text-sm text-[#737373]">Loading incident logbook...</div>
          ) : (
            incidents.map((inc) => (
              <div
                key={inc.id}
                className="p-4 bg-[#181818] rounded-xl border border-[#262626] hover:border-[#333333] transition-all"
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-semibold text-blue-400">{inc.incident_number}</span>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border uppercase ${
                        inc.severity === 'SEV-1'
                          ? 'bg-red-500/10 text-red-400 border-red-500/20'
                          : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                      }`}>
                        {inc.severity}
                      </span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20 uppercase">
                        {inc.status}
                      </span>
                      <span className="text-xs text-[#737373]">{inc.service}</span>
                    </div>
                    <h4 className="text-sm font-semibold text-white">{inc.title}</h4>
                    <p className="text-xs text-[#A3A3A3] leading-relaxed">{inc.summary}</p>
                  </div>

                  <button
                    onClick={() => {
                      onSelectIncident(`Review incident ${inc.incident_number}: ${inc.title} and runbook resolution`);
                      onClose();
                    }}
                    className="px-3 py-1.5 rounded-lg bg-[#262626] hover:bg-blue-600 text-xs font-medium text-white transition-colors shrink-0 ml-3"
                  >
                    Analyze in Chat
                  </button>
                </div>

                <div className="mt-3 pt-2.5 border-t border-[#222222] grid grid-cols-3 gap-2 text-xs">
                  <div className="flex items-center space-x-1.5 text-[#A3A3A3]">
                    <Clock size={13} className="text-blue-400" />
                    <span>MTTR: <strong className="text-white">{inc.mttr_minutes}m</strong></span>
                  </div>
                  <div className="flex items-center space-x-1.5 text-[#A3A3A3]">
                    <ShieldAlert size={13} className={inc.sla_breached ? 'text-red-400' : 'text-green-400'} />
                    <span>SLA Breached: <strong className={inc.sla_breached ? 'text-red-400' : 'text-green-400'}>{inc.sla_breached ? 'YES' : 'NO'}</strong></span>
                  </div>
                  <div className="flex items-center space-x-1.5 text-[#A3A3A3]">
                    <Award size={13} className="text-yellow-400" />
                    <span className="truncate">Credit: <strong className="text-white">{inc.service_credit_tier}</strong></span>
                  </div>
                </div>
              </div>
            ))
          )}
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
