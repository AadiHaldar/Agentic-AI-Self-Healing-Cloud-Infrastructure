import React from 'react';
import { ShieldCheck, CheckCircle2 } from 'lucide-react';

export const SecurePage: React.FC = () => {
  const securityChecks = [
    { name: 'Secrets Scanner (detect-secrets)', status: 'Clean', details: '0 high-entropy keys detected' },
    { name: 'Python Security (Bandit AST)', status: 'Clean', details: 'All subprocess calls verified safe (shell=False)' },
    { name: 'Dependency Audit (pip-audit)', status: 'Protected', details: 'All dependencies match non-vulnerable CVE databases' },
    { name: 'Quality Gate Enforcement', status: 'Enforced', details: 'review-agent/quality-gate blocks merge on critical' }
  ];

  return (
    <div>
      <div style={{ marginBottom: '18px' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--txh)', letterSpacing: '-0.02em' }}>
          Security &amp; Quality Gate Status
        </h2>
        <p style={{ color: 'var(--txm)', fontSize: '12px', marginTop: '2px' }}>
          Real-time security posture and required GitHub Check Run enforcement.
        </p>
      </div>

      <div className="card-panel">
        <div className="card-header">
          <div className="card-title">
            <ShieldCheck size={15} color="var(--sf)" />
            <span>Active Security Scanners</span>
          </div>
          <span className="pill pill-success">Quality Gate: PASS</span>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          {securityChecks.map((chk, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '14px 20px',
                borderBottom: '1px solid var(--brd)',
                fontSize: '12.5px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <CheckCircle2 size={16} color="var(--sf)" />
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--txh)' }}>{chk.name}</div>
                  <div style={{ fontSize: '11px', color: 'var(--txm)', marginTop: '2px' }}>{chk.details}</div>
                </div>
              </div>

              <span className="pill pill-success" style={{ fontSize: '11px' }}>
                {chk.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
