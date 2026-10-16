import { useEffect, useState } from 'react';
import { ExternalLink, GitPullRequest, MessageSquare, RefreshCw } from 'lucide-react';
import { api, github, GATE_CHECK_NAME } from '../api/client';
import { useApp } from '../lib/context';
import { timeAgo, useRemote } from '../lib/hooks';
import type { GhCheckRun, GhComment, GhPull } from '../types';
import { Card, CardHead, Empty, GatePill, Notice, PageHead, Pill, Skeleton, Spinner } from '../components/ui';

function useGates(repo: string, pulls: GhPull[] | null) {
  const [gates, setGates] = useState<Record<number, GhCheckRun | null>>({});
  useEffect(() => {
    if (!pulls) return;
    let alive = true;
    Promise.allSettled(pulls.slice(0, 8).map((p) => github.checks(repo, p.head.sha))).then((rs) => {
      if (!alive) return;
      const next: Record<number, GhCheckRun | null> = {};
      rs.forEach((r, i) => {
        const run = r.status === 'fulfilled' ? r.value.find((c) => c.name === GATE_CHECK_NAME) ?? null : null;
        next[pulls[i].number] = run;
      });
      setGates(next);
    });
    return () => { alive = false; };
  }, [repo, pulls]);
  return gates;
}

function BotComment({ c }: { c: GhComment }) {
  const [open, setOpen] = useState(false);
  const long = c.body.length > 1400;
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="row small mute" style={{ marginBottom: 6 }}>
        <MessageSquare size={13} /><strong style={{ color: 'var(--tx-dim)' }}>{c.user.login}</strong>
        <span>{timeAgo(c.created_at)}</span><span className="grow" />
        <a href={c.html_url} target="_blank" rel="noreferrer">open <ExternalLink size={11} style={{ verticalAlign: -1 }} /></a>
      </div>
      <pre className="block">{open || !long ? c.body : `${c.body.slice(0, 1400)}…`}</pre>
      {long && <button className="btn sm ghost" style={{ marginTop: 6 }} onClick={() => setOpen(!open)}>{open ? 'Collapse' : 'Show full comment'}</button>}
    </div>
  );
}

