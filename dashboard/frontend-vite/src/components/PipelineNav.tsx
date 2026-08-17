import React from 'react';
import type { StageTab } from '../types';
import { FileCode, Search, Wrench, Shield, Activity, Settings, LayoutGrid } from 'lucide-react';

interface PipelineNavProps {
  activeTab: StageTab;
  onTabChange: (tab: StageTab) => void;
  prCount: number;
  criticalCount: number;
  anomalyCount: number;
}

export const PipelineNav: React.FC<PipelineNavProps> = ({
  activeTab,
  onTabChange,
  prCount,
  criticalCount,
  anomalyCount
}) => {
  return (
    <nav className="pipeline-nav">
      <button
        className={`nav-tab tab-overview ${activeTab === 'overview' ? 'active' : ''}`}
        onClick={() => onTabChange('overview')}
      >
        <LayoutGrid size={15} opacity={activeTab === 'overview' ? 1 : 0.65} />
        <span>Overview</span>
      </button>

      <span className="tab-arrow">&rsaquo;</span>

      <button
        className={`nav-tab tab-review ${activeTab === 'review' ? 'active' : ''}`}
        onClick={() => onTabChange('review')}
      >
        <FileCode size={15} opacity={activeTab === 'review' ? 1 : 0.65} />
        <span>Review</span>
        <span className="tab-badge">{prCount} PRs</span>
      </button>

      <span className="tab-arrow">&rsaquo;</span>

      <button
        className={`nav-tab tab-analyze ${activeTab === 'analyze' ? 'active' : ''}`}
        onClick={() => onTabChange('analyze')}
      >
        <Search size={15} opacity={activeTab === 'analyze' ? 1 : 0.65} />
        <span>Analyze</span>
        <span className="tab-badge">{anomalyCount > 0 ? `${anomalyCount} Alerts` : 'Live'}</span>
      </button>

      <span className="tab-arrow">&rsaquo;</span>

      <button
        className={`nav-tab tab-fix ${activeTab === 'fix' ? 'active' : ''}`}
        onClick={() => onTabChange('fix')}
      >
        <Wrench size={15} opacity={activeTab === 'fix' ? 1 : 0.65} />
        <span>Fix</span>
        <span className="tab-badge">Auto</span>
      </button>

      <span className="tab-arrow">&rsaquo;</span>

      <button
        className={`nav-tab tab-secure ${activeTab === 'secure' ? 'active' : ''}`}
        onClick={() => onTabChange('secure')}
      >
        <Shield size={15} opacity={activeTab === 'secure' ? 1 : 0.65} />
        <span>Secure</span>
        <span className="tab-badge">{criticalCount > 0 ? `${criticalCount} Crit` : 'Pass'}</span>
      </button>

      <div style={{ flex: 1 }} />

      <button
        className={`nav-tab tab-infra ${activeTab === 'infra' ? 'active' : ''}`}
        onClick={() => onTabChange('infra')}
      >
        <Activity size={15} opacity={activeTab === 'infra' ? 1 : 0.65} />
        <span>Infra Healing</span>
      </button>

      <button
        className={`nav-tab tab-settings ${activeTab === 'settings' ? 'active' : ''}`}
        onClick={() => onTabChange('settings')}
      >
        <Settings size={15} opacity={activeTab === 'settings' ? 1 : 0.65} />
        <span>Settings</span>
      </button>
    </nav>
  );
};
