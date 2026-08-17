import React from 'react';
import { GitBranch, ArrowUpRight } from 'lucide-react';

export const FixPage: React.FC = () => {
  const autoFixBranches = [
    {
      branch: 'autoreview/fix-bandit-b602-pr42',
      repo: 'AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure',
      issue: 'bandit/B602: Insecure subprocess shell=True vulnerability',
      status: 'PR Opened',
      time: '10m ago'
    },
    {
      branch: 'autoreview/fix-pip-audit-cve-2024-pr41',
      repo: 'AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure',
      issue: 'pip-audit: Upgrade vulnerable dependency scikit-learn>=1.4',
      status: 'PR Opened',
      time: '1h ago'
    }
  ];

  return (
    <div>
      <div style={{ marginBottom: '18px' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--txh)', letterSpacing: '-0.02em' }}>
          Automated Remediation &amp; Fix PRs
        </h2>
        <p style={{ color: 'var(--txm)', fontSize: '12px', marginTop: '2px' }}>
          Automatic Git branches and Pull Requests created by the agent for non-deterministic code issues.
        </p>
      </div>

      <div className="card-panel">
        <div className="card-header">
          <div className="card-title">
            <GitBranch size={15} color="var(--am)" />
            <span>Active Auto-Fix Branches ({autoFixBranches.length})</span>
          </div>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          {autoFixBranches.map((item, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px 20px',
                borderBottom: '1px solid var(--brd)',
                fontSize: '12.5px'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--txh)', fontFamily: 'var(--fmono)' }}>
                    {item.branch}
                  </span>
                  <span className="pill pill-warning" style={{ fontSize: '10px' }}>
                    {item.status}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--txm)', marginTop: '4px' }}>
                  {item.issue}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--txl)', marginTop: '2px' }}>
                  Target: {item.repo} • {item.time}
                </div>
              </div>

              <a
                href={`https://github.com/${item.repo}/pulls`}
                target="_blank"
                rel="noreferrer"
                className="btn btn-outline btn-sm"
              >
                <span>View PR</span>
                <ArrowUpRight size={12} />
              </a>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
