import { useEffect, useState } from 'react';
import {
  Activity, Brain, Crosshair, Gauge, History, Play, RotateCcw, ShieldCheck, Sparkles, Wrench, Zap,
} from 'lucide-react';
import { api } from '../api/client';
import { useApp } from '../lib/context';
import { useRemote } from '../lib/hooks';
import type { EvaluateResponse } from '../types';
import { Topology } from '../components/Topology';
import { ShapBars } from '../components/Charts';
import { Card, CardHead, Empty, Notice, PageHead, Pill, Spinner } from '../components/ui';

interface Scenario {
  id: string; name: string; blurb: string; service: string;
  cpu: number; mem: number; lat: number; rate: number;
}

// The same four fault patterns used by scripts/run_evaluation.py, plus a healthy control.
const SCENARIOS: Scenario[] = [
  { id: 'surge', name: 'Flash-sale surge', blurb: 'Checkout CPU saturates under a traffic spike.', service: 'checkoutservice', cpu: 0.954, mem: 0.45, lat: 450, rate: 500 },
  { id: 'deadlock', name: 'Thread deadlock', blurb: 'Cart threads starve: CPU pegged, throughput collapses.', service: 'cartservice', cpu: 0.99, mem: 0.85, lat: 5000, rate: 0 },
  { id: 'leak', name: 'Memory leak', blurb: 'Redis heap grows toward OOM while CPU stays low.', service: 'redis-cart', cpu: 0.15, mem: 0.942, lat: 48, rate: 110 },
  { id: 'cascade', name: 'Cascading overload', blurb: 'Frontend degrades as downstream calls pile up.', service: 'frontend', cpu: 0.88, mem: 0.80, lat: 320, rate: 250 },
  { id: 'healthy', name: 'Healthy control', blurb: 'Normal traffic. Nothing should fire.', service: 'frontend', cpu: 0.25, mem: 0.40, lat: 45, rate: 120 },
];

// What the digital-twin gate can say, and how to show it.
const VERDICT: Record<string, { label: string; tone?: 'ok' | 'bad' | 'warn'; pill: 'ok' | 'bad' | 'warn' | 'mute' }> = {
  SAFE_TO_EXECUTE: { label: 'SAFE', tone: 'ok', pill: 'ok' },
  NOT_NEEDED: { label: 'Not needed', tone: 'warn', pill: 'warn' },
  INEFFECTIVE: { label: 'Ineffective', tone: 'bad', pill: 'bad' },
  RISK_OF_OVERLOAD: { label: 'Risk', tone: 'bad', pill: 'bad' },
  TARGET_NOT_IN_TWIN: { label: 'Unknown service', tone: 'bad', pill: 'bad' },
  'N/A': { label: 'Skipped', pill: 'mute' },
};
const verdictOf = (rec?: string) => VERDICT[rec ?? 'N/A'] ?? { label: rec ?? '—', pill: 'mute' as const };

const SERVICES = ['frontend', 'checkoutservice', 'cartservice', 'redis-cart'];

interface HistoryRow {
  at: string; scenario: string; service: string; flagged: boolean;
  rl: string; llm: string; gate: string; ms: number; source: string;
}

const pct = (v: number) => `${Math.round(v * 100)}%`;
const ms = (v: number) => (v >= 1000 ? `${(v / 1000).toFixed(2)} s` : `${v.toFixed(v < 10 ? 1 : 0)} ms`);

function Slider({ label, value, min, max, step, onChange, fmt }: {
  label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void; fmt: (v: number) => string;
}) {
  return (
    <label className="field">
      <span>{label}: <strong className="mono" style={{ color: 'var(--tx)' }}>{fmt(value)}</strong></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(parseFloat(e.target.value))} />
    </label>
  );
}

function Stage({ idx, icon, title, ms: t, tone, children, show }: {
  idx: number; icon: React.ReactNode; title: string; ms?: number; tone?: 'ok' | 'bad' | 'warn'; children: React.ReactNode; show: boolean;
}) {
  return (
    <div className={`stage ${show ? tone ?? '' : 'idle'}`} style={show ? { animationDelay: `${idx * 260}ms` } : undefined}>
      <div className="st-h">{icon}<span>{title}</span>{t !== undefined && show && <span className="ms">{ms(t)}</span>}</div>
      {show ? children : <div className="mute small">waiting…</div>}
    </div>
  );
}

