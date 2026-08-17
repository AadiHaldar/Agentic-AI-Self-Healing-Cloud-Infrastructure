import React, { useState, useEffect } from 'react';
import type { StageTab, SystemStatus, ConnectedRepo, PRReviewRecord, TopologyData } from './types';
import { fetchSystemStatus, fetchConnectedRepos, fetchPRReviews, fetchTopology } from './api/client';
import { StatusBar } from './components/StatusBar';
import { PipelineNav } from './components/PipelineNav';
import { OverviewPage } from './pages/OverviewPage';
import { ReviewPage } from './pages/ReviewPage';
import { AnalyzePage } from './pages/AnalyzePage';
import { FixPage } from './pages/FixPage';
import { SecurePage } from './pages/SecurePage';
import { InfraHealingPage } from './pages/InfraHealingPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<StageTab>('overview');
  const [status, setStatus] = useState<SystemStatus>({
    status: 'HEALTHY',
    total_pods: 4,
    active_anomalies: 0,
    anomalous_pods: [],
    active_mode: 'parallel'
  });
  const [repos, setRepos] = useState<ConnectedRepo[]>([]);
  const [reviews, setReviews] = useState<PRReviewRecord[]>([]);
  const [topology, setTopology] = useState<TopologyData>({
    nodes: [
      { id: 'frontend', type: 'pod', cpu_usage: 0.35, memory_usage: 0.40, status: 'Healthy' },
      { id: 'checkoutservice', type: 'pod', cpu_usage: 0.88, memory_usage: 0.72, status: 'Warning' },
      { id: 'cartservice', type: 'pod', cpu_usage: 0.45, memory_usage: 0.50, status: 'Healthy' },
      { id: 'redis-cart', type: 'pod', cpu_usage: 0.20, memory_usage: 0.30, status: 'Healthy' }
    ],
    links: [
      { source: 'frontend', target: 'checkoutservice', relation: 'calls' },
      { source: 'checkoutservice', target: 'cartservice', relation: 'calls' },
      { source: 'cartservice', target: 'redis-cart', relation: 'calls' }
    ]
  });
  const [lastScanTime, setLastScanTime] = useState<string>('Just now');

  const loadData = async () => {
    try {
      const [st, rp, pr, tp] = await Promise.all([
        fetchSystemStatus(),
        fetchConnectedRepos(),
        fetchPRReviews(50),
        fetchTopology()
      ]);
      setStatus(st);
      setRepos(rp);
      setReviews(pr);
      setTopology(tp);
      setLastScanTime(new Date().toLocaleTimeString());
    } catch (e) {
      console.error('Error loading dashboard telemetry:', e);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 8000);
    return () => clearInterval(interval);
  }, []);

  const totalCritical = reviews.reduce((acc, r) => acc + (r.critical_count || 0), 0);

  return (
    <div className="app-container">
      <StatusBar status={status} lastScanTime={lastScanTime} />
      <PipelineNav
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        prCount={reviews.length}
        criticalCount={totalCritical}
        anomalyCount={status.active_anomalies}
      />

      <main className="main-content">
        {activeTab === 'overview' && (
          <OverviewPage
            status={status}
            repos={repos}
            reviews={reviews}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}

        {activeTab === 'review' && (
          <ReviewPage
            reviews={reviews}
            onRefresh={loadData}
            onDismissRule={(ruleId) => {
              console.log('Dismiss rule:', ruleId);
            }}
          />
        )}

        {activeTab === 'analyze' && <AnalyzePage />}

        {activeTab === 'fix' && <FixPage />}

        {activeTab === 'secure' && <SecurePage />}

        {activeTab === 'infra' && (
          <InfraHealingPage
            topology={topology}
            onRefreshTopology={loadData}
          />
        )}

        {activeTab === 'settings' && <SettingsPage repos={repos} />}
      </main>
    </div>
  );
};

export default App;
