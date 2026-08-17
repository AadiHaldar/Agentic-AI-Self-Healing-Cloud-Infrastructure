import React from 'react';
import type { ReviewFinding } from '../types';
import { ShieldAlert, AlertTriangle, Info } from 'lucide-react';

interface FindingCardProps {
  finding: ReviewFinding;
  onDismiss?: (ruleId: string) => void;
}

export const FindingCard: React.FC<FindingCardProps> = ({ finding, onDismiss }) => {
  const getSeverityPill = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return <span className="pill pill-critical"><ShieldAlert size={12} /> CRITICAL</span>;
      case 'error':
        return <span className="pill pill-critical"><AlertTriangle size={12} /> ERROR</span>;
      case 'warning':
        return <span className="pill pill-warning"><AlertTriangle size={12} /> WARNING</span>;
      default:
        return <span className="pill pill-info"><Info size={12} /> INFO</span>;
    }
  };

  return (
    <div
      style={{
        background: 'var(--bg2)',
        border: '1px solid var(--brd)',
        borderRadius: 'var(--rmd)',
        padding: '14px 16px',
        marginBottom: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {getSeverityPill(finding.severity)}
          <span style={{ fontFamily: 'var(--fmono)', fontSize: '11.5px', color: 'var(--txh)', fontWeight: 600 }}>
            {finding.file}:{finding.line}
          </span>
          <span style={{ fontFamily: 'var(--fmono)', fontSize: '10.5px', color: 'var(--txm)', background: 'var(--bg3)', padding: '1px 6px', borderRadius: '4px' }}>
            {finding.rule_id}
          </span>
        </div>

        {onDismiss && (
          <button
            className="btn btn-outline btn-sm"
            onClick={() => onDismiss(finding.rule_id)}
            title="Dismiss rule for this repo"
          >
            Dismiss Rule
          </button>
        )}
      </div>

      <div style={{ fontSize: '12.5px', color: 'var(--txh)', lineHeight: 1.5 }}>
        {finding.message}
      </div>

      {finding.llm_note && (
        <div style={{ fontSize: '11.5px', color: 'var(--in)', background: 'var(--ind)', padding: '6px 10px', borderRadius: '6px' }}>
          <strong>LLM Note:</strong> {finding.llm_note}
        </div>
      )}

      {finding.suggested_patch && (
        <div style={{ marginTop: '4px' }}>
          <div style={{ fontSize: '10.5px', fontWeight: 600, color: 'var(--sf)', textTransform: 'uppercase', marginBottom: '4px', letterSpacing: '0.05em' }}>
            Suggested Fix
          </div>
          <div className="diff-box">
            <span className="diff-add">{finding.suggested_patch}</span>
          </div>
        </div>
      )}
    </div>
  );
};
