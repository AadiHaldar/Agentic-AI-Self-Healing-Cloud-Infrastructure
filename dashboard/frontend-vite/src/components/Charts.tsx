/** SHAP contribution bars (diverging around zero) and the OWASP compliance ring. */

export function ShapBars({ scores }: { scores: Record<string, number> }) {
  const entries = Object.entries(scores);
  const max = Math.max(0.0001, ...entries.map(([, v]) => Math.abs(v)));
  const sorted = [...entries].sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  return (
    <div>
      {sorted.map(([k, v]) => {
        const w = (Math.abs(v) / max) * 50;
        const positive = v >= 0;
        return (
          <div className="shap-row" key={k}>
            <span className="mono trunc" title={k}>{k}</span>
            <div className="shap-track" role="img" aria-label={`${k} contribution ${v.toFixed(3)}`}>
              <span className="shap-mid" />
              <i style={{
                width: `${w}%`,
                left: positive ? '50%' : `${50 - w}%`,
                background: positive ? 'var(--bad)' : 'var(--info)',
              }} />
            </div>
            <span className="mono small dim" style={{ textAlign: 'right' }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}</span>
          </div>
        );
      })}
      <div className="tiny mute" style={{ marginTop: 8, display: 'flex', gap: 14 }}>
        <span><span style={{ color: 'var(--bad)' }}>■</span> pushes toward anomaly</span>
        <span><span style={{ color: 'var(--info)' }}>■</span> pushes toward normal</span>
      </div>
    </div>
  );
}

export function ScoreRing({ score, grade }: { score: number; grade: string }) {
  const r = 54, c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const color = score >= 85 ? 'var(--ok)' : score >= 60 ? 'var(--warn)' : 'var(--bad)';
  return (
    <div className="score-ring" role="img" aria-label={`Compliance score ${score.toFixed(0)} percent, grade ${grade}`}>
      <svg viewBox="0 0 132 132" width="132" height="132">
        <circle cx="66" cy="66" r={r} fill="none" stroke="var(--line)" strokeWidth="10" />
        <circle cx="66" cy="66" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={`${c * pct} ${c}`} transform="rotate(-90 66 66)" style={{ transition: 'stroke-dasharray .8s ease' }} />
      </svg>
      <div className="center">
        <div>
          <div className="grade" style={{ color }}>{grade}</div>
          <div className="tiny mute">{score.toFixed(0)}%</div>
        </div>
      </div>
    </div>
  );
}
