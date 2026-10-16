import { useEffect, useMemo, useState } from 'react';
import {
  Activity, GitPullRequest, LayoutDashboard, Moon, ScanSearch, Server, ShieldCheck, Sun, Wrench,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { api, DEFAULT_REPO } from './api/client';
import { AppCtx } from './lib/context';
import { useHashRoute, useRemote } from './lib/hooks';
import { Pill } from './components/ui';
import { Overview } from './pages/Overview';
import { Review } from './pages/Review';
import { Scanner } from './pages/Scanner';
import { AutoFix } from './pages/AutoFix';
import { Healing } from './pages/Healing';
import { System } from './pages/System';

const NAV: { id: string; label: string; icon: ReactNode; group: string; accent?: string }[] = [
  { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={16} />, group: '' },
  { id: 'review', label: 'PR Review', icon: <GitPullRequest size={16} />, group: 'left', accent: 'var(--left)' },
  { id: 'scanner', label: 'Security Scanner', icon: <ScanSearch size={16} />, group: 'left', accent: 'var(--left)' },
  { id: 'autofix', label: 'Auto-Fix', icon: <Wrench size={16} />, group: 'left', accent: 'var(--left)' },
  { id: 'healing', label: 'Self-Healing', icon: <Activity size={16} />, group: 'right', accent: 'var(--right)' },
  { id: 'system', label: 'System', icon: <Server size={16} />, group: 'sys' },
];

const TITLES: Record<string, string> = {
  overview: 'Overview', review: 'PR Review', scanner: 'Security Scanner',
  autofix: 'Auto-Fix', healing: 'Self-Healing', system: 'System',
};

function readTheme(): 'dark' | 'light' {
  try {
    const t = localStorage.getItem('agentheal-theme');
    if (t === 'light' || t === 'dark') return t;
  } catch { /* storage blocked */ }
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export default function App() {
  const { route, params } = useHashRoute();
  const [theme, setTheme] = useState<'dark' | 'light'>(readTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('agentheal-theme', theme); } catch { /* ignore */ }
  }, [theme]);

  const metaQ = useRemote(api.meta, [], 30_000);
  const statusQ = useRemote(api.status, [], 8_000);
  const reposQ = useRemote(api.repos, [], 60_000);

  const online = !statusQ.error && !!statusQ.data;
  const repo = reposQ.data?.find((r) => r.repo_full_name.includes('Self-Healing'))?.repo_full_name ?? DEFAULT_REPO;

  const ctx = useMemo(
    () => ({ meta: metaQ.data, status: statusQ.data, online, repo, refreshStatus: statusQ.reload }),
    [metaQ.data, statusQ.data, online, repo, statusQ.reload],
  );

  const active = NAV.some((n) => n.id === route) ? route : 'overview';

  useEffect(() => { document.title = `${TITLES[active]} · AgentHeal`; }, [active]);

  let page: ReactNode;
  switch (active) {
    case 'review': page = <Review />; break;
    case 'scanner': page = <Scanner />; break;
    case 'autofix': page = <AutoFix />; break;
    case 'healing': page = <Healing scenario={params.get('scenario') ?? undefined} />; break;
    case 'system': page = <System />; break;
    default: page = <Overview />;
  }

  const m = metaQ.data;

  return (
    <AppCtx.Provider value={ctx}>
      <div className="shell">
        <aside className="side">
          <div className="brand">
            <div className="brand-mark"><ShieldCheck size={18} strokeWidth={2.4} /></div>
            <div>
              <div className="brand-name">AgentHeal</div>
              <div className="brand-sub">Review · Secure · Self-heal</div>
            </div>
          </div>
          <nav className="nav" aria-label="Primary">
            {NAV.map((n, i) => (
              <div key={n.id}>
                {n.group !== (NAV[i - 1]?.group ?? '__') && n.group === 'left' && (
                  <div className="nav-label"><span className="nav-dot" style={{ background: 'var(--left)' }} />Shift-left · code</div>
                )}
                {n.group !== (NAV[i - 1]?.group ?? '__') && n.group === 'right' && (
                  <div className="nav-label"><span className="nav-dot" style={{ background: 'var(--right)' }} />Shift-right · cluster</div>
                )}
                {n.group !== (NAV[i - 1]?.group ?? '__') && n.group === 'sys' && (
                  <div className="nav-label">Platform</div>
                )}
                <a href={`#/${n.id}`} className={active === n.id ? 'active' : ''}
                  style={{ ['--accent' as string]: n.accent }} aria-current={active === n.id ? 'page' : undefined}>
                  {n.icon}<span>{n.label}</span>
                </a>
              </div>
            ))}
          </nav>
          <div className="side-foot">
            <div>v{m?.version ?? '—'}</div>
            <button className="theme-btn" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              aria-label="Toggle colour theme">
              {theme === 'dark' ? <Sun size={13} /> : <Moon size={13} />}
              {theme === 'dark' ? 'Light theme' : 'Dark theme'}
            </button>
          </div>
        </aside>

        <div className="main">
          <div className="topbar">
            <strong style={{ fontSize: 14 }}>{TITLES[active]}</strong>
            <span className="grow" />
            {online
              ? <Pill tone="ok" dot pulse>API online</Pill>
              : <Pill tone="bad" dot>{statusQ.loading ? 'connecting…' : 'API offline'}</Pill>}
            {m && (
              <>
                <Pill tone={m.gemini_configured ? 'info' : 'warn'}>{m.gemini_configured ? 'Gemini connected' : 'Gemini: no key'}</Pill>
                <Pill tone={m.cluster_reachable ? 'ok' : 'mute'}>{m.cluster_reachable ? `cluster: ${m.kube_context ?? 'connected'}` : m.kubectl_available ? 'no cluster (dry-run)' : 'kubectl missing (dry-run)'}</Pill>
                {m.demo_seed && <Pill tone="warn">demo dataset</Pill>}
              </>
            )}
            {statusQ.data && (
              <Pill tone={statusQ.data.status === 'HEALTHY' ? 'ok' : 'bad'}>
                cluster {statusQ.data.status.toLowerCase()}
              </Pill>
            )}
          </div>
          <main className="page" id="content">{page}</main>
        </div>
      </div>
    </AppCtx.Provider>
  );
}
