import React, { useState, useEffect } from 'react';
import { Loader2, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

interface RemediationRecord {
  incident_id: number;
  incident_title: string;
  action: string;
  status: string;
  updated_at: string;
}

export const RemediationHistory: React.FC = () => {
  const [history, setHistory] = useState<RemediationRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/dashboard/remediations');
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (err) {
      console.error("Failed to fetch remediation history", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            Remediation Logs
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Audit trail of SRE self-healing actions, approvals, and post-remediation execution outcomes.
          </p>
        </div>
        <button 
          onClick={fetchHistory}
          className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
        >
          Refresh Logs
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-accent-violet animate-spin" />
        </div>
      ) : (
        <div className="glass-panel rounded-2xl border border-slate-800/60 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead>
                <tr className="border-b border-slate-800/80 text-slate-400 bg-slate-950/20 font-medium">
                  <th className="p-4">Incident ID</th>
                  <th className="p-4">Incident Title</th>
                  <th className="p-4">Remediation Action</th>
                  <th className="p-4">Outcome Status</th>
                  <th className="p-4">Updated Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {history.map((record, idx) => {
                  return (
                    <tr key={idx} className="hover:bg-slate-900/10">
                      <td className="p-4 font-mono text-purple-400 font-semibold">
                        #{record.incident_id}
                      </td>
                      <td className="p-4 font-medium text-white max-w-xs truncate">
                        {record.incident_title}
                      </td>
                      <td className="p-4">
                        <code className="px-2.5 py-1 rounded bg-slate-950 font-mono text-xs text-purple-300 border border-slate-900 select-all whitespace-nowrap block max-w-sm overflow-x-auto">
                          {record.action}
                        </code>
                      </td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold uppercase ${
                          record.status === 'SUCCESS' ? 'bg-emerald-500/10 text-emerald-400' :
                          record.status === 'FAILED' ? 'bg-rose-500/10 text-rose-400' :
                          record.status === 'EXECUTING' ? 'bg-sky-500/10 text-sky-400 animate-pulse' :
                          'bg-amber-500/10 text-amber-400'
                        }`}>
                          {record.status === 'SUCCESS' && <CheckCircle2 className="w-3.5 h-3.5" />}
                          {record.status === 'FAILED' && <XCircle className="w-3.5 h-3.5" />}
                          {record.status === 'EXECUTING' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                          {record.status === 'PENDING_APPROVAL' && <AlertTriangle className="w-3.5 h-3.5" />}
                          {record.status}
                        </span>
                      </td>
                      <td className="p-4 text-xs text-slate-500 font-mono">
                        {new Date(record.updated_at).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
                {history.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-12 text-center text-slate-500 font-medium">
                      No recovery executions logged in audit database.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
