import React from 'react';
import { ShieldAlert, Radio, Smartphone, Activity, AlertTriangle, Layers } from 'lucide-react';
import { SURFACES } from '../../utils/constants';

/**
 * Universal Header Component for RAHAT Command
 * Controls surface switching, Surge Mode status, and system connection indicators.
 */
export default function Header({ 
  activeSurface, 
  setActiveSurface, 
  surgeMode = false, 
  onToggleSurge,
  isConnected = true 
}) {
  return (
    <header className="rahat-header">
      {/* Brand & District Title */}
      <div className="header-brand">
        <div className="brand-logo">
          <ShieldAlert className="logo-icon" size={26} />
        </div>
        <div>
          <div className="brand-title-row">
            <h1 className="brand-title">RAHAT COMMAND</h1>
            <span className="version-pill">ERSS-SURGE v2.0</span>
          </div>
          <p className="brand-subtitle">
            District Emergency Operations Centre • Rampur, Uttarakhand
          </p>
        </div>
      </div>

      {/* Surface Navigation Tabs (Switching views during hackathon demo) */}
      <nav className="surface-nav">
        <button
          className={`nav-btn ${activeSurface === SURFACES.OPERATOR ? 'active' : ''}`}
          onClick={() => setActiveSurface(SURFACES.OPERATOR)}
        >
          <Layers size={16} />
          <span>Operator Dashboard</span>
        </button>

        <button
          className={`nav-btn ${activeSurface === SURFACES.TEAM_PWA ? 'active' : ''}`}
          onClick={() => setActiveSurface(SURFACES.TEAM_PWA)}
        >
          <Smartphone size={16} />
          <span>Rescue Team PWA</span>
        </button>

        <button
          className={`nav-btn ${activeSurface === SURFACES.SIMULATOR ? 'active' : ''}`}
          onClick={() => setActiveSurface(SURFACES.SIMULATOR)}
        >
          <Radio size={16} />
          <span>Citizen Simulator</span>
        </button>
      </nav>

      {/* Surge Mode & System Status Controls */}
      <div className="header-controls">
        {/* Surge Mode Indicator & Trigger */}
        <button 
          className={`surge-toggle-btn ${surgeMode ? 'surge-active pulse-critical' : ''}`}
          onClick={onToggleSurge}
          title="Click to toggle Disaster Surge Mode"
        >
          <AlertTriangle size={15} />
          <span>{surgeMode ? 'SURGE MODE: ACTIVE' : 'SURGE MODE: STANDBY'}</span>
        </button>

        {/* Live Feed Heartbeat Indicator */}
        <div className="live-status-pill">
          <span className={`status-dot ${isConnected ? 'dot-online' : 'dot-offline'}`}></span>
          <span className="status-label">{isConnected ? 'LIVE WS' : 'DISCONNECTED'}</span>
        </div>
      </div>
    </header>
  );
}
