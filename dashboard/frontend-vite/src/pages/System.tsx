import { useState } from 'react';
import { ExternalLink, Plus, Server, Shield } from 'lucide-react';
import { api } from '../api/client';
import { useApp } from '../lib/context';
import { fmtUptime, useRemote } from '../lib/hooks';
import { Card, CardHead, Notice, PageHead, Pill } from '../components/ui';

const yn = (v: boolean | undefined, yes = 'yes', no = 'no') =>
  v === undefined ? <Pill tone="mute">…</Pill> : <Pill tone={v ? 'ok' : 'warn'}>{v ? yes : no}</Pill>;

export function System() {
  const { meta, online, repo } = useApp();
  const repos = useRemote(api.repos, [], 60_000);
  const health = useRemote(api.serviceHealth, [], 10_000);

  const [selRepo, setSelRepo] = useState('');
  const [rule, setRule] = useState('ruff/E501');
  const [msg, setMsg] = useState<string | null>(null);
  const target = selRepo || repo;

  const dismiss = async () => {
    try {
      await api.dismissRule(target, rule, 'Suppressed from console');
      setMsg(`Rule ${rule} will be suppressed in future reviews of ${target}.`);
    } catch (e) { setMsg(`Error: ${e instanceof Error ? e.message : String(e)}`); }
  };

  return (
    <>
      <PageHead title="System" sub="What this deployment is, and what is actually wired up. Read from the server, not assumed." />

      <div className="grid g2">
        <Card>
          <CardHead icon={<Server size={15} />} title="Deployment" right={online ? <Pill tone="ok" dot>online</Pill> : <Pill tone="bad" dot>offline</Pill>} />
          <div className="card-body">
            <dl className="kv">
              <dt>Version</dt><dd className="mono">{meta?.version ?? '—'}</dd>
              <dt>Uptime</dt><dd>{meta ? fmtUptime(meta.uptime_seconds) : '—'}</dd>
              <dt>Anomaly model trained</dt><dd>{yn(meta?.detector_trained)}</dd>
              <dt>Gemini API connected</dt><dd>{yn(meta?.gemini_configured, 'yes', 'no key')}</dd>
              <dt>kubectl installed</dt><dd>{yn(meta?.kubectl_available)}</dd>
              <dt>Cluster reachable</dt><dd>{yn(meta?.cluster_reachable, meta?.kube_context ?? 'yes', 'no (dry-run only)')}</dd>
              <dt>Target namespace</dt><dd className="mono">{meta?.k8s_namespace ?? '—'}</dd>
              <dt>PR-review webhook mounted</dt><dd>{yn(meta?.github_pr_review_mounted)}</dd>
              <dt>Seeded demo data</dt><dd>{yn(meta ? !meta.demo_seed : undefined, 'off', 'on')}</dd>
            </dl>
          </div>
        </Card>

        <Card>
          <CardHead title="Webhook pipeline counters" right={health.error ? <Pill tone="warn">unavailable</Pill> : <Pill tone="info">since boot</Pill>} />
          <div className="card-body">
            {health.error ? <Notice tone="warn">/api/service-health is not available on this deployment ({health.error}). The PR-review router may not be mounted.</Notice> : !health.data ? <span className="mute">Loading…</span> : (
              <dl className="kv">
                {Object.entries(health.data.counters).map(([k, v]) => (<><dt key={`k${k}`} className="mono small">{k}</dt><dd key={`v${k}`} className="mono">{v}</dd></>))}
                <dt>Pipeline success rate</dt><dd>{health.data.pipeline_success_rate == null ? 'n/a (no runs yet)' : `${(health.data.pipeline_success_rate * 100).toFixed(0)}%`}</dd>
              </dl>
            )}
          </div>
        </Card>
      </div>

      <div className="grid g2" style={{ marginTop: 16 }}>
        <Card>
          <CardHead icon={<Shield size={15} />} title="GitHub App" />
          <div className="card-body stack" style={{ gap: 12 }}>
            {!repos.data || repos.data.length === 0 ? <Notice tone="warn">No repositories are connected yet.</Notice> : (
              <div className="row wrap">{repos.data.map((r) => <Pill key={r.repo_full_name} tone="mute">{r.repo_full_name}</Pill>)}</div>
            )}
            <a className="btn" href="/install" target="_blank" rel="noreferrer">Open one-click installer <ExternalLink size={13} /></a>
            <p className="tiny mute">Webhook endpoint: <code>/webhooks/github</code> (HMAC-SHA256, constant-time compare, delivery-ID de-duplication, per-installation rate limit).</p>
          </div>
        </Card>

        <Card>
          <CardHead title="Suppress a rule" />
          <div className="card-body stack" style={{ gap: 12 }}>
            <label className="field"><span>Repository</span>
              <select value={target} onChange={(e) => setSelRepo(e.target.value)}>
                {[...new Set([repo, ...(repos.data?.map((r) => r.repo_full_name) ?? [])])].map((r) => <option key={r}>{r}</option>)}
              </select>
            </label>
            <label className="field"><span>Rule id (e.g. ruff/E501, bandit/B101)</span>
              <input type="text" value={rule} onChange={(e) => setRule(e.target.value)} />
            </label>
            <button className="btn" onClick={dismiss}><Plus size={14} />Add suppression</button>
            {msg && <Notice>{msg}</Notice>}
          </div>
        </Card>
      </div>
    </>
  );
}
