import React from 'react';
import { 
  LayoutDashboard, 
  AlertOctagon, 
  Layers, 
  Binary, 
  History, 
  Activity, 
  ShieldAlert 
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  wsStatus: 'connected' | 'disconnected' | 'connecting';
  activeIncidentCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  activeTab, 
  setActiveTab, 
  wsStatus,
  activeIncidentCount
}) => {
  const menuItems = [
    { id: 'overview', name: 'Overview', icon: LayoutDashboard },
    { id: 'incidents', name: 'Incidents', icon: AlertOctagon, badge: activeIncidentCount },
    { id: 'clusters', name: 'Log Clusters', icon: Layers },
    { id: 'rca', name: 'RCA Reports', icon: ShieldAlert },
    { id: 'remediations', name: 'Remediation Logs', icon: History },
  ];

  return (
    <aside className="w-64 h-screen glass-panel fixed left-0 top-0 flex flex-col justify-between border-r border-slate-800 z-10">
      <div>
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-800/80 flex items-center gap-3">
          <div className="bg-gradient-premium p-2 rounded-lg text-white shadow-lg shadow-purple-500/20">
            <Binary className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-purple-300 bg-clip-text text-transparent">
              RootLens
            </h1>
            <p className="text-[10px] text-purple-400 font-semibold tracking-wider uppercase">
              Self-Healing SRE
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="p-4 space-y-2 mt-4">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 group ${
                  isActive 
                    ? 'bg-purple-950/40 text-purple-200 border-l-4 border-accent-violet glass-panel shadow-inner' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/30 hover:translate-x-1'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-5 h-5 transition-transform duration-200 ${
                    isActive ? 'text-accent-violet' : 'text-slate-400 group-hover:text-slate-300'
                  }`} />
                  <span className="font-medium text-sm">{item.name}</span>
                </div>
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-accent-magenta text-white shadow-sm shadow-accent-magenta/30 animate-pulse">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* System Live Status Footer */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/20">
        <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-900/40 border border-slate-800/50">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-purple-400" />
            <span className="text-xs text-slate-400 font-medium">Real-Time Sync</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${
              wsStatus === 'connected' ? 'bg-accent-cyan shadow-sm shadow-emerald-500/50 animate-ping' :
              wsStatus === 'connecting' ? 'bg-amber-400 animate-pulse' : 'bg-rose-500'
            }`} />
            <span className="text-[10px] uppercase font-bold text-slate-500">
              {wsStatus}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
