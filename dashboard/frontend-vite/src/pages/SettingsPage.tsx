import React, { useState } from 'react';
import type { ConnectedRepo } from '../types';
import { dismissRule } from '../api/client';
import { Shield, Plus, CheckCircle2 } from 'lucide-react';

interface SettingsPageProps {
  repos: ConnectedRepo[];
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ repos }) => {
  const [ruleInput, setRuleInput] = useState('ruff/E501');
  const [selectedRepo, setSelectedRepo] = useState(repos[0]?.repo_full_name || 'AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure');
  const [dismissStatus, setDismissStatus] = useState<string | null>(null);

  const handleDismiss = async () => {
    try {
      await dismissRule(selectedRepo, ruleInput, 'Manual suppression from dashboard');
      setDismissStatus(`Rule ${ruleInput} successfully dismissed for ${selectedRepo}`);
    } catch (e: any) {
      setDismissStatus(`Error: ${e.message}`);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '18px' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--txh)', letterSpacing: '-0.02em' }}>
          Platform Settings &amp; Learning Rules
        </h2>
        <p style={{ color: 'var(--txm)', fontSize: '12px', marginTop: '2px' }}>
          Manage per-repository rule suppressions and GitHub App connection credentials.
        </p>
      </div>

      <div className="two-col">
        {/* Rule Dismissal / Learnings Form */}
        <div className="card-panel">
          <div className="card-header">
            <div className="card-title">
              <Shield size={15} color="var(--sf)" />
              <span>Learnings &amp; Finding Suppressions</span>
            </div>
          </div>

          <div className="card-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--txm)', marginBottom: '5px', fontWeight: 500 }}>
                  Target Repository
                </label>
                <select
                  value={selectedRepo}
                  onChange={(e) => setSelectedRepo(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--brdh)',
                    borderRadius: 'var(--rsm)',
                    padding: '7px 10px',
                    color: 'var(--txh)',
                    fontFamily: 'var(--fmono)',
                    fontSize: '12px'
                  }}
                >
                  {repos.map((r, i) => (
                    <option key={i} value={r.repo_full_name}>{r.repo_full_name}</option>
                  ))}
                  <option value="AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure">
                    AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure
                  </option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--txm)', marginBottom: '5px', fontWeight: 500 }}>
                  Rule ID to Suppress (e.g. <code>ruff/E501</code>, <code>bandit/B101</code>)
                </label>
                <input
                  type="text"
                  value={ruleInput}
                  onChange={(e) => setRuleInput(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--brdh)',
                    borderRadius: 'var(--rsm)',
                    padding: '7px 10px',
                    color: 'var(--txh)',
                    fontFamily: 'var(--fmono)',
                    fontSize: '12px'
                  }}
                />
              </div>

              <button className="btn btn-primary" onClick={handleDismiss} style={{ justifyContent: 'center', marginTop: '4px' }}>
                <Plus size={14} />
                <span>Add Suppression Rule</span>
              </button>

              {dismissStatus && (
                <div style={{ fontSize: '11.5px', color: 'var(--sf)', background: 'var(--sfd)', padding: '8px 12px', borderRadius: '6px' }}>
                  {dismissStatus}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* GitHub App Configuration Status */}
        <div className="card-panel">
          <div className="card-header">
            <div className="card-title">
              <CheckCircle2 size={15} color="var(--sf)" />
              <span>GitHub App Manifest Credentials</span>
            </div>
          </div>

          <div className="card-body" style={{ fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ background: 'var(--bg2)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--brd)' }}>
              <div style={{ color: 'var(--txm)', fontSize: '11px' }}>Storage Persistence</div>
              <div style={{ color: 'var(--sf)', fontWeight: 600, fontFamily: 'var(--fmono)', marginTop: '2px' }}>
                SQLite (app_config) + .env.app (disk)
              </div>
            </div>

            <div style={{ background: 'var(--bg2)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--brd)' }}>
              <div style={{ color: 'var(--txm)', fontSize: '11px' }}>Webhook HMAC-SHA256</div>
              <div style={{ color: 'var(--txh)', fontWeight: 600, fontFamily: 'var(--fmono)', marginTop: '2px' }}>
                Active &amp; Cryptographically Verified
              </div>
            </div>

            <a href="/install" target="_blank" rel="noreferrer" className="btn btn-outline" style={{ justifyContent: 'center', marginTop: '4px' }}>
              <span>Open 1-Click App Installer</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
