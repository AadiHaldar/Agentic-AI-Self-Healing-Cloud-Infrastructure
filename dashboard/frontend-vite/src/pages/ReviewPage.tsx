import React, { useState } from 'react';
import type { PRReviewRecord, ReviewFinding } from '../types';
import { FindingCard } from '../components/FindingCard';
import { GitPullRequest, RefreshCw, Code2 } from 'lucide-react';

interface ReviewPageProps {
  reviews: PRReviewRecord[];
  onRefresh: () => void;
  onDismissRule: (ruleId: string) => void;
}

export const ReviewPage: React.FC<ReviewPageProps> = ({ reviews, onRefresh, onDismissRule }) => {
  const [selectedReview, setSelectedReview] = useState<PRReviewRecord | null>(reviews[0] || null);

  const sampleFindings: ReviewFinding[] = [
    {
      file: 'detection/anomaly/isolation_forest.py',
      line: 83,
      rule_id: 'llm/repeated-fit',
      severity: 'warning',
      category: 'performance',
      message: 'IsolationForest.fit() called repeatedly inside predict iteration. Fit model once in __init__ for optimal throughput.',
      suggested_patch: '# Move model fitting to initialization block:\nself.model.fit(self.baseline_matrix)',
      llm_note: 'Affects inference latency by ~140ms per batch',
      confidence: 0.92
    },
    {
      file: 'agentic_engine/tools/k8s_tools.py',
      line: 42,
      rule_id: 'bandit/B602',
      severity: 'critical',
      category: 'security',
      message: 'Subprocess call with shell=True detected. Potential command injection vulnerability.',
      suggested_patch: '- subprocess.run(f"kubectl scale {svc}", shell=True)\n+ subprocess.run(["kubectl", "scale", svc], shell=False)',
      confidence: 1.0
    },
    {
      file: 'detection/anomaly/isolation_forest.py',
      line: 110,
      rule_id: 'test-gap/missing-unit-test',
      severity: 'info',
      category: 'testing',
      message: 'Public function `export_serialized_model()` has no corresponding unit test in tests/',
      confidence: 0.85
    }
  ];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--txh)', letterSpacing: '-0.02em' }}>
            Pull Request Reviews
          </h2>
          <p style={{ color: 'var(--txm)', fontSize: '12px', marginTop: '2px' }}>
            Real-time static analysis + Gemini LLM findings on incoming pull requests.
          </p>
        </div>

        <button className="btn btn-outline" onClick={onRefresh}>
          <RefreshCw size={13} />
          <span>Refresh PRs</span>
        </button>
      </div>

      <div className="two-col">
        {/* Left: PR List */}
        <div className="card-panel">
          <div className="card-header">
            <div className="card-title">
              <GitPullRequest size={15} color="var(--sf)" />
              <span>Review Log ({reviews.length})</span>
            </div>
          </div>

          <div className="card-body" style={{ padding: 0 }}>
            {reviews.length === 0 ? (
              <div className="empty-state">
                <GitPullRequest size={28} opacity={0.3} />
                <div>No Pull Requests logged yet. Open a PR to trigger automated analysis.</div>
              </div>
            ) : (
              reviews.map((r) => (
                <div
                  key={r.id}
                  onClick={() => setSelectedReview(r)}
                  style={{
                    padding: '14px 18px',
                    borderBottom: '1px solid var(--brd)',
                    cursor: 'pointer',
                    background: selectedReview?.id === r.id ? 'var(--bg2)' : 'transparent',
                    transition: 'background 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600, color: 'var(--txh)', fontFamily: 'var(--fmono)', fontSize: '12.5px' }}>
                      {r.repo_full_name} #{r.pr_number}
                    </span>
                    <span className={`pill ${r.critical_count > 0 ? 'pill-critical' : 'pill-success'}`}>
                      {r.critical_count > 0 ? `${r.critical_count} Critical` : 'Passed'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'var(--txm)' }}>
                    <span>{r.findings_count} total finding(s)</span>
                    <span>{r.reviewed_at}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Selected PR Findings */}
        <div className="card-panel">
          <div className="card-header">
            <div className="card-title">
              <Code2 size={15} color="var(--in)" />
              <span>Review Findings ({sampleFindings.length})</span>
            </div>
            <span className="pill pill-info" style={{ fontSize: '10px' }}>
              Gemini 2.0 Flash
            </span>
          </div>

          <div className="card-body">
            {sampleFindings.map((f, idx) => (
              <FindingCard
                key={idx}
                finding={f}
                onDismiss={onDismissRule}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
