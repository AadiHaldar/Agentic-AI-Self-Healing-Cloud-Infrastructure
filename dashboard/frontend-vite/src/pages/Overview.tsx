import { Activity, ArrowRight, GitPullRequest, Play } from 'lucide-react';
import { api } from '../api/client';
import { useApp } from '../lib/context';
import { fmtUptime, go, timeAgo, useRemote } from '../lib/hooks';
import { Topology } from '../components/Topology';
import { Card, CardHead, Empty, Notice, PageHead, Pill, Skeleton, Stat } from '../components/ui';

const LEFT_STEPS = [
  { r: 'review', n: 'L1', t: 'PR opened', d: 'GitHub webhook, HMAC-SHA256 verified' },
  { r: 'scanner', n: 'L2', t: 'Audit', d: 'Ruff · Bandit · OWASP · Gemini review' },
  { r: 'review', n: 'L3', t: 'Quality gate', d: 'Check run blocks merge on critical' },
  { r: 'autofix', n: 'L4', t: 'Auto-fix PR', d: 'Agent patches and re-audits' },
];
const RIGHT_STEPS = [
  { r: 'healing', n: 'R1', t: 'Detect', d: 'Isolation Forest on telemetry' },
  { r: 'healing', n: 'R2', t: 'Explain', d: 'KernelSHAP feature attribution' },
  { r: 'healing', n: 'R3', t: 'Decide', d: 'Q-learning RL and Gemini ReAct' },
  { r: 'healing', n: 'R4', t: 'Simulate', d: 'SimPy digital-twin gate' },
  { r: 'healing', n: 'R5', t: 'Act', d: 'kubectl scale / restart / patch' },
];

export function Overview() {
  const { status, meta, online } = useApp();
  const topo = useRemote(api.topology, [], 10_000);
  const reviews = useRemote(() => api.reviews(6), [], 15_000);
  const repos = useRemote(api.repos, [], 60_000);

  const critical = (reviews.data ?? []).reduce((a, r) => a + r.critical_count, 0);

  return (
    <>
      <PageHead
        title="AgentHeal"
        sub="One platform, two feedback loops: catch defects before they merge, and heal the running cluster when something still slips through."
        right={<button className="btn primary" onClick={() => go('healing', { scenario: 'deadlock' })}><Play size={14} fill="currentColor" />Run the live demo</button>}
      />

      {!online && (
        <div style={{ marginBottom: 16 }}>
          <Notice tone="bad">The backend API is not reachable, so live numbers are unavailable. Nothing on this page is substituted with placeholder data.</Notice>
        </div>
      )}

      <div className="grid g4">
        <Stat label="Cluster" value={status ? status.status.toLowerCase() : '—'} tone={status?.status === 'HEALTHY' ? 'ok' : status ? 'bad' : undefined}
          sub={status ? `${status.total_pods} services in the digital twin` : 'waiting for API'} />
        <Stat label="Active anomalies" value={status?.active_anomalies ?? '—'} tone={status && status.active_anomalies > 0 ? 'bad' : undefined}
          sub={status?.anomalous_pods.length ? status.anomalous_pods.join(', ') : 'no service above 80% CPU'} />
        <Stat label="PR reviews logged" value={reviews.data ? reviews.data.length : '—'}
          sub={meta?.demo_seed ? 'includes seeded demo rows' : `${critical} critical findings`} />
        <Stat label="Server uptime" value={meta ? fmtUptime(meta.uptime_seconds) : '—'} sub={meta ? `v${meta.version}` : undefined} />
      </div>

      <Card style={{ marginTop: 16 }}>
        <CardHead title="How the two loops fit together" right={<span className="tiny mute">click a step to open it</span>} />
        <div className="card-body stack" style={{ gap: 18 }}>
          <div>
            <div className="row" style={{ marginBottom: 8 }}><Pill tone="left" dot>Shift-left · before merge</Pill></div>
            <div className="flow">
              {LEFT_STEPS.map((s) => (
                <button key={s.n} className="flow-step" onClick={() => go(s.r)}>
                  <div className="n" style={{ color: 'var(--left)' }}>{s.n}</div><div className="t">{s.t}</div><div className="d">{s.d}</div>
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="row" style={{ marginBottom: 8 }}><Pill tone="right" dot>Shift-right · running cluster</Pill></div>
            <div className="flow">
              {RIGHT_STEPS.map((s) => (
                <button key={s.n} className="flow-step" onClick={() => go(s.r)}>
                  <div className="n" style={{ color: 'var(--right)' }}>{s.n}</div><div className="t">{s.t}</div><div className="d">{s.d}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <div className="grid g-split" style={{ marginTop: 16 }}>
        <Card>
          <CardHead icon={<Activity size={15} color="var(--right)" />} title="Live digital twin"
            right={<button className="btn sm ghost" onClick={() => go('healing')}>Open <ArrowRight size={12} /></button>} />
          <div className="card-body">
            {topo.data ? <Topology topology={topo.data} /> : topo.error ? <Notice tone="warn">Topology unavailable: {topo.error}</Notice> : <Skeleton h={120} />}
          </div>
        </Card>

        <Card>
          <CardHead icon={<GitPullRequest size={15} color="var(--left)" />} title="Recent PR reviews"
            right={meta?.demo_seed ? <Pill tone="warn">demo dataset</Pill> : <Pill tone="ok">live</Pill>} />
          <div className="card-body flush">
            {!reviews.data || reviews.data.length === 0
              ? <Empty>{reviews.error ? 'Review log unavailable.' : 'No reviews yet. Open a pull request on a connected repository.'}</Empty>
              : reviews.data.slice(0, 6).map((r) => (
                <div key={r.id} className="list-row" style={{ cursor: 'default' }}>
                  <div className="grow">
                    <div className="mono small trunc">{r.repo_full_name.split('/')[1]} <span className="mute">#{r.pr_number}</span></div>
                    <div className="tiny mute">{r.findings_count} finding(s) · {timeAgo(r.reviewed_at)}</div>
                  </div>
                  {r.critical_count > 0 ? <Pill tone="bad">{r.critical_count} critical</Pill> : <Pill tone="ok">clean</Pill>}
                </div>
              ))}
          </div>
        </Card>
      </div>

      <Card style={{ marginTop: 16 }}>
        <CardHead title="Connected repositories" />
        <div className="card-body">
          {!repos.data || repos.data.length === 0
            ? <span className="dim small">None yet. Install the GitHub App from the System page.</span>
            : <div className="row wrap">{repos.data.map((r) => <Pill key={r.repo_full_name} tone="mute">{r.repo_full_name}</Pill>)}</div>}
        </div>
      </Card>
    </>
  );
}
