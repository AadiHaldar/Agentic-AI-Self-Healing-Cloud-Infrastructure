#!/usr/bin/env python3
"""
AgentHeal end-to-end demo / smoke test.

Runs the whole platform through its public HTTP API, narrating each step, and exits non-zero
if any check fails. Standard library only.

    python scripts/demo_e2e.py --base http://127.0.0.1:8001
    python scripts/demo_e2e.py --base http://127.0.0.1:8000 --webhook-secret <secret>

Everything printed comes from the server's real responses. Where the server is in a degraded
mode (no Gemini key, no cluster) the script says so instead of hiding it.
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

USE_COLOR = sys.stdout.isatty() and os.name != "nt" or os.environ.get("FORCE_COLOR")
def c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if USE_COLOR else s
OK, BAD, DIM, BOLD = (lambda s: c("32", s)), (lambda s: c("31", s)), (lambda s: c("2", s)), (lambda s: c("1", s))

VULNERABLE = '''import hashlib, os, pickle, sqlite3, subprocess
import requests, yaml

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
'''

FIXED = '''import os
import sqlite3

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")

def fetch_customer_account(db_path: str, customer_id: str):
    """Look up an account using a parameterised query."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT id, email, balance FROM accounts WHERE customer_id = ?", (customer_id,)
        ).fetchone()
    finally:
        conn.close()
