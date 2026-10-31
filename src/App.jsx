import React, { useState } from 'react';
import Header from './components/common/Header';
import { SURFACES } from './utils/constants';
import './App.css';

/**
 * Main Application Component for RAHAT
 * Serves as the master root hosting the 3 core hackathon surfaces.
 */
export default function App() {
  const [activeSurface, setActiveSurface] = useState(SURFACES.OPERATOR);
  const [surgeMode, setSurgeMode] = useState(false);
  const [isConnected, setIsConnected] = useState(true);

  const handleToggleSurge = () => {
    setSurgeMode(prev => !prev);
  };

  return (
    <div className="app-container">
      {/* Universal Command Header */}
      <Header
        activeSurface={activeSurface}
        setActiveSurface={setActiveSurface}
        surgeMode={surgeMode}
        onToggleSurge={handleToggleSurge}
        isConnected={isConnected}
      />

      {/* Surface Viewport Switching */}
      <main className="app-main" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {activeSurface === SURFACES.OPERATOR && (
          <div className="placeholder-view">
            <div className="placeholder-card">
              <span className="badge badge-crit placeholder-badge">SURFACE 1 • DESKTOP CONTROL ROOM</span>
              <h2 className="placeholder-title">Operator Command Dashboard</h2>
              <p className="placeholder-desc">
                High-density situational awareness dashboard for District Emergency Operations Centre (DEOC).
                Operators see merged incidents, not an unorganized message inbox.
              </p>
              <div className="placeholder-steps">
                <strong>Next to be built in upcoming Chunks:</strong>
                <div>• Chunk 2: Unified Mock Data Store & State Providers</div>
                <div>• Chunk 3: Live KPI Counters & Surge Banner</div>
                <div>• Chunk 4: Interactive Geospatial Leaflet Map (Incidents, Teams, Routes)</div>
                <div>• Chunk 5: Priority Triage Queue (CRIT / HIGH / MED / LOW)</div>
                <div>• Chunk 6: Incident Detail Drawer & Approve/Override Controls</div>
              </div>
            </div>
          </div>
        )}

        {activeSurface === SURFACES.TEAM_PWA && (
          <div className="placeholder-view">
            <div className="placeholder-card">
              <span className="badge badge-high placeholder-badge">SURFACE 2 • MOBILE PWA</span>
              <h2 className="placeholder-title">Rescue Team PWA (Field Unit)</h2>
              <p className="placeholder-desc">
                High-contrast, mobile-first interface designed for boats, medical vans, and SDRF personnel in weak-connectivity flood zones.
              </p>
              <div className="placeholder-steps">
                <strong>Coming in Chunk 7 & 8:</strong>
                <div>• Active Assignment details & "Open in Google Maps" turn-by-turn button</div>
                <div>• NDMA-grounded SOP interactive safety checklist</div>
                <div>• One-tap quick actions: [Reached], [Rescued], [No one here], [Need backup]</div>
                <div>• Offline mutation queue with auto-sync when network returns</div>
              </div>
            </div>
          </div>
        )}

        {activeSurface === SURFACES.SIMULATOR && (
          <div className="placeholder-view">
            <div className="placeholder-card">
              <span className="badge badge-low placeholder-badge">SURFACE 3 • INTERACTIVE BENCH</span>
              <h2 className="placeholder-title">Citizen Simulator (Judges Console)</h2>
              <p className="placeholder-desc">
                Interactive mobile testbench allowing hackathon judges to type custom Hinglish messages, test voice notes, and simulate IVR callbacks.
              </p>
              <div className="placeholder-steps">
                <strong>Coming in Chunk 9:</strong>
                <div>• Phone container mockup with WhatsApp & SMS tabs</div>
                <div>• Pre-loaded Hinglish test scenarios (Dadi trapped, duplicate spam, lone victim)</div>
                <div>• Simulated voice note audio uploader & STT transcription preview</div>
                <div>• Real-time ingestion feedback & HTTP response viewer</div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
