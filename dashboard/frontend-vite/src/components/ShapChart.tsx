import React from 'react';

interface ShapChartProps {
  scores?: Record<string, number>;
}

export const ShapChart: React.FC<ShapChartProps> = ({ scores }) => {
  if (!scores || Object.keys(scores).length === 0) {
    return (
      <div className="empty-state" style={{ padding: '16px' }}>
        No feature attribution scores available. Inject an alert to evaluate SHAP importance.
      </div>
    );
  }

  const entries = Object.entries(scores);
  const maxAbs = Math.max(...entries.map(([_, v]) => Math.abs(v)), 0.01);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
      {entries.map(([feature, val]) => {
        const percent = Math.min(100, Math.round((Math.abs(val) / maxAbs) * 100));
        const isPositive = val >= 0;

        return (
          <div
            key={feature}
            style={{
              display: 'grid',
              gridTemplateColumns: '130px 1fr 60px',
              alignItems: 'center',
              gap: '10px',
              fontFamily: 'var(--fmono)',
              fontSize: '11.5px'
            }}
          >
            <div style={{ color: 'var(--txm)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {feature}
            </div>

            <div style={{ background: 'var(--bg3)', height: '10px', borderRadius: '3px', position: 'relative', overflow: 'hidden' }}>
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  bottom: 0,
                  left: 0,
                  width: `${percent}%`,
                  background: isPositive ? 'var(--in)' : 'var(--em)',
                  borderRadius: '3px',
                  transition: 'width 0.4s ease'
                }}
              />
            </div>

            <div style={{ textAlign: 'right', color: isPositive ? 'var(--in)' : 'var(--em)', fontWeight: 600 }}>
              {val > 0 ? `+${val.toFixed(2)}` : val.toFixed(2)}
            </div>
          </div>
        );
      })}
    </div>
  );
};
