import { useState } from 'react';
import { CheckCircle2, ScanSearch, ShieldAlert } from 'lucide-react';
import { api } from '../api/client';
import type { OwaspResult } from '../types';
import { ScoreRing } from '../components/Charts';
import { Card, CardHead, Empty, Notice, PageHead, Pill, SeverityPill, Spinner } from '../components/ui';

const VULNERABLE_CODE = `import hashlib
import os
import pickle
import sqlite3
import subprocess

import requests
import yaml


def get_user(uid):
    conn = sqlite3.connect("app.db")
    return conn.execute(f"SELECT * FROM users WHERE id = '{uid}'").fetchone()


def run_report(cmd):
    return subprocess.run(cmd, shell=True)


def load_session(blob):
    return pickle.loads(blob)


def calculate(expr):
    return eval(expr)


def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()


def fetch_remote(url):
    return requests.get(url, verify=False)


def load_config(text):
    return yaml.load(text)


def read_upload(name):
    return open(os.path.join("/data/uploads", name)).read()


def cleanup():
    try:
        os.remove("/tmp/cache")
    except Exception:
        pass
`;

const CLEAN_CODE = `import os
import sqlite3

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")


def fetch_customer_account(db_path: str, customer_id: str):
    """Look up an account using a parameterised query."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT id, email, balance FROM accounts WHERE customer_id = ?",
            (customer_id,),
        )
        return cur.fetchone()
    finally:
        conn.close()
`;

const VULN_REQS = `fastapi==0.115.0
pydantic==2.8.2
pyyaml==5.3
requests==2.28.0
scikit-learn==1.4.0
`;

type Preset = 'vuln' | 'clean' | 'reqs' | 'custom';