export function Review() {
  const { repo, meta } = useApp();
  const pulls = useRemote(() => github.pulls(repo), [repo]);
  const log = useRemote(() => api.reviews(50), [], 15_000);
  const gates = useGates(repo, pulls.data);
  const [sel, setSel] = useState<number | null>(null);

  const list = pulls.data ?? [];
  const current = list.find((p) => p.number === sel) ?? list[0] ?? null;

  const comments = useRemote(
    () => (current ? Promise.all([github.issueComments(repo, current.number), github.reviewComments(repo, current.number)]) : Promise.resolve([[], []] as [GhComment[], GhComment[]])),
    [repo, current?.number],
  );
  const [issue, inline] = comments.data ?? [[], []];
  const gate = current ? gates[current.number] : undefined;

  return (
    <>
      <PageHead
        title="PR Review"
        sub="Pull requests on the connected repository, with the real quality-gate result and the review the bot posted. Read live from GitHub, not from seeded data."
        right={<><Pill tone="left" dot>shift-left</Pill><button className="btn sm" onClick={() => { pulls.reload(); comments.reload(); }}><RefreshCw size={13} />Refresh</button></>}
      />

      {pulls.error && (
        <div style={{ marginBottom: 16 }}>
          <Notice tone="warn">Could not load pull requests from GitHub ({pulls.error}). The server-side review log below is still available.</Notice>
        </div>
      )}

      <div className="grid g-split">
        <Card>
          <CardHead icon={<GitPullRequest size={15} color="var(--left)" />} title={`Pull requests${pulls.data ? ` (${list.length})` : ''}`}
            right={<span className="mono tiny mute">{repo}</span>} />
          <div className="card-body flush">
            {pulls.loading && !pulls.data ? <div style={{ padding: 18 }} className="stack"><Skeleton h={38} /><Skeleton h={38} /><Skeleton h={38} /></div>
              : list.length === 0 ? <Empty>No pull requests found.</Empty>
              : list.map((p) => (
                <button key={p.number} className={`list-row${current?.number === p.number ? ' sel' : ''}`} onClick={() => setSel(p.number)}>
                  <div className="grow" style={{ minWidth: 0 }}>
                    <div className="row">
                      <span className="mono small mute">#{p.number}</span>
                      <span className="trunc" style={{ fontWeight: 600 }}>{p.title}</span>
                    </div>
                    <div className="tiny mute trunc" style={{ marginTop: 2 }}>{p.head.ref} → {p.base.ref} · {p.user.login} · {timeAgo(p.created_at)}</div>
                  </div>
                  {gates[p.number] !== undefined
                    ? <GatePill conclusion={gates[p.number]?.conclusion} />
                    : <Spinner size={12} />}
                  <Pill tone={p.merged_at ? 'left' : p.state === 'open' ? 'ok' : 'mute'}>{p.merged_at ? 'merged' : p.state}</Pill>
                </button>
              ))}
          </div>
        </Card>

        <div className="stack">
          <Card>
            <CardHead title={current ? `#${current.number} · ${current.title}` : 'Details'}
              right={current ? <a className="btn sm" href={current.html_url} target="_blank" rel="noreferrer">GitHub <ExternalLink size={12} /></a> : undefined} />
            <div className="card-body stack" style={{ gap: 14 }}>
              {!current ? <Empty>Select a pull request.</Empty> : (
                <>
                  <div className="row wrap">
                    <GatePill conclusion={gate?.conclusion} />
                    <span className="tiny mute mono">{current.head.sha.slice(0, 7)}</span>
                    <span className="tiny mute">{current.head.ref}</span>
                  </div>
                  {gate?.output?.title && (
                    <div>
                      <div className="label">Quality gate</div>
                      <div style={{ marginTop: 4, fontWeight: 600 }}>{gate.output.title}</div>
                      {gate.output.summary && <pre className="block" style={{ marginTop: 6, maxHeight: 180 }}>{gate.output.summary}</pre>}
                    </div>
                  )}
                  <div className="row small dim"><MessageSquare size={14} />{issue.length} summary comment(s), {inline.length} inline comment(s)</div>
                </>
              )}
            </div>
          </Card>

          <Card>
            <CardHead title="Bot review" right={comments.loading ? <Spinner size={12} /> : undefined} />
            <div className="card-body">
              {comments.error ? <Notice tone="warn">{comments.error}</Notice>
                : issue.length === 0 && inline.length === 0 ? <Empty icon={<MessageSquare size={24} />}>The bot has not commented on this pull request.</Empty>
                : <>
                  {issue.map((c) => <BotComment key={c.id} c={c} />)}
                  {inline.length > 0 && <div className="label" style={{ margin: '14px 0 8px' }}>Inline comments</div>}
                  {inline.slice(0, 8).map((c) => (
                    <div key={c.id} style={{ marginBottom: 10 }}>
                      <div className="mono tiny mute">{c.path}{c.line ? `:${c.line}` : ''} · {c.user.login}</div>
                      <pre className="block" style={{ marginTop: 4, maxHeight: 140 }}>{c.body}</pre>
                    </div>
                  ))}
                </>}
            </div>
          </Card>
        </div>
      </div>

      <Card style={{ marginTop: 16 }}>
        <CardHead title="Server-side review log" right={meta?.demo_seed ? <Pill tone="warn">includes seeded demo rows</Pill> : <Pill tone="ok">live webhook data</Pill>} />
        <div className="card-body flush" style={{ overflowX: 'auto' }}>
          {!log.data || log.data.length === 0 ? <Empty>{log.error ? `Review log unavailable (${log.error}).` : 'No reviews recorded by the webhook yet.'}</Empty> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
              <thead><tr className="label" style={{ textAlign: 'left' }}>
                {['Repository', 'PR', 'Findings', 'Critical', 'Status', 'Reviewed'].map((h) => <th key={h} style={{ padding: '10px 18px', fontWeight: 600 }}>{h}</th>)}
              </tr></thead>
              <tbody>
                {log.data.map((r) => (
                  <tr key={r.id} style={{ borderTop: '1px solid var(--line)' }}>
                    <td className="mono" style={{ padding: '9px 18px' }}>{r.repo_full_name}</td>
                    <td style={{ padding: '9px 18px' }}>#{r.pr_number}</td>
                    <td style={{ padding: '9px 18px' }}>{r.findings_count}</td>
                    <td style={{ padding: '9px 18px' }}>{r.critical_count > 0 ? <Pill tone="bad">{r.critical_count}</Pill> : 0}</td>
                    <td style={{ padding: '9px 18px' }}><Pill tone={r.status.includes('pass') || r.status === 'success' ? 'ok' : 'bad'}>{r.status.replace('_', ' ')}</Pill></td>
                    <td className="mute" style={{ padding: '9px 18px' }}>{timeAgo(r.reviewed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </>
  );
}
