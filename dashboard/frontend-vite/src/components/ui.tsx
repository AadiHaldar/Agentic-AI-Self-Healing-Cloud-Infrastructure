import type { ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, Info, Inbox, Loader2, XCircle } from 'lucide-react';

type Tone = 'ok' | 'bad' | 'warn' | 'info' | 'left' | 'right' | 'mute';

export function Pill({ tone = 'mute', children, dot, pulse }: { tone?: Tone; children: ReactNode; dot?: boolean; pulse?: boolean }) {
  return (
    <span className={`pill ${tone}${pulse ? ' pulse' : ''}`}>
      {dot && <span className="dot" />}
      {children}
    </span>
  );
}

export function Card({ children, className = '', style }: { children: ReactNode; className?: string; style?: React.CSSProperties }) {
  return <section className={`card ${className}`} style={style}>{children}</section>;
}

export function CardHead({ icon, title, right, accent }: { icon?: ReactNode; title: ReactNode; right?: ReactNode; accent?: string }) {
  return (
    <header className="card-head">
      <h3 style={accent ? { color: accent } : undefined}>{icon}<span style={{ color: 'var(--tx)' }}>{title}</span></h3>
      <span className="grow" />
      {right}
    </header>
  );
}

export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: 'ok' | 'bad' | 'warn' }) {
  const color = tone === 'ok' ? 'var(--ok)' : tone === 'bad' ? 'var(--bad)' : tone === 'warn' ? 'var(--warn)' : undefined;
  return (
    <Card className="stat">
      <div className="label">{label}</div>
      <div className="v" style={{ color }}>{value}</div>
      {sub && <div className="s">{sub}</div>}
    </Card>
  );
}

export function PageHead({ title, sub, right }: { title: string; sub?: ReactNode; right?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {sub && <p>{sub}</p>}
      </div>
      <span className="grow" />
      {right}
    </div>
  );
}

export function Notice({ tone = 'info', children }: { tone?: 'info' | 'warn' | 'bad' | 'ok'; children: ReactNode }) {
  const Icon = tone === 'bad' ? XCircle : tone === 'warn' ? AlertTriangle : tone === 'ok' ? CheckCircle2 : Info;
  const color = tone === 'bad' ? 'var(--bad)' : tone === 'warn' ? 'var(--warn)' : tone === 'ok' ? 'var(--ok)' : 'var(--info)';
  return (
    <div className={`notice ${tone === 'info' ? '' : tone}`} role={tone === 'bad' ? 'alert' : undefined}>
      <Icon size={16} color={color} />
      <div>{children}</div>
    </div>
  );
}

export function Empty({ children, icon }: { children: ReactNode; icon?: ReactNode }) {
  return <div className="empty">{icon ?? <Inbox size={26} />}<div>{children}</div></div>;
}

export function Spinner({ size = 14 }: { size?: number }) {
  return <Loader2 size={size} className="spin" aria-label="Loading" />;
}

export function Skeleton({ h = 14, w = '100%' }: { h?: number; w?: number | string }) {
  return <div className="skeleton" style={{ height: h, width: w }} />;
}

export function Bar({ value, color = 'var(--right)' }: { value: number; color?: string }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return <div className="bar"><i style={{ width: `${pct}%`, background: color }} /></div>;
}

export function loadColor(v: number): string {
  return v >= 0.8 ? 'var(--bad)' : v >= 0.6 ? 'var(--warn)' : 'var(--ok)';
}

export function SeverityPill({ severity }: { severity: string }) {
  const tone: Tone = severity === 'critical' ? 'bad' : severity === 'high' ? 'warn' : severity === 'medium' ? 'info' : 'mute';
  return <Pill tone={tone}>{severity}</Pill>;
}

export function GatePill({ conclusion }: { conclusion: string | null | undefined }) {
  if (!conclusion) return <Pill tone="mute">no gate run</Pill>;
  if (conclusion === 'success') return <Pill tone="ok" dot>gate passed</Pill>;
  if (conclusion === 'failure') return <Pill tone="bad" dot>gate blocked</Pill>;
  return <Pill tone="warn">{conclusion}</Pill>;
}