export function Scanner() {
  const [preset, setPreset] = useState<Preset>('vuln');
  const [code, setCode] = useState(VULNERABLE_CODE);
  const [filename, setFilename] = useState('services/payment_service.py');
  const [reqs, setReqs] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OwaspResult | null>(null);
  const [ms, setMs] = useState<number | null>(null);

  const choose = (p: Preset) => {
    setPreset(p);
    setResult(null); setError(null);
    if (p === 'vuln') { setCode(VULNERABLE_CODE); setReqs(''); setFilename('services/payment_service.py'); }
    if (p === 'clean') { setCode(CLEAN_CODE); setReqs(''); setFilename('services/billing_service.py'); }
    if (p === 'reqs') { setCode(''); setReqs(VULN_REQS); }
  };

  const scan = async () => {
    setBusy(true); setError(null);
    const t0 = performance.now();
    try {
      const r = await api.owaspScan(code.trim() ? code : null, filename || 'snippet.py', reqs.trim() ? reqs : null);
      setResult(r.compliance);
      setMs(performance.now() - t0);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setBusy(false); }
  };

  const allCats = ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08', 'A09', 'A10'];
  const violated = new Set((result?.violated_categories ?? []).map((c) => c.slice(0, 3)));

  return (
    <>
      <PageHead
        title="Security Scanner"
        sub="The same OWASP Top 10 auditor that runs on every pull request. Paste code or a requirements file and it is analysed server-side with Python’s AST. Nothing is executed."
        right={<Pill tone="left" dot>shift-left</Pill>}
      />

      <div className="grid g-split">
        <Card>
          <CardHead icon={<ScanSearch size={15} color="var(--left)" />} title="Input" right={
            <div className="seg" role="tablist" aria-label="Sample input">
              {([['vuln', 'Vulnerable code'], ['clean', 'Fixed code'], ['reqs', 'Vulnerable deps']] as [Preset, string][]).map(([id, label]) => (
                <button key={id} className={preset === id ? 'on' : ''} onClick={() => choose(id)} role="tab" aria-selected={preset === id}>{label}</button>
              ))}
            </div>} />
          <div className="card-body stack" style={{ gap: 12 }}>
            <label className="field"><span>File name</span>
              <input type="text" value={filename} onChange={(e) => { setFilename(e.target.value); setPreset('custom'); }} />
            </label>
            <label className="field"><span>Python source</span>
              <textarea rows={16} value={code} spellCheck={false}
                onChange={(e) => { setCode(e.target.value); setPreset('custom'); }} placeholder="Paste Python code…" />
            </label>
            <label className="field"><span>requirements.txt (optional)</span>
              <textarea rows={4} value={reqs} spellCheck={false}
                onChange={(e) => { setReqs(e.target.value); setPreset('custom'); }} placeholder="package==version" />
            </label>
            <button className="btn left" onClick={scan} disabled={busy || (!code.trim() && !reqs.trim())}>
              {busy ? <><Spinner />Scanning…</> : <><ShieldAlert size={15} />Scan against OWASP Top 10</>}
            </button>
            {error && <Notice tone="bad">{error}</Notice>}
          </div>
        </Card>

        <div className="stack">
          <Card>
            <CardHead icon={<CheckCircle2 size={15} color="var(--left)" />} title="Result"
              right={ms !== null ? <span className="tiny mute mono">{ms.toFixed(0)} ms round-trip</span> : undefined} />
            <div className="card-body">
              {!result ? <Empty icon={<ScanSearch size={26} />}>Choose a sample and press Scan.</Empty> : (
                <div className="stack" style={{ gap: 16 }}>
                  <div className="row" style={{ gap: 20, alignItems: 'center' }}>
                    <ScoreRing score={result.compliance_score} grade={result.grade} />
                    <div className="grow">
                      <div style={{ fontSize: 20, fontWeight: 700 }}>{result.total_findings} finding{result.total_findings === 1 ? '' : 's'}</div>
                      <div className="dim small" style={{ marginTop: 2 }}>
                        {result.violated_categories.length} of 10 categories violated
                      </div>
                      <div style={{ marginTop: 8 }}>
                        <Pill tone={result.compliance_score >= 85 ? 'ok' : 'bad'} dot>
                          {result.compliance_score >= 85 ? 'would pass the merge gate' : 'would block the merge'}
                        </Pill>
                      </div>
                    </div>
                  </div>
                  <div className="owasp-grid" aria-label="OWASP categories">
                    {allCats.map((c) => (
                      <div key={c} className={`owasp-cell ${violated.has(c) ? 'bad' : 'ok'}`} title={violated.has(c) ? 'violated' : 'no findings'}>{c}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
          <Notice>
            Honest scope: this is pattern and AST matching on single files, not whole-program taint analysis. It does not detect hardcoded
            secrets (the PR pipeline uses <code>detect-secrets</code> for that) and may over-flag, for example every <code>os.path.join</code>.
          </Notice>
        </div>
      </div>

      {result && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title={`Findings (${result.findings.length})`} />
          <div className="card-body flush">
            {result.findings.length === 0 ? <Empty icon={<CheckCircle2 size={26} />}>No violations found.</Empty> :
              [...result.findings].sort((a, b) => ['critical', 'high', 'medium', 'low'].indexOf(a.severity) - ['critical', 'high', 'medium', 'low'].indexOf(b.severity)).map((f, i) => (
                <div className="finding" key={i}>
                  <div className="row wrap">
                    <SeverityPill severity={f.severity} />
                    <strong>{f.title}</strong>
                    <span className="grow" />
                    <span className="mono tiny mute">{f.category_id} · {f.file}:{f.line}{f.cwe_id ? ` · ${f.cwe_id}` : ''}</span>
                  </div>
                  <p className="small dim" style={{ marginTop: 6 }}>{f.description}</p>
                  <div className="rec"><strong style={{ color: 'var(--ok)' }}>Fix: </strong>{f.recommendation}</div>
                </div>
              ))}
          </div>
        </Card>
      )}
    </>
  );
}
