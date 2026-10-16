import { useEffect, useState } from 'react';
import { ArrowRight, ExternalLink, GitBranch, Wrench } from 'lucide-react';
import { github, GATE_CHECK_NAME } from '../api/client';
import { useApp } from '../lib/context';
import { timeAgo, useRemote } from '../lib/hooks';
import type { GhCheckRun, GhPull } from '../types';
import { Card, CardHead, Empty, GatePill, Notice, PageHead, Pill, Skeleton } from '../components/ui';

const isAutoFix = (p: GhPull) => /^(autoreview|autofix|auto-fix)/i.test(p.head.ref) || /auto.?fix/i.test(p.title);

interface Enriched { pr: GhPull; gate: GhCheckRun | null }

export function AutoFix() {
  const { repo } = useApp();
  const pulls = useRemote(() => github.pulls(repo), [repo]);
  const [rows, setRows] = useState<Enriched[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const fixes = (pulls.data ?? []).filter(isAutoFix);
  const all = pulls.data ?? [];

  useEffect(() => {
    if (!pulls.data) return;
    let alive = true;
    const wanted = pulls.data.filter(isAutoFix).slice(0, 8);
    Promise.all(wanted.map(async (p) => {
      const [detail, checks] = await Promise.all([github.pull(repo, p.number), github.checks(repo, p.head.sha)]);
      return { pr: detail, gate: checks.find((c) => c.name === GATE_CHECK_NAME) ?? null } as Enriched;
    }))
      .then((r) => { if (alive) { setRows(r); setErr(null); } })
      .catch((e: unknown) => { if (alive) setErr(e instanceof Error ? e.message : String(e)); });
    return () => { alive = false; };
  }, [repo, pulls.data]);

  // Find the PR this fix most likely repairs: the closest earlier non-fix PR.
  const sourceOf = (fix: GhPull): GhPull | undefined =>
    all.filter((p) => !isAutoFix(p) && p.number < fix.number).sort((a, b) => b.number - a.number)[0];

  return (
    <>
      <PageHead
        title="Auto-Fix"
        sub="When the quality gate blocks a pull request, the agent opens a separate fix branch and PR. Shown here from the real repository."
        right={<Pill tone="left" dot>shift-left</Pill>}
      />

      <Card>
        <CardHead icon={<Wrench size={15} color="var(--left)" />} title="How it works" />
        <div className="card-body">
          <div className="flow">
            {[
              ['1', 'PR opened', 'Webhook fires; HMAC verified'],
              ['2', 'Audit', 'Ruff, Bandit, OWASP, Gemini review'],
              ['3', 'Gate blocks', 'Critical finding → check run fails'],
              ['4', 'Fix branch', 'Agent patches code on autoreview/…'],
              ['5', 'Fix PR', 'Re-audited; gate passes → mergeable'],
            ].map(([n, t, d]) => (
              <div className="flow-step" key={n} style={{ cursor: 'default' }}>
                <div className="n" style={{ color: 'var(--left)' }}>STEP {n}</div>
                <div className="t">{t}</div>
                <div className="d">{d}</div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      <div style={{ marginTop: 16 }}>
        {pulls.error && <Notice tone="warn">Could not load pull requests from GitHub ({pulls.error}).</Notice>}
        {err && <Notice tone="warn">{err}</Notice>}
      </div>

      <div className="stack" style={{ marginTop: 16 }}>
        {pulls.loading && !pulls.data ? <Card><div className="card-body stack"><Skeleton h={60} /><Skeleton h={60} /></div></Card>
          : fixes.length === 0 ? <Card><Empty icon={<GitBranch size={26} />}>No auto-fix pull requests found in this repository.</Empty></Card>
          : (rows ?? fixes.map((pr) => ({ pr, gate: undefined as unknown as GhCheckRun | null }))).map(({ pr, gate }) => {
            const src = sourceOf(pr);
            return (
              <Card key={pr.number}>
                <div className="card-body">
                  <div className="row wrap" style={{ gap: 14 }}>
                    <div className="grow" style={{ minWidth: 240 }}>
                      <div className="row wrap">
                        <span className="mono small mute">#{pr.number}</span>
                        <strong>{pr.title}</strong>
                        <Pill tone={pr.merged_at ? 'left' : pr.state === 'open' ? 'ok' : 'mute'}>{pr.merged_at ? 'merged' : pr.state}</Pill>
                      </div>
                      <div className="mono tiny mute" style={{ marginTop: 4 }}><GitBranch size={11} style={{ verticalAlign: -1 }} /> {pr.head.ref} · opened {timeAgo(pr.created_at)} by {pr.user.login}</div>
                    </div>
                    {src && (
                      <div className="row small dim">
                        <span>fixes</span><a href={src.html_url} target="_blank" rel="noreferrer">#{src.number}</a>
                        <ArrowRight size={13} /><span className="mute tiny">(likely source PR)</span>
                      </div>
                    )}
                    {gate !== undefined && <GatePill conclusion={gate?.conclusion} />}
                    {pr.additions !== undefined && (
                      <span className="mono small">
                        <span style={{ color: 'var(--ok)' }}>+{pr.additions}</span> <span style={{ color: 'var(--bad)' }}>−{pr.deletions}</span>
                        <span className="mute"> · {pr.changed_files} files</span>
                      </span>
                    )}
                    <a className="btn sm" href={pr.html_url} target="_blank" rel="noreferrer">View <ExternalLink size={12} /></a>
                  </div>
                  {gate?.output?.title && <div className="small dim" style={{ marginTop: 10 }}>{gate.output.title}</div>}
                </div>
              </Card>
            );
          })}
      </div>
    </>
  );
}
