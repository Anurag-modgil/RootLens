import React, { useState, useEffect } from 'react';
import { Layers, Loader2, Calendar, FileText, ChevronDown, ChevronUp } from 'lucide-react';

interface LogSample {
  id: number;
  timestamp: string;
  service_name: string;
  log_level: string;
  message: string;
}

interface Cluster {
  id: number;
  name: string;
  summary: string;
  log_count: number;
  created_at: string;
  samples: LogSample[];
}

export const Clusters: React.FC = () => {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchClusters = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/dashboard/clusters');
      if (res.ok) {
        const data = await res.json();
        setClusters(data);
      }
    } catch (err) {
      console.error("Failed to fetch clusters", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClusters();
  }, []);

  const toggleExpand = (id: number) => {
    if (expandedId === id) {
      setExpandedId(null);
    } else {
      setExpandedId(id);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
          HDBSCAN Log Clusters
        </h2>
        <p className="text-slate-400 text-sm mt-1">
          Vectorized log sequences clustered by similarity to identify patterns and anomalies automatically.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-accent-violet animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {clusters.map((cluster) => {
            const isExpanded = expandedId === cluster.id;
            return (
              <div 
                key={cluster.id} 
                className="glass-panel rounded-2xl border border-slate-800/60 overflow-hidden"
              >
                {/* Header panel */}
                <div 
                  onClick={() => toggleExpand(cluster.id)}
                  className="p-6 bg-slate-900/20 hover:bg-slate-800/20 flex items-center justify-between cursor-pointer transition-colors"
                >
                  <div className="space-y-2 max-w-4xl">
                    <div className="flex items-center gap-3">
                      <div className="bg-purple-950/50 p-2 rounded-lg text-accent-violet">
                        <Layers className="w-5 h-5" />
                      </div>
                      <h3 className="text-lg font-bold text-white tracking-tight">
                        {cluster.name}
                      </h3>
                      <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-slate-800 text-purple-300 font-mono">
                        Cluster ID: {cluster.id}
                      </span>
                    </div>
                    <p className="text-slate-300 text-sm">{cluster.summary}</p>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right space-y-1">
                      <span className="block text-2xl font-black text-accent-cyan font-mono">
                        {cluster.log_count}
                      </span>
                      <span className="block text-[10px] text-slate-500 uppercase font-bold tracking-wider">
                        Matching Logs
                      </span>
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-slate-400" />
                    )}
                  </div>
                </div>

                {/* Expanded contents: Sample logs */}
                {isExpanded && (
                  <div className="border-t border-slate-800/50 bg-slate-950/20 p-6 space-y-4">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                      <FileText className="w-4 h-4 text-purple-400" /> Pattern Telemetry Samples (Top 5)
                    </h4>
                    
                    <div className="space-y-3 font-mono text-xs">
                      {cluster.samples.map((sample) => (
                        <div 
                          key={sample.id} 
                          className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/50 flex flex-col space-y-2 hover:bg-slate-800/30 transition-colors"
                        >
                          <div className="flex items-center justify-between text-slate-500 text-[10px]">
                            <div className="flex items-center gap-3">
                              <span className="flex items-center gap-1">
                                <Calendar className="w-3 h-3" /> {new Date(sample.timestamp).toLocaleString()}
                              </span>
                              <span className="font-bold text-purple-400">{sample.service_name}</span>
                            </div>
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-extrabold uppercase ${
                              sample.log_level === 'CRITICAL' || sample.log_level === 'ERROR' ? 'bg-rose-950 text-rose-400' :
                              sample.log_level === 'WARNING' ? 'bg-amber-950 text-amber-400' :
                              'bg-slate-800 text-slate-400'
                            }`}>
                              {sample.log_level}
                            </span>
                          </div>
                          <pre className="text-slate-200 select-all whitespace-pre-wrap leading-relaxed text-[11px]">
                            {sample.message}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
          {clusters.length === 0 && (
            <div className="py-20 text-center text-slate-500 font-medium glass-panel rounded-2xl border border-slate-800/60">
              No clusters created. Ingest logs to run clustering checks automatically.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
