import React from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';
import { 
  Server, 
  AlertCircle, 
  Grid, 
  TrendingUp,
  Terminal,
  Clock
} from 'lucide-react';

interface LogEvent {
  event_type: string;
  data: any;
  timestamp: string;
}

interface OverviewProps {
  stats: {
    total_logs: number;
    total_incidents: number;
    active_incidents: number;
    total_clusters: number;
    severity_counts: { LOW: number; MEDIUM: number; HIGH: number; CRITICAL: number };
    service_stats: Array<{ name: string; total_logs: number; error_logs: number; status: string }>;
    ingestion_trend: Array<{ time: string; logs: number; errors: number }>;
  };
  notifications: LogEvent[];
}

export const Overview: React.FC<OverviewProps> = ({ stats, notifications }) => {
  const cardData = [
    { title: 'Total Ingested Logs', value: stats.total_logs, icon: Server, color: 'text-accent-cyan', bg: 'bg-emerald-500/10' },
    { title: 'Active Incidents', value: stats.active_incidents, icon: AlertCircle, color: 'text-accent-magenta', bg: 'bg-rose-500/10', class: stats.active_incidents > 0 ? 'glow-incident' : '' },
    { title: 'Log Clusters', value: stats.total_clusters, icon: Grid, color: 'text-accent-violet', bg: 'bg-violet-500/10' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            System Overview
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Real-time telemetry and SRE diagnostics dashboard.
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/40 border border-slate-700/50">
          <Clock className="w-4 h-4 text-accent-cyan" />
          <span className="text-xs font-mono text-slate-300">Live Engine Monitor</span>
        </div>
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {cardData.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div 
              key={idx} 
              className={`glass-panel-interactive p-6 rounded-2xl flex items-center justify-between border border-slate-800/60 ${card.class || ''}`}
            >
              <div className="space-y-2">
                <span className="text-slate-400 text-sm font-medium">{card.title}</span>
                <h3 className="text-4xl font-extrabold text-white tracking-tight">{card.value}</h3>
              </div>
              <div className={`${card.bg} p-4 rounded-xl`}>
                <Icon className={`w-8 h-8 ${card.color}`} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Log Ingestion Rate Chart */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800/60 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-accent-cyan" /> Ingestion Rate
            </h4>
            <span className="text-xs text-slate-400">Past 7 Hours</span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={stats.ingestion_trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorLogs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorErrors" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#FF007A" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#FF007A" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#121420', border: '1px solid #2B314B', borderRadius: '12px' }}
                  labelStyle={{ color: '#fff', fontWeight: 'bold' }}
                />
                <Area type="monotone" dataKey="logs" name="Total Logs" stroke="#8B5CF6" strokeWidth={2} fillOpacity={1} fill="url(#colorLogs)" />
                <Area type="monotone" dataKey="errors" name="Errors" stroke="#FF007A" strokeWidth={2} fillOpacity={1} fill="url(#colorErrors)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Severity Count Chart */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800/60 space-y-4">
          <h4 className="text-lg font-bold text-white">Incident Severity Distribution</h4>
          <div className="h-64 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[
                { name: 'Low', count: stats.severity_counts.LOW, fill: '#64748b' },
                { name: 'Med', count: stats.severity_counts.MEDIUM, fill: '#00DF89' },
                { name: 'High', count: stats.severity_counts.HIGH, fill: '#f59e0b' },
                { name: 'Crit', count: stats.severity_counts.CRITICAL, fill: '#FF007A' }
              ]}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#121420', border: '1px solid #2B314B', borderRadius: '12px' }}
                />
                <Bar dataKey="count" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Services and Notifications Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Service Health Grid */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800/60 space-y-4">
          <h4 className="text-lg font-bold text-white">Service Health Monitor</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-medium">
                  <th className="pb-3">Service Name</th>
                  <th className="pb-3">Total Logs</th>
                  <th className="pb-3">Error Count</th>
                  <th className="pb-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {stats.service_stats.map((service, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/10">
                    <td className="py-3 font-semibold text-white">{service.name}</td>
                    <td className="py-3 font-mono">{service.total_logs}</td>
                    <td className="py-3 font-mono text-accent-magenta">{service.error_logs}</td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded-full uppercase ${
                        service.status === 'healthy' ? 'bg-emerald-500/10 text-emerald-400' :
                        service.status === 'warning' ? 'bg-amber-500/10 text-amber-400' :
                        'bg-rose-500/10 text-rose-400 font-bold'
                      }`}>
                        {service.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {stats.service_stats.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">
                      No services registered. Send logs to begin.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Multi-Agent Log Stream */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800/60 flex flex-col space-y-4 max-h-[350px]">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-bold text-white flex items-center gap-2">
              <Terminal className="w-5 h-5 text-accent-violet animate-pulse" /> SRE Activity Feed
            </h4>
            <span className="text-xs text-purple-400 font-semibold uppercase animate-pulse">Streaming</span>
          </div>
          <div className="flex-1 overflow-y-auto space-y-3 font-mono text-xs pr-2">
            {notifications.map((note, idx) => (
              <div 
                key={idx} 
                className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/50 flex flex-col space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${
                    note.event_type.includes('fail') || note.event_type.includes('detected') ? 'bg-rose-950/50 text-rose-400' :
                    note.event_type.includes('resolve') || note.event_type.includes('success') ? 'bg-emerald-950/50 text-emerald-400' :
                    'bg-slate-800 text-slate-300'
                  }`}>
                    {note.event_type}
                  </span>
                  <span className="text-slate-500 text-[10px]">{note.timestamp}</span>
                </div>
                <pre className="text-slate-300 whitespace-pre-wrap select-all text-[11px] leading-relaxed">
                  {JSON.stringify(note.data, null, 2)}
                </pre>
              </div>
            ))}
            {notifications.length === 0 && (
              <div className="h-full flex items-center justify-center text-slate-500 py-12">
                Waiting for agent events...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
