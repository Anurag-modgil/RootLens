import React, { useState, useEffect } from 'react';
import { 
  AlertOctagon, 
  Play, 
  Loader2, 
  Terminal,
  ShieldCheck
} from 'lucide-react';

interface ClusterDetail {
  id: number;
  name: string;
  summary: string;
  log_count: number;
}

interface LogDetail {
  id: number;
  timestamp: string;
  service_name: string;
  log_level: string;
  message: string;
}

interface Incident {
  id: number;
  title: string;
  description: string;
  status: string;
  severity: string;
  remediation_status: string | null;
  remediation_action: string | null;
  created_at: string;
  updated_at: string;
  clusters: ClusterDetail[];
}

interface IncidentDetails extends Incident {
  logs: LogDetail[];
}

interface IncidentsProps {
  onApproveRemediation: (incidentId: number) => Promise<boolean>;
}

export const Incidents: React.FC<IncidentsProps> = ({ onApproveRemediation }) => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [details, setDetails] = useState<IncidentDetails | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || "";

  const fetchIncidents = async () => {
    try {
      let url = `${API_BASE}/api/v1/dashboard/incidents`;
      const params = [];
      if (severityFilter) params.push(`severity=${severityFilter}`);
      if (statusFilter) params.push(`status=${statusFilter}`);
      if (params.length > 0) url += `?${params.join('&')}`;

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setIncidents(data);
      }
    } catch (err) {
      console.error("Failed to fetch incidents", err);
    }
  };

  const fetchIncidentDetails = async (id: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/dashboard/incidents/${id}`);
      if (res.ok) {
        const data = await res.json();
        setDetails(data);
      }
    } catch (err) {
      console.error("Failed to fetch incident details", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, [severityFilter, statusFilter]);

  useEffect(() => {
    if (selectedId !== null) {
      fetchIncidentDetails(selectedId);
    } else {
      setDetails(null);
    }
  }, [selectedId]);

  const handleApprove = async (id: number) => {
    setActionLoading(true);
    const success = await onApproveRemediation(id);
    if (success) {
      // Re-fetch details and list
      await fetchIncidentDetails(id);
      await fetchIncidents();
    }
    setActionLoading(false);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 h-[calc(100vh-100px)]">
      {/* Incidents Table / List */}
      <div className="lg:col-span-2 glass-panel rounded-2xl p-6 border border-slate-800/60 flex flex-col h-full overflow-hidden">
        <div className="space-y-4 mb-4">
          <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
            <AlertOctagon className="w-5 h-5 text-accent-magenta" /> System Incidents
          </h2>
          
          {/* Filters */}
          <div className="grid grid-cols-2 gap-3">
            <select 
              value={severityFilter} 
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-purple-500"
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
            <select 
              value={statusFilter} 
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-purple-500"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="RESOLVED">Resolved</option>
            </select>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 pr-1">
          {incidents.map((inc) => {
            const isSelected = selectedId === inc.id;
            return (
              <button
                key={inc.id}
                onClick={() => setSelectedId(inc.id)}
                className={`w-full text-left p-4 rounded-xl transition-all duration-200 border ${
                  isSelected 
                    ? 'bg-purple-950/20 border-accent-magenta/60 shadow-lg shadow-rose-950/10' 
                    : 'bg-slate-900/40 border-slate-800/60 hover:bg-slate-800/30'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`px-2 py-0.5 text-[9px] font-extrabold rounded-full uppercase ${
                    inc.severity === 'CRITICAL' ? 'bg-rose-500/10 text-rose-400' :
                    inc.severity === 'HIGH' ? 'bg-amber-500/10 text-amber-400' :
                    inc.severity === 'MEDIUM' ? 'bg-violet-500/10 text-violet-400' :
                    'bg-slate-500/10 text-slate-400'
                  }`}>
                    {inc.severity}
                  </span>
                  <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded ${
                    inc.status === 'RESOLVED' ? 'bg-emerald-950 text-emerald-400' : 'bg-rose-950 text-rose-400'
                  }`}>
                    {inc.status}
                  </span>
                </div>
                <h3 className="font-semibold text-sm text-white line-clamp-1 mb-1">{inc.title}</h3>
                <p className="text-slate-400 text-xs line-clamp-2 mb-2">{inc.description}</p>
                <div className="flex items-center justify-between text-[10px] text-slate-500">
                  <span>ID: {inc.id} • {inc.clusters.length} Cluster(s)</span>
                  <span>{new Date(inc.created_at).toLocaleTimeString()}</span>
                </div>
              </button>
            );
          })}
          {incidents.length === 0 && (
            <div className="py-12 text-center text-slate-500 text-sm">
              No incidents match selected filters.
            </div>
          )}
        </div>
      </div>

      {/* Incident Detail Pane */}
      <div className="lg:col-span-3 glass-panel rounded-2xl p-6 border border-slate-800/60 flex flex-col h-full overflow-hidden">
        {selectedId === null ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-3">
            <AlertOctagon className="w-12 h-12 text-slate-700" />
            <p className="text-sm">Select an incident to view details, RCA, and remediation actions.</p>
          </div>
        ) : loading ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-accent-violet animate-spin" />
          </div>
        ) : details ? (
          <div className="flex-1 overflow-y-auto space-y-6 pr-1">
            {/* Header info */}
            <div className="border-b border-slate-800 pb-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-purple-400">INCIDENT ID: {details.id}</span>
                <span className="text-xs text-slate-500">{new Date(details.created_at).toLocaleString()}</span>
              </div>
              <h1 className="text-xl font-bold text-white leading-tight">{details.title}</h1>
              <p className="text-slate-300 text-sm leading-relaxed">{details.description}</p>
            </div>

            {/* Clusters & Summary */}
            <div className="space-y-3">
              <h3 className="font-bold text-slate-200 text-sm uppercase tracking-wider">Associated Clusters</h3>
              <div className="grid grid-cols-1 gap-3">
                {details.clusters.map((c) => (
                  <div key={c.id} className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60 flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold text-sm text-purple-300">{c.name}</h4>
                      <p className="text-slate-400 text-xs mt-1">{c.summary}</p>
                    </div>
                    <span className="px-3 py-1 rounded bg-slate-950 font-mono text-xs text-accent-cyan">
                      {c.log_count} logs
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Remediation approval section */}
            {details.remediation_action && (
              <div className="p-6 rounded-2xl bg-gradient-to-r from-purple-950/20 to-slate-900 border border-purple-900/30 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-white text-sm flex items-center gap-2">
                    <Terminal className="w-5 h-5 text-accent-violet" /> SRE Recovery Playbook
                  </h3>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                    details.remediation_status === 'SUCCESS' ? 'bg-emerald-950 text-emerald-400' :
                    details.remediation_status === 'FAILED' ? 'bg-rose-950 text-rose-400' :
                    details.remediation_status === 'EXECUTING' ? 'bg-blue-950 text-blue-400 animate-pulse' :
                    'bg-amber-950 text-amber-400 glow-incident'
                  }`}>
                    {details.remediation_status}
                  </span>
                </div>
                
                <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800/80 font-mono text-xs text-purple-300 select-all overflow-x-auto">
                  {details.remediation_action}
                </div>

                {details.remediation_status === 'PENDING_APPROVAL' && (
                  <button
                    onClick={() => handleApprove(details.id)}
                    disabled={actionLoading}
                    className="w-full bg-gradient-premium hover:opacity-90 active:scale-[0.98] text-white px-4 py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-purple-500/20"
                  >
                    {actionLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4 fill-current" />
                    )}
                    Approve & Run Self-Healing Command
                  </button>
                )}

                {details.remediation_status === 'SUCCESS' && (
                  <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
                    <ShieldCheck className="w-4 h-4" /> Remediation run successfully. Auto-verification complete.
                  </div>
                )}
              </div>
            )}

            {/* Related Raw Logs */}
            <div className="space-y-3">
              <h3 className="font-bold text-slate-200 text-sm uppercase tracking-wider">Telemetry Diagnostic Logs</h3>
              <div className="rounded-xl border border-slate-800/80 overflow-hidden font-mono text-[11px] leading-relaxed max-h-[300px] overflow-y-auto">
                {details.logs.map((log) => (
                  <div key={log.id} className="p-3 border-b border-slate-800/40 hover:bg-slate-900/50 flex flex-col space-y-1">
                    <div className="flex items-center gap-3">
                      <span className="text-slate-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                      <span className="text-purple-400">{log.service_name}</span>
                      <span className={`px-1 rounded text-[9px] font-bold ${
                        log.log_level === 'CRITICAL' || log.log_level === 'ERROR' ? 'bg-rose-950 text-rose-400' :
                        log.log_level === 'WARNING' ? 'bg-amber-950 text-amber-400' :
                        'bg-slate-800 text-slate-400'
                      }`}>
                        {log.log_level}
                      </span>
                    </div>
                    <p className="text-slate-300 whitespace-pre-wrap select-all">{log.message}</p>
                  </div>
                ))}
                {details.logs.length === 0 && (
                  <div className="py-8 text-center text-slate-600">No logs for this incident.</div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="py-8 text-center text-slate-500">Failed to load details.</div>
        )}
      </div>
    </div>
  );
};
