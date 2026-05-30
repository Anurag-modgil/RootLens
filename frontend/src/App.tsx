import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Overview } from './pages/Overview';
import { Incidents } from './pages/Incidents';
import { Clusters } from './pages/Clusters';
import { RCAReports } from './pages/RCAReports';
import { RemediationHistory } from './pages/RemediationHistory';

interface LogEvent {
  event_type: string;
  data: any;
  timestamp: string;
}

interface Stats {
  total_logs: number;
  total_incidents: number;
  active_incidents: number;
  total_clusters: number;
  severity_counts: { LOW: number; MEDIUM: number; HIGH: number; CRITICAL: number };
  service_stats: Array<{ name: string; total_logs: number; error_logs: number; status: string }>;
  ingestion_trend: Array<{ time: string; logs: number; errors: number }>;
}

const initialStats: Stats = {
  total_logs: 0,
  total_incidents: 0,
  active_incidents: 0,
  total_clusters: 0,
  severity_counts: { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 },
  service_stats: [],
  ingestion_trend: []
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || "";
const WS_BASE = (import.meta.env.VITE_WS_BASE_URL as string) || "";

function App() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [stats, setStats] = useState<Stats>(initialStats);
  const [notifications, setNotifications] = useState<LogEvent[]>([]);
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');

  // Fetch general stats
  const fetchOverviewStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/dashboard/overview`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Failed to fetch overview stats", err);
    }
  };

  // Connect to WebSockets for SRE Agent real-time events
  useEffect(() => {
    let ws: WebSocket;
    const connectWS = () => {
      setWsStatus('connecting');
      let wsUrl = WS_BASE;
      if (!wsUrl) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${window.location.host}/ws/updates`;
      }
      
      console.log(`Connecting to SRE Agent WebSocket at: ${wsUrl}`);
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsStatus('connected');
        console.log("SRE WebSocket connected.");
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          console.log("WebSocket event received:", payload);
          
          // Append to feed
          const newEvent: LogEvent = {
            event_type: payload.event_type || 'AGENT_EVENT',
            data: payload.data || {},
            timestamp: new Date().toLocaleTimeString()
          };
          
          setNotifications(prev => [newEvent, ...prev].slice(0, 100));
          
          // Trigger a silent overview refresh
          fetchOverviewStats();
        } catch (err) {
          console.error("Failed to parse websocket event data:", err);
        }
      };

      ws.onclose = () => {
        setWsStatus('disconnected');
        console.log("SRE WebSocket closed. Retrying in 5 seconds...");
        setTimeout(connectWS, 5000);
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        ws.close();
      };
    };

    connectWS();
    fetchOverviewStats();
    
    // Poll stats periodically as fallback
    const interval = setInterval(fetchOverviewStats, 10000);

    return () => {
      if (ws) {
        ws.close();
      }
      clearInterval(interval);
    };
  }, []);

  const handleApproveRemediation = async (incidentId: number): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/dashboard/incidents/${incidentId}/approve`, {
        method: 'POST',
      });
      if (res.ok) {
        console.log(`Incident ID ${incidentId} remediation execution approved.`);
        fetchOverviewStats();
        return true;
      }
      return false;
    } catch (err) {
      console.error(`Failed to approve remediation for incident ${incidentId}`, err);
      return false;
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return <Overview stats={stats} notifications={notifications} />;
      case 'incidents':
        return <Incidents onApproveRemediation={handleApproveRemediation} />;
      case 'clusters':
        return <Clusters />;
      case 'rca':
        return <RCAReports />;
      case 'remediations':
        return <RemediationHistory />;
      default:
        return <Overview stats={stats} notifications={notifications} />;
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 text-slate-100 flex font-sans">
      {/* Fixed Sidebar */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        wsStatus={wsStatus}
        activeIncidentCount={stats.active_incidents}
      />

      {/* Main Panel */}
      <main className="flex-1 ml-64 p-8 min-h-screen overflow-x-hidden">
        <div className="max-w-7xl mx-auto">
          {renderContent()}
        </div>
      </main>
    </div>
  );
}

export default App;