export function Healing({ scenario }: { scenario?: string }) {
  const { meta, refreshStatus } = useApp();
  const topo = useRemote(api.topology, []);

  const initial = SCENARIOS.find((s) => s.id === scenario) ?? SCENARIOS[1];
  const [sel, setSel] = useState<string>(initial.id);
  const [service, setService] = useState(initial.service);
  const [cpu, setCpu] = useState(initial.cpu);
  const [mem, setMem] = useState(initial.mem);
  const [lat, setLat] = useState(initial.lat);
  const [rate, setRate] = useState(initial.rate);
  const [execute, setExecute] = useState(false);

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<EvaluateResponse | null>(null);
  const [history, setHistory] = useState<HistoryRow[]>([]);

  const [ovAction, setOvAction] = useState('RESTART_POD');
  const [ovReason, setOvReason] = useState('Operator intervention from console');
  const [ovMsg, setOvMsg] = useState<string | null>(null);

  const pick = (s: Scenario) => {
    setSel(s.id); setService(s.service); setCpu(s.cpu); setMem(s.mem); setLat(s.lat); setRate(s.rate);
  };

  useEffect(() => {
    const s = SCENARIOS.find((x) => x.id === scenario);
    if (s) pick(s);
  }, [scenario]);

  const run = async () => {
    setRunning(true); setError(null); setResult(null);
    try {
      const res = await api.evaluate({
        target_service: service, cpu_usage: cpu, mem_usage: mem, latency_ms: lat, request_rate: rate,
        execute: execute && !!meta?.cluster_reachable,
      });
      setResult(res);
      const t = res.timings;
      setHistory((h) => [{
        at: new Date().toLocaleTimeString(),
        scenario: SCENARIOS.find((s) => s.id === sel)?.name ?? 'Custom',
        service, flagged: res.detection.model_flagged,
        rl: res.agents.rl_simifed.action, llm: res.agents.llm_react.proposed_action,
        gate: res.agents.llm_react.simulation.recommendation,
        ms: t.detect_ms + t.shap_ms + t.rl_ms + t.llm_ms,
        source: res.agents.llm_react.source,
      }, ...h].slice(0, 8));
      topo.reload(); refreshStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const reset = async () => {
    try { await api.resetTopology(); setResult(null); topo.reload(); refreshStatus(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };

  const override = async () => {
    if (!window.confirm(`Apply ${ovAction} to ${service}? ${meta?.cluster_reachable ? `This changes the live cluster (${meta.kube_context}, namespace ${meta.k8s_namespace}).` : 'No cluster is reachable from this host, so it will be a dry run or fail.'}`)) return;
    try {
      const r = await api.override(service, ovAction, ovReason);
      setOvMsg(`${r.k8s_output.status}: ${r.k8s_output.message ?? ''}`);
      topo.reload();
    } catch (e) { setOvMsg(`Error: ${e instanceof Error ? e.message : String(e)}`); }
  };

  const llm = result?.agents.llm_react;
  const rl = result?.agents.rl_simifed;
  const sim = llm?.simulation;
  const det = result?.detection;
  const t = result?.timings;
  const total = t ? t.detect_ms + t.shap_ms + t.rl_ms + t.llm_ms : 0;
  const show = !!result && !running;

  const actText = (() => {
    if (!result || !llm) return '';
    if (result.actuation) return `${result.actuation.status}: ${result.actuation.message ?? ''}`;
    if (!det?.is_anomaly_used) return 'No action needed';
    return 'Plan only. Nothing was changed.';
  })();

  return (
    <>
      <PageHead
        title="Self-Healing"
        sub="Inject a real fault pattern and watch the loop run: detect → explain → decide → simulate → act. Every number below is measured on this server, per request."
        right={<Pill tone="right" dot>shift-right</Pill>}
      />

      {meta && !meta.gemini_configured && (
        <div style={{ marginBottom: 16 }}>
          <Notice tone="warn">No Gemini API key is configured on this server, so the LLM agent returns a canned fallback plan. It is labelled “fallback” in the results.</Notice>
        </div>
      )}

      <Card>
        <CardHead icon={<Crosshair size={15} color="var(--right)" />} title="1 · Choose a fault" right={<span className="tiny mute">patterns from scripts/run_evaluation.py</span>} />
        <div className="card-body" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 12 }}>
          {SCENARIOS.map((s) => (
            <button key={s.id} onClick={() => pick(s)} className="btn" aria-pressed={sel === s.id}
              style={{
                flexDirection: 'column', alignItems: 'flex-start', gap: 4, textAlign: 'left', padding: '12px 14px',
                borderColor: sel === s.id ? 'var(--right)' : undefined,
                background: sel === s.id ? 'var(--right-soft)' : undefined,
              }}>
              <span style={{ fontWeight: 650 }}>{s.name}</span>
              <span className="small dim" style={{ fontWeight: 400 }}>{s.blurb}</span>
              <span className="tiny mute mono">{s.service} · cpu {pct(s.cpu)} · mem {pct(s.mem)}</span>
            </button>
          ))}
        </div>
      </Card>

      <div className="grid g-split" style={{ marginTop: 16 }}>
        <Card>
          <CardHead icon={<Activity size={15} color="var(--right)" />} title="Digital twin"
            right={<button className="btn sm ghost" onClick={reset}><RotateCcw size={13} />Reset twin</button>} />
          <div className="card-body">
            {topo.data ? (
              <Topology topology={topo.data} selected={service}
                predicted={result && sim?.predicted_cpu ? sim.predicted_cpu : undefined}
                onSelect={(id) => setService(id)} />
            ) : topo.error ? <Notice tone="bad">Could not load topology: {topo.error}</Notice> : <Spinner />}
            <p className="tiny mute" style={{ marginTop: 8 }}>
              Click a service to target it. Edges turn red when an endpoint is above 80% CPU. After a run, “after action” shows the
              simulator’s predicted CPU for the target and its neighbours.
            </p>
          </div>
        </Card>

        <Card>
          <CardHead icon={<Zap size={15} color="var(--right)" />} title="2 · Inject telemetry" />
          <div className="card-body stack" style={{ gap: 14 }}>
            <label className="field">
              <span>Target service</span>
              <select value={service} onChange={(e) => setService(e.target.value)}>
                {SERVICES.map((s) => <option key={s}>{s}</option>)}
              </select>
            </label>
            <div className="grid g2" style={{ gap: 14 }}>
              <Slider label="CPU" value={cpu} min={0.05} max={1} step={0.01} onChange={setCpu} fmt={pct} />
              <Slider label="Memory" value={mem} min={0.05} max={1} step={0.01} onChange={setMem} fmt={pct} />
              <Slider label="Latency" value={lat} min={20} max={5000} step={10} onChange={setLat} fmt={(v) => `${v} ms`} />
              <Slider label="Request rate" value={rate} min={0} max={3000} step={10} onChange={setRate} fmt={(v) => `${v}/s`} />
            </div>
            <label className="row small" style={{ cursor: meta?.cluster_reachable ? 'pointer' : 'not-allowed', opacity: meta?.cluster_reachable ? 1 : 0.6 }}>
              <input type="checkbox" checked={execute && !!meta?.cluster_reachable} disabled={!meta?.cluster_reachable}
                onChange={(e) => setExecute(e.target.checked)} />
              <span>
                Execute on the cluster if the twin says SAFE
                {meta?.cluster_reachable
                  ? <span className="mute"> — live: {meta.kube_context} / {meta.k8s_namespace}</span>
                  : <span className="mute"> — no reachable cluster from this host; runs are plan-only</span>}
              </span>
            </label>
            <div className="row">
              <button className="btn primary grow" onClick={run} disabled={running}>
                {running ? <><Spinner />Running (Gemini call ≈ 5–8 s)…</> : <><Play size={14} fill="currentColor" />Inject &amp; analyse</>}
              </button>
            </div>
            {error && <Notice tone="bad">{error}</Notice>}
          </div>
        </Card>
      </div>

      <Card style={{ marginTop: 16 }}>
        <CardHead icon={<Gauge size={15} color="var(--right)" />} title="3 · Pipeline" right={
          show ? <Pill tone="mute">{ms(total)} compute · measured now</Pill> : running ? <Pill tone="info"><Spinner size={11} />running</Pill> : undefined} />
        <div className="card-body">
          <div className="pipe">
            <Stage idx={0} show={show} icon={<Crosshair size={14} color="var(--right)" />} title="Detect" ms={t?.detect_ms}
              tone={det?.model_flagged ? 'bad' : 'ok'}>
              <div className="big" style={{ color: det?.model_flagged ? 'var(--bad)' : 'var(--ok)' }}>{det?.model_flagged ? 'Anomaly' : 'Normal'}</div>
              <div className="tiny mute" style={{ marginTop: 4 }}>Isolation Forest score <span className="mono">{det?.anomaly_score}</span> (below 0 = anomalous)</div>
            </Stage>
            <Stage idx={1} show={show} icon={<Sparkles size={14} color="var(--right)" />} title="Explain" ms={t?.shap_ms}>
              {result && (() => {
                const top = Object.entries(result.shap_scores).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0];
                return <>
                  <div className="big mono" style={{ fontSize: 14 }}>{top?.[0] ?? '—'}</div>
                  <div className="tiny mute" style={{ marginTop: 4 }}>KernelSHAP: largest contributor ({top ? top[1].toFixed(2) : '—'})</div>
                </>;
              })()}
            </Stage>
            <Stage idx={2} show={show} icon={<Brain size={14} color="var(--right)" />} title="Decide (RL ‖ LLM)" ms={t ? t.rl_ms + t.llm_ms : undefined}
              tone={result?.comparison.actions_match ? 'ok' : 'warn'}>
              <div className="small"><span className="mute">RL </span><strong className="mono">{rl?.action}</strong> <span className="mute tiny">{t && ms(t.rl_ms)}</span></div>
              <div className="small"><span className="mute">LLM </span><strong className="mono">{llm?.proposed_action}</strong> <span className="mute tiny">{t && ms(t.llm_ms)}</span></div>
              <div style={{ marginTop: 6 }} className="row wrap">
                <Pill tone={result?.comparison.actions_match ? 'ok' : 'warn'}>{result?.comparison.actions_match ? 'agents agree' : 'agents diverge'}</Pill>
                <Pill tone={llm?.source.startsWith('gemini') ? 'info' : 'warn'}>{llm?.source.startsWith('gemini') ? 'live Gemini' : llm?.source === 'skipped' ? 'LLM skipped' : 'fallback'}</Pill>
              </div>
            </Stage>
            <Stage idx={3} show={show} icon={<ShieldCheck size={14} color="var(--right)" />} title="Gate (twin)" tone={verdictOf(sim?.recommendation).tone}>
              <div className="big" style={{ color: sim?.is_safe ? 'var(--ok)' : sim?.recommendation === 'N/A' ? undefined : 'var(--bad)' }}>
                {verdictOf(sim?.recommendation).label}
              </div>
              <div className="tiny mute" style={{ marginTop: 4 }}>
                {sim?.recommendation === 'N/A' ? 'no action to check' : sim?.reason ?? ''}
              </div>
              {llm?.gate_alternative?.action && (
                <div className="tiny" style={{ marginTop: 6, color: 'var(--right)', fontWeight: 700 }}>
                  Gate suggests <span className="mono">{llm.gate_alternative.action}</span> instead
                </div>
              )}
            </Stage>
            <Stage idx={4} show={show} icon={<Wrench size={14} color="var(--right)" />} title="Act"
              tone={result?.actuation?.status === 'blocked' ? 'bad' : undefined}>
              <div className="big" style={{ fontSize: 14 }}>{sim && !sim.is_safe && sim.recommendation !== 'N/A' ? 'Blocked by gate' : result?.executed ? 'Execute requested' : 'Plan only'}</div>
              <div className="tiny mute" style={{ marginTop: 4 }}>{actText}</div>
            </Stage>
          </div>
          <p className="tiny mute" style={{ marginTop: 12 }}>
            <strong>How to read this.</strong> The RL agent is a Q-table trained offline inside a fault simulator (not on a real cluster), so treat it as a
            baseline policy. The gate is a digital-twin sanity check: it blocks actions for services the twin predicts will stay healthy, actions that
            would not relieve the predicted fault, and actions that would overload neighbours. Its effects are modelled assumptions, not measurements.
          </p>
          {det && det.assumed_features.length > 0 && (
            <div style={{ marginTop: 12 }}><Notice>Not provided, so healthy-baseline values were assumed for: <code>{det.assumed_features.join(', ')}</code>.</Notice></div>
          )}
        </div>
      </Card>

      <div className="grid g2" style={{ marginTop: 16 }}>
        <Card>
          <CardHead icon={<Brain size={15} color="var(--right)" />} title="LLM reasoning"
            right={llm ? <Pill tone={llm.source.startsWith('gemini') ? 'info' : 'warn'}>{llm.source}</Pill> : undefined} />
          <div className="card-body stack" style={{ gap: 12 }}>
            {!show || !llm ? <Empty icon={<Brain size={24} />}>Run an incident to see the agent’s reasoning.</Empty> : (
              <>
                <div><div className="label">Root cause</div><div style={{ marginTop: 4 }}>{llm.root_cause ?? '—'}</div></div>
                <div><div className="label">Reasoning</div><pre className="block" style={{ marginTop: 4 }}>{llm.thought ?? '—'}</pre></div>
                <div><div className="label">Operator explanation</div><div className="dim" style={{ marginTop: 4 }}>{llm.explanation ?? '—'}</div></div>
              </>
            )}
          </div>
        </Card>
        <Card>
          <CardHead icon={<Sparkles size={15} color="var(--right)" />} title="Why was it flagged? (SHAP)" />
          <div className="card-body">
            {!show || !result ? <Empty icon={<Sparkles size={24} />}>Feature attribution appears after a run.</Empty> : (
              <>
                <ShapBars scores={result.shap_scores} />
                <p className="tiny mute" style={{ marginTop: 10 }}>
                  KernelSHAP over the Isolation Forest’s output, using a synthetic healthy background. Treat it as a guide to which
                  signals matter, not as a precise causal measure.
                </p>
              </>
            )}
          </div>
        </Card>
      </div>

      <div className="grid g-wide" style={{ marginTop: 16 }}>
        <Card>
          <CardHead icon={<History size={15} color="var(--right)" />} title="Run history (this session)" />
          <div className="card-body flush" style={{ overflowX: 'auto' }}>
            {history.length === 0 ? <Empty>No runs yet.</Empty> : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
                <thead>
                  <tr className="label" style={{ textAlign: 'left' }}>
                    {['Time', 'Fault', 'Detected', 'RL', 'LLM', 'Gate', 'Compute'].map((h) => <th key={h} style={{ padding: '10px 14px', fontWeight: 600 }}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {history.map((h, i) => (
                    <tr key={i} style={{ borderTop: '1px solid var(--line)' }}>
                      <td className="mono mute" style={{ padding: '9px 14px' }}>{h.at}</td>
                      <td style={{ padding: '9px 14px' }}>{h.scenario}</td>
                      <td style={{ padding: '9px 14px' }}><Pill tone={h.flagged ? 'bad' : 'ok'}>{h.flagged ? 'yes' : 'no'}</Pill></td>
                      <td className="mono" style={{ padding: '9px 14px' }}>{h.rl}</td>
                      <td className="mono" style={{ padding: '9px 14px' }}>{h.llm}</td>
                      <td style={{ padding: '9px 14px' }}><Pill tone={verdictOf(h.gate).pill}>{verdictOf(h.gate).label}</Pill></td>
                      <td className="mono" style={{ padding: '9px 14px' }}>{ms(h.ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        <Card>
          <CardHead icon={<Wrench size={15} color="var(--warn)" />} title="Operator override" />
          <div className="card-body stack" style={{ gap: 12 }}>
            <p className="small dim">Bypasses the agents and applies an action to <strong className="mono">{service}</strong> directly. Asks for confirmation first.</p>
            <label className="field"><span>Action</span>
              <select value={ovAction} onChange={(e) => setOvAction(e.target.value)}>
                <option value="RESTART_POD">RESTART_POD</option>
                <option value="SCALE_UP">SCALE_UP (4 replicas)</option>
                <option value="PATCH_LIMITS">PATCH_LIMITS (cpu 1000m / mem 1024Mi)</option>
              </select>
            </label>
            <label className="field"><span>Reason (audit note)</span>
              <input type="text" value={ovReason} onChange={(e) => setOvReason(e.target.value)} />
            </label>
            <button className="btn danger" onClick={override}>Apply override</button>
            {ovMsg && <Notice>{ovMsg}</Notice>}
          </div>
        </Card>
      </div>
    </>
  );
}