'''

# Same four fault patterns as scripts/run_evaluation.py, plus a healthy control.
SCENARIOS = [
    ("Healthy control",    "frontend",        0.25,  0.40,   45.0, 120.0, False),
    ("Flash-sale surge",   "checkoutservice", 0.954, 0.45,  450.0, 500.0, True),
    ("Thread deadlock",    "cartservice",     0.99,  0.85, 5000.0,   0.0, True),
    ("Memory leak",        "redis-cart",      0.15,  0.942,  48.0, 110.0, True),
    ("Cascading overload", "frontend",        0.88,  0.80,  320.0, 250.0, True),
]

checks = []


def check(name: str, ok: bool, detail: str = ""):
    checks.append((name, ok))
    print(f"   {'[PASS]' if ok else '[FAIL]'} {name}" + (f"  {DIM(detail)}" if detail else ""))
    return ok


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def call(self, method: str, path: str, body=None, headers=None, raw: bytes = None, timeout=120):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        h = {"Content-Type": "application/json", **(headers or {})}
        req = urllib.request.Request(self.base + path, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.loads(r.read().decode() or "null")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode() or "null")
            except Exception:
                return e.code, None


def step(n: int, title: str, say: str):
    print()
    print(BOLD(f"STEP {n} - {title}"))
    print(DIM(f"   say: {say}"))


def load_dotenv_secret() -> str:
    for candidate in (".env", os.path.join(os.path.dirname(__file__), "..", ".env")):
        try:
            for line in open(candidate, encoding="utf-8"):
                if line.startswith("GITHUB_WEBHOOK_SECRET="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            continue
    return ""


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8000", help="server base URL")
    ap.add_argument("--webhook-secret", default=os.environ.get("DEMO_WEBHOOK_SECRET", ""),
                    help="webhook HMAC secret configured on the server (or env DEMO_WEBHOOK_SECRET; falls back to .env)")
    ap.add_argument("--execute", action="store_true",
                    help="also request execution of the first SAFE plan (only does anything if a cluster is reachable)")
    args = ap.parse_args()
    api = Api(args.base)
    secret = args.webhook_secret or load_dotenv_secret()
    t_start = time.perf_counter()

    # ── 0. Platform ────────────────────────────────────────────────────────
    step(0, "Platform facts", "Before anything else: what is this deployment actually wired to?")
    code, meta = api.call("GET", "/api/meta")
    if code != 200:
        print(BAD(f"   cannot reach {args.base}/api/meta (HTTP {code}). Is the server / tunnel up?"))
        return 2
    print(f"   version {meta['version']}  uptime {meta['uptime_seconds']:.0f}s  anomaly model trained: {meta['detector_trained']}")
    print(f"   Gemini connected: {meta['gemini_configured']}   cluster reachable: {meta.get('cluster_reachable')}"
          f" ({meta.get('kube_context') or 'no context'}, ns {meta.get('k8s_namespace')})   demo seed: {meta['demo_seed']}")
    check("API reachable and anomaly model trained", meta["detector_trained"])
    api.call("POST", "/api/topology/reset", {})
    _, st = api.call("GET", "/api/status")
    check("digital twin starts healthy", st["status"] == "HEALTHY", f"{st['total_pods']} services")

    # ── 1. Shift-left ──────────────────────────────────────────────────────
    step(1, "Shift-left: a risky change arrives", "The same auditor that reviews every pull request; it parses the AST, nothing is executed.")
    _, bad = api.call("POST", "/api/owasp/scan", {"code": VULNERABLE, "filename": "services/payment_service.py", "requirements_txt": None})
    b = bad["compliance"]
    cats = ", ".join(sorted({f["category_id"][:3] for f in b["findings"]}))
    print(f"   vulnerable file -> grade {b['grade']} ({b['compliance_score']:.0f}%), {b['total_findings']} findings in {len(b['violated_categories'])} categories [{cats}]")
    for f in sorted(b["findings"], key=lambda f: ["critical", "high", "medium", "low"].index(f["severity"]))[:4]:
        print(f"      {f['severity']:<8} line {f['line']:<3} {f['title']}")
    check("vulnerable code is blocked by the gate (score < 85)", b["compliance_score"] < 85, f"score {b['compliance_score']:.0f}")

    print(DIM("   ...the agent proposes a fix; the fixed file is audited again:"))
    _, good = api.call("POST", "/api/owasp/scan", {"code": FIXED, "filename": "services/payment_service.py", "requirements_txt": None})
    g = good["compliance"]
    print(f"   fixed file      -> grade {g['grade']} ({g['compliance_score']:.0f}%), {g['total_findings']} findings")
    check("fixed code passes the gate", g["compliance_score"] >= 85 and g["total_findings"] == 0)

    _, deps = api.call("POST", "/api/owasp/scan", {"code": None, "filename": "requirements.txt",
                                                    "requirements_txt": "pyyaml==5.3\nrequests==2.28.0\nfastapi==0.115.0\n"})
    d = deps["compliance"]["findings"]
    print(f"   dependency audit -> {len(d)} vulnerable pins: " + "; ".join(f["title"].replace("Vulnerable Dependency ", "") for f in d))
    check("dependency CVEs detected", len(d) >= 1)

    # ── 2. Webhook ingestion ───────────────────────────────────────────────
    step(2, "Shift-left: the webhook front door", "GitHub events are only accepted with a valid HMAC-SHA256 signature, and replays are ignored.")
    if not secret:
        print(BAD("   no webhook secret supplied (--webhook-secret / DEMO_WEBHOOK_SECRET / .env): skipping signed-request checks"))
    else:
        payload = json.dumps({"zen": "demo", "hook_id": 1}).encode()
        delivery = str(uuid.uuid4())
        hdr = {"X-GitHub-Event": "ping", "X-GitHub-Delivery": delivery}
        code, _ = api.call("POST", "/webhooks/github", raw=payload, headers=hdr)
        check("unsigned request rejected (401)", code == 401, f"HTTP {code}")
        code, _ = api.call("POST", "/webhooks/github", raw=payload, headers={**hdr, "X-Hub-Signature-256": sign(secret + "x", payload)})
        check("wrong signature rejected (401)", code == 401, f"HTTP {code}")
        code, r = api.call("POST", "/webhooks/github", raw=payload, headers={**hdr, "X-Hub-Signature-256": sign(secret, payload)})
        check("correctly signed request accepted", code == 200, f"HTTP {code} {r}")
        code, r = api.call("POST", "/webhooks/github", raw=payload, headers={**hdr, "X-Hub-Signature-256": sign(secret, payload)})
        check("replayed delivery ignored", code == 200 and (r or {}).get("reason") == "duplicate_delivery", f"{r}")
    print(DIM("   note: the GitHub App's webhook URL points at the production deployment, not this server; a live PR -> review round-trip is not exercised here."))

    # ── 3. Shift-right ─────────────────────────────────────────────────────
    step(3, "Shift-right: faults hit the running cluster", "Detect -> explain -> decide -> simulate -> (act). All timings below are measured on this server, per request.")
    rows, executed_once, first_safe = [], False, None
    for name, svc, cpu, mem, lat, rate, should_flag in SCENARIOS:
        body = {"target_service": svc, "cpu_usage": cpu, "mem_usage": mem, "latency_ms": lat, "request_rate": rate}
        code, r = api.call("POST", "/api/evaluate", body)
        if code != 200:
            check(f"{name}: evaluate", False, f"HTTP {code}")
            continue
        det, llm, rl, t = r["detection"], r["agents"]["llm_react"], r["agents"]["rl_simifed"], r["timings"]
        top = max(r["shap_scores"], key=lambda k: abs(r["shap_scores"][k]))
        sim = llm["simulation"]
        gate = "skipped" if sim["recommendation"] == "N/A" else ("SAFE" if sim["is_safe"] else "RISK")
        rows.append((name, svc, det["model_flagged"], top, rl["action"], llm["proposed_action"], llm["source"].split(":")[0], gate,
                     t["detect_ms"], t["shap_ms"], t["rl_ms"], t["llm_ms"]))
        check(f"{name}: anomaly {'flagged' if should_flag else 'NOT flagged'}", det["model_flagged"] == should_flag,
              f"score {det['anomaly_score']}")
        if should_flag and gate == "SAFE" and first_safe is None:
            first_safe = (svc, body)
        api.call("POST", "/api/topology/reset", {})

    print()
    hdr = f"   {'fault':<19}{'flag':<6}{'top SHAP':<14}{'RL':<13}{'LLM':<13}{'LLM src':<9}{'gate':<8}{'detect':>8}{'shap':>8}{'rl':>7}{'llm':>9}"
    print(BOLD(hdr))
    for (name, svc, flag, top, rlx, llmx, src, gate, d_, s_, r_, l_) in rows:
        print(f"   {name:<19}{str(flag):<6}{top:<14}{rlx:<13}{llmx:<13}{src:<9}{gate:<8}{d_:>6.1f}ms{s_:>6.1f}ms{r_:>5.1f}ms{l_ / 1000:>7.2f}s")
    if rows:
        agree = sum(1 for r in rows if r[2] and r[4] == r[5])
        flagged = sum(1 for r in rows if r[2])
        print(DIM(f"   RL and LLM chose the same action in {agree}/{flagged} flagged runs. LLM source: {rows[-1][6]} "
                  f"({'live model call' if rows[-1][6] == 'gemini' else 'canned fallback - no Gemini key on this server'})."))
    check("healthy control raised no action", any(r[0] == "Healthy control" and not r[2] and r[5] == "DO_NOTHING" for r in rows))

    # ── 4. Acting ──────────────────────────────────────────────────────────
    step(4, "Acting on the plan", "Nothing touches the cluster unless the twin says SAFE and a cluster is reachable.")
    if first_safe and args.execute:
        svc, body = first_safe
        code, r = api.call("POST", "/api/evaluate", {**body, "execute": True})
        print(f"   execute=true on {svc}: {r['actuation']}")
        check("execution is gated and reported honestly", r["actuation"] is not None or not meta.get("cluster_reachable"))
        api.call("POST", "/api/topology/reset", {})
    else:
        why = "pass --execute to request it" if meta.get("cluster_reachable") else "no cluster is reachable from this server, so runs are plan-only"
        print(f"   not executed ({why}).")

    # ── Summary ────────────────────────────────────────────────────────────
    failed = [n for n, ok in checks if not ok]
    print()
    print(BOLD(f"SUMMARY: {len(checks) - len(failed)}/{len(checks)} checks passed in {time.perf_counter() - t_start:.1f}s"))
    for n in failed:
        print(BAD(f"   FAILED: {n}"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
