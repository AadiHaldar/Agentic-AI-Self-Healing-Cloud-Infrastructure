import React from 'react';
import type { ConnectedRepo, PRReviewRecord, SystemStatus } from '../types';
import { GitPullRequest, CheckCircle2, ExternalLink, Activity } from 'lucide-react';

interface OverviewPageProps {
  status: SystemStatus;
  repos: ConnectedRepo[];
  reviews: PRReviewRecord[];
  onNavigate: (tab: any) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  status,
  repos,
  reviews,
  onNavigate
}) => {
  const totalFindings = reviews.reduce((acc, r) => acc + (r.findings_count || 0), 0);
  const criticalFindings = reviews.reduce((acc, r) => acc + (r.critical_count || 0), 0);

  return (
    <div>
      {/* CTA / Quick Status */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(0, 212, 170, 0.08), rgba(124, 140, 248, 0.08))',
          border: '1px solid var(--sfm)',
          borderRadius: 'var(--rlg)',
          padding: '24px 28px',
          marginBottom: '22px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px'
        }}
      >
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '6px', color: '#ffffff', letterSpacing: '-0.02em' }}>
            Agentic AI Review &amp; Self-Healing Cloud
          </h2>
          <p style={{ color: 'var(--txm)', fontSize: '13px', maxWidth: '580px', lineHeight: 1.5 }}>
            Automated code review on every PR with Ruff, Bandit, Secrets scanner &amp; Gemini 2.0 Flash, paired with SimPy Digital Twin self-healing cloud operations.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <a href="/install" target="_blank" rel="noreferrer" className="btn btn-primary">
            <span>+ Connect Repository</span>
            <ExternalLink size={13} />
          </a>
          <button className="btn btn-outline" onClick={() => onNavigate('analyze')}>
            <span>Run Incident Test</span>
            <Activity size={13} />
          </button>
        </div>
      </div>

      {/* 4-col Metrics Grid */}
      <div className="metrics-grid">
        <div className="metric-card card-ember">
          <div className="metric-label">Critical Findings</div>
          <div className="metric-val">{criticalFindings}</div>
          <div className="metric-sub">Across all {repos.length || 1} connected repos</div>
        </div>

        <div className="metric-card card-seafoam">
          <div className="metric-label">PRs Reviewed</div>
          <div className="metric-val">{reviews.length}</div>
          <div className="metric-sub">{totalFindings} total findings surfaced</div>
        </div>

        <div className="metric-card card-indigo">
          <div className="metric-label">Connected Repos</div>
          <div className="metric-val">{repos.length}</div>
          <div className="metric-sub">Active webhooks &amp; check runs</div>
        </div>

        <div className="metric-card card-amber">
          <div className="metric-label">Infra Health</div>
          <div className="metric-val" style={{ fontSize: '24px', paddingTop: '4px' }}>
            {status.status}
          </div>
          <div className="metric-sub">{status.total_pods} pods in Digital Twin</div>
        </div>
      </div>

      {/* Two Columns */}
      <div className="two-col">
        {/* Recent Reviews Column */}
        <div className="card-panel">
          <div className="card-header">
            <div className="card-title">
              <GitPullRequest size={15} color="var(--sf)" />
              <span>Recent Pull Request Reviews</span>
            </div>
            <button className="btn btn-outline btn-sm" onClick={() => onNavigate('review')}>
              View All &rarr;
            </button>
          </div>

          <div className="card-body" style={{ padding: '0' }}>
            {reviews.length === 0 ? (
              <div className="empty-state">
                <GitPullRequest size={32} opacity={0.3} />
                <div>No Pull Requests reviewed yet. Open a PR in a connected repository to trigger automated analysis.</div>
              </div>
            ) : (
              reviews.slice(0, 5).map((rev) => (
                <div
                  key={rev.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 18px',
                    borderBottom: '1px solid var(--brd)',
                    fontSize: '12.5px'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--txh)', fontFamily: 'var(--fmono)' }}>
                      {rev.repo_full_name} #{rev.pr_number}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--txm)', marginTop: '2px' }}>
                      {rev.reviewed_at}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className="pill pill-info">{rev.findings_count} findings</span>
                    {rev.critical_count > 0 ? (
                      <span className="pill pill-critical">{rev.critical_count} critical</span>
                    ) : (
                      <span className="pill pill-success">Quality Gate Passed</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Connected Repositories Column */}
        <div className="card-panel">
          <div className="card-header">
            <div className="card-title">
              <CheckCircle2 size={15} color="var(--sf)" />
              <span>Connected Repositories</span>
            </div>
          </div>

          <div className="card-body" style={{ padding: '12px' }}>
            {repos.length === 0 ? (
              <div className="empty-state" style={{ padding: '18px' }}>
                <div>No repositories connected yet.</div>
                <a href="/install" target="_blank" rel="noreferrer" className="btn btn-primary btn-sm" style={{ marginTop: '8px' }}>
                  Install App &rarr;
                </a>
              </div>
            ) : (
              repos.map((repo, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 12px',
                    background: 'var(--bg2)',
                    border: '1px solid var(--brd)',
                    borderRadius: '8px',
                    marginBottom: '8px',
                    fontSize: '12px',
                    fontFamily: 'var(--fmono)'
                  }}
                >
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '210px', color: 'var(--txh)', fontWeight: 500 }}>
                    {repo.repo_full_name}
                  </div>
                  <span className="pill pill-success" style={{ fontSize: '10px' }}>
                    Active
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
