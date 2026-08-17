import React from 'react';
import type { SystemStatus } from '../types';
import { ShieldCheck, AlertTriangle, Cpu, ExternalLink } from 'lucide-react';

interface StatusBarProps {
  status: SystemStatus;
  lastScanTime: string;
}

export const StatusBar: React.FC<StatusBarProps> = ({ status, lastScanTime }) => {
  const isDegraded = status.status === 'DEGRADED' || status.active_anomalies > 0;

  return (
    <header className="status-bar">
      <div className="status-brand">
        <div className={`status-brand-dot ${isDegraded ? 'pulse-critical' : ''}`} />
        <span>Agentic AI</span>
      </div>

      <div className="status-divider" />

      <div className={`status-metric ${isDegraded ? 'metric-critical' : 'metric-healthy'}`}>
        <span className={`pulse-dot ${isDegraded ? 'pulse-critical' : ''}`} />
        <span className="status-metric-num">{status.active_anomalies}</span>
        <span>{isDegraded ? 'active anomalies' : 'critical'}</span>
      </div>

      <div className="status-metric metric-info">
        <Cpu size={14} opacity={0.7} />
        <span className="status-metric-num">{status.total_pods}</span>
        <span>pods monitored</span>
      </div>

      <div className="status-metric metric-healthy">
        {isDegraded ? <AlertTriangle size={14} color="var(--em)" /> : <ShieldCheck size={14} color="var(--sf)" />}
        <span className="status-metric-num">{status.status}</span>
      </div>

      <div style={{ flex: 1 }} />

      <div className="status-metric" style={{ fontSize: '11px', color: 'var(--txl)' }}>
        Last scan: {lastScanTime}
      </div>

      <div className="status-divider" />

      <a href="/install" target="_blank" rel="noreferrer" className="btn btn-primary btn-sm">
        <span>GitHub App</span>
        <ExternalLink size={12} />
      </a>
    </header>
  );
};
