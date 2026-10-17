#!/usr/bin/env python3
"""
AgentHeal - interactive terminal demo of the shift-right (self-healing) loop.

    python scripts/demo_healing_terminal.py                 # uses the running server on :8000, else runs in-process
    python scripts/demo_healing_terminal.py --base http://127.0.0.1:8001
    python scripts/demo_healing_terminal.py --step          # pause before every stage (best for presenting)
    python scripts/demo_healing_terminal.py --fast          # no reveal delays

Every number on screen comes from the real pipeline response (/api/evaluate): the Isolation Forest verdict, KernelSHAP
contributions, the RL policy and Gemini decisions, the digital-twin gate verdict and measured timings. Nothing is scripted.
Where something is a dry run or a fallback, it says so. Standard library only.
"""
import argparse
import json
import os
import shutil
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if os.name == "nt":
    os.system("")  # enable ANSI escape sequences in the Windows console

R, B, DIM = "\033[0m", "\033[1m", "\033[2m"
RED, GRN, YEL, BLU, MAG, CYN, WHT = "\033[91m", "\033[92m", "\033[93m", "\033[94m", "\033[95m", "\033[96m", "\033[97m"
WIDTH = min(shutil.get_terminal_size((100, 30)).columns, 110)

# The same fault patterns as scripts/run_evaluation.py and the console.
SCENARIOS = [
    ("1", "Flash-sale surge",   "checkoutservice", 0.954, 0.45,  450.0, 500.0, None),
    ("2", "Thread deadlock",    "cartservice",     0.99,  0.85, 5000.0,   0.0, None),
    ("3", "Memory leak",        "redis-cart",      0.15,  0.942,  48.0, 110.0, None),
    ("4", "Cascading overload", "frontend",        0.88,  0.80,  320.0, 250.0, None),
    ("5", "Healthy control",    "frontend",        0.25,  0.40,   45.0, 120.0, None),
    ("6", "False alarm (detector flag forced, telemetry healthy)", "frontend", 0.25, 0.40, 45.0, 120.0, True),
]

SAY = {
    "detect":  "An unsupervised Isolation Forest scores the telemetry. Below zero means anomalous. This takes milliseconds.",
    "explain": "KernelSHAP says which signals pushed the score. Red bars push toward anomaly. It is attribution, not proof of root cause.",
    "decide":  "Two independent deciders: a Q-learning policy trained offline on a simulator, and Gemini reasoning over the evidence. Disagreement is shown, not hidden.",
    "gate":    "Nothing runs unless the digital twin says the action is needed, effective for this kind of fault, and safe for neighbours.",
    "act":     "Execution is opt-in and needs a reachable cluster. Without one this is a plan, never a pretend success.",
}


# ── API access: HTTP to a running server, or in-process ──────────────────────

class Api:
    def __init__(self, base=None, inproc=False):
        self.base, self.client = (base or "").rstrip("/"), None
        if inproc:
            sys.path.insert(0, ROOT)
            os.environ.setdefault("SEED_DEMO_DATA", "0")
            import logging
            logging.disable(logging.CRITICAL)
            from fastapi.testclient import TestClient
            from dashboard.backend.main import app
            self.client = TestClient(app)

    def call(self, method, path, body=None, timeout=120):
        if self.client is not None:
            r = self.client.request(method, path, json=body)
            r.raise_for_status()
            return r.json()
        req = urllib.request.Request(self.base + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode() or "null")


def connect(args) -> "Api":
    if args.base:
        api = Api(args.base)
        api.call("GET", "/api/meta", timeout=8)
        return api
    try:
        api = Api("http://127.0.0.1:8000")
        api.call("GET", "/api/meta", timeout=3)
        return api
    except Exception:
        print(f"{YEL}No server on http://127.0.0.1:8000, so I'll run the pipeline in-process (takes ~15 s to load)...{R}")
        return Api(inproc=True)


# ── drawing helpers ──────────────────────────────────────────────────────────

def hr(ch="─"):
    print(f"{DIM}{ch * WIDTH}{R}")


def colour_for(v):
    return RED if v >= 0.8 else YEL if v >= 0.6 else GRN


def bar(v, n=12):
    v = max(0.0, min(1.0, v))
    filled = int(round(v * n))
    return f"{colour_for(v)}{'█' * filled}{DIM}{'░' * (n - filled)}{R}"


def shap_bar(v, scale, n=11):
    half = int(round(abs(v) / scale * n)) if scale else 0
    if v >= 0:
        return f"{DIM}{'·' * n}{R}│{RED}{'█' * half}{DIM}{'·' * (n - half)}{R}"
    return f"{DIM}{'·' * (n - half)}{R}{BLU}{'█' * half}{R}│{DIM}{'·' * n}{R}"


def ms(v):
    return f"{v / 1000:.2f} s" if v >= 1000 else f"{v:.1f} ms"


def wrap(text, indent=6, width=None):
    width = (width or WIDTH) - indent
    return "\n".join(" " * indent + line for line in textwrap.wrap(str(text), width)) if text else ""


def say(args, stage):
    if args.narrate:
        print(f"{DIM}{CYN}   SAY ▸ {SAY[stage]}{R}")


def pause(args, label="continue"):
    if args.step:
        input(f"{DIM}   ⏎ Enter to {label}...{R}")
    elif not args.fast:
        time.sleep(0.55)


def spinner(message, done_event):
    frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    i, t0 = 0, time.time()
    while not done_event.is_set():
        sys.stdout.write(f"\r {YEL}{frames[i % len(frames)]}{R} {message} {DIM}{time.time() - t0:4.1f}s{R}   ")
        sys.stdout.flush()
        time.sleep(0.09)
        i += 1
    sys.stdout.write("\r" + " " * (WIDTH - 1) + "\r")


def show_topology(topo, target=None, predicted=None, title="Digital twin"):
    nodes = topo.get("nodes", [])
    print(f"\n {B}{title}{R}  {DIM}(each service: CPU and memory; arrows are calls){R}")
    for i, n in enumerate(nodes):
        cpu, mem = n.get("cpu_usage", 0) or 0, n.get("memory_usage", 0) or 0
        mark = f"{MAG}◀ target{R}" if n["id"] == target else ""
        after = ""
        if predicted and n["id"] in predicted:
            after = f"  {GRN}after action: CPU {predicted[n['id']]:.0%}{R}"
        prefix = "  " if i == 0 else f"{DIM}  ↓ calls{R}\n  "
        print(f"{prefix}{WHT}{n['id']:<17}{R} CPU {bar(cpu)} {cpu:>4.0%}   MEM {bar(mem)} {mem:>4.0%} {mark}{after}")


# ── the pipeline view ────────────────────────────────────────────────────────

def run_scenario(api, args, meta, label, svc, cpu, mem, lat, rate, force, session):
    api.call("POST", "/api/topology/reset")
    topo = api.call("GET", "/api/topology")
    print()
    hr("═")
    print(f" {B}{CYN}INCIDENT:{R} {B}{label}{R}")
    print(f" service {B}{svc}{R} | CPU {cpu:.0%} | memory {mem:.0%} | latency {lat:.0f} ms | request rate {rate:.0f}/s"
          + (f" | {YEL}detector flag forced ON{R}" if force else ""))
    hr("═")
    topo_after_injection = dict(topo)
    topo_after_injection["nodes"] = [dict(n, **({"cpu_usage": cpu, "memory_usage": mem} if n["id"] == svc else {})) for n in topo["nodes"]]
    show_topology(topo_after_injection, svc, title="Twin with the fault injected")
    print()
    body = {"target_service": svc, "cpu_usage": cpu, "mem_usage": mem, "latency_ms": lat, "request_rate": rate}
    if force:
        body["is_anomaly"] = True
    if args.execute and meta.get("cluster_reachable"):
        body["execute"] = True

    holder = {}
    done = threading.Event()

    def work():
        try:
            holder["r"] = api.call("POST", "/api/evaluate", body)
        except Exception as e:  # noqa: BLE001
            holder["e"] = e
        finally:
            done.set()

    th = threading.Thread(target=work, daemon=True)
    th.start()
    spinner("running the pipeline (the Gemini call takes ~5-10 s)", done)
    th.join()
    if "e" in holder:
        print(f" {RED}Request failed: {holder['e']}{R}")
        return
    r = holder["r"]
    det, rl, llm, t = r["detection"], r["agents"]["rl_simifed"], r["agents"]["llm_react"], r["timings"]
    sim = llm["simulation"]

    # 1 detect
    say(args, "detect")
    flagged = det["model_flagged"]
    print(f" {B}1 DETECT{R}   Isolation Forest -> "
          f"{(RED + B + 'ANOMALY') if flagged else (GRN + B + 'NORMAL')}{R}   score {det['anomaly_score']:+.4f}   {DIM}{ms(t['detect_ms'])}{R}")
    if det["forced"]:
        print(f"      {YEL}detector flag was forced on for this test (model said: {'anomaly' if flagged else 'normal'}){R}")
    if det["assumed_features"]:
        print(f"      {DIM}assumed healthy-baseline values for: {', '.join(det['assumed_features'])}{R}")
    pause(args)

    # 2 explain
    say(args, "explain")
    scores = r["shap_scores"]
    scale = max([abs(v) for v in scores.values()] + [1e-9])
    print(f" {B}2 EXPLAIN{R}  KernelSHAP   {DIM}{ms(t['shap_ms'])}   {RED}█{DIM} toward anomaly  {BLU}█{DIM} toward normal{R}")
    for k, v in sorted(scores.items(), key=lambda kv: -abs(kv[1])):
        print(f"      {k:<14} {shap_bar(v, scale)} {v:+.3f}")
    pause(args)

    # 3 decide
    say(args, "decide")
    live = llm["source"].startswith("gemini")
    src = f"{GRN}live Gemini{R}" if live else (f"{DIM}skipped (no anomaly){R}" if llm["source"] == "skipped" else f"{YEL}FALLBACK (no Gemini key or call failed){R}")
    print(f" {B}3 DECIDE{R}")
    print(f"      RL policy   {B}{rl['action']:<13}{R} {DIM}{ms(t['rl_ms'])}  ·  {rl.get('policy', '')}{R}")
    print(f"      LLM         {B}{llm['proposed_action']:<13}{R} {DIM}{ms(t['llm_ms'])}{R}  {src}")
    if r["comparison"]["actions_match"]:
        print(f"      {GRN}agents agree{R}")
    else:
        print(f"      {YEL}agents diverge{R}")
    if llm.get("root_cause"):
        print(f"      {DIM}root cause (LLM):{R} {llm['root_cause']}")
        if llm.get("explanation"):
            print(wrap(f"explanation: {llm['explanation']}", 6))
    pause(args)

    # 4 gate
    say(args, "gate")
    rec = sim["recommendation"]
    no_action = llm["proposed_action"] == "DO_NOTHING"
    if no_action:
        fc = sim.get("baseline") or {}
        print(f" {B}4 GATE{R}     {DIM}no action proposed, so there is nothing to approve{R}")
        if fc:
            print(f"      twin forecast without intervention: peak CPU {fc.get('peak_cpu', 0):.0%}, memory {fc.get('peak_memory', 0):.0%}")
    else:
        col = {"SAFE_TO_EXECUTE": GRN, "NOT_NEEDED": YEL}.get(rec, RED if rec != "N/A" else DIM)
        label_g = {"SAFE_TO_EXECUTE": "SAFE", "N/A": "SKIPPED (no action to check)"}.get(rec, rec.replace("_", " "))
        print(f" {B}4 GATE{R}     digital twin -> {col}{B}{label_g}{R}")
        if sim.get("reason") and rec != "N/A":
            print(wrap(sim["reason"], 6))
    alt = (llm.get("gate_alternative") or {}).get("action")
    if alt and not no_action:
        print(f"      {GRN}{B}gate suggests {alt} instead{R}")
    pause(args)

    # 5 act
    say(args, "act")
    if r.get("actuation"):
        a = r["actuation"]
        print(f" {B}5 ACT{R}      {a['status']}: {a.get('message', '')}")
    elif no_action or (not flagged and not det["forced"]):
        print(f" {B}5 ACT{R}      no action needed; nothing was changed")
    elif rec not in ("SAFE_TO_EXECUTE", "N/A"):
        print(f" {B}5 ACT{R}      {RED}blocked by the gate{R}; nothing was changed")
    else:
        why = "execute is off" if not args.execute else "no cluster is reachable"
        print(f" {B}5 ACT{R}      {YEL}plan only{R} ({why}); nothing was changed. Plan: {B}{llm['proposed_action']}{R} on {svc}")

    pred = sim.get("predicted_cpu") or None
    if pred and sim.get("is_safe"):
        after_topo = api.call("GET", "/api/topology")
        show_topology(after_topo, svc, predicted=pred, title="Twin: predicted CPU after the approved action")
    total = t["detect_ms"] + t["shap_ms"] + t["rl_ms"] + t["llm_ms"]
    print(f"\n {DIM}pipeline compute {ms(total)} (measured){R}")
    session.append((label.split(" (")[0], "yes" if flagged else "no", rl["action"], llm["proposed_action"],
                    "no action" if no_action else rec, total))


def custom(api, args, meta, session):
    try:
        svc = input(" service [checkoutservice/cartservice/redis-cart/frontend]: ").strip() or "checkoutservice"
        cpu = float(input(" CPU 0-1 [0.9]: ") or 0.9)
        mem = float(input(" memory 0-1 [0.5]: ") or 0.5)
        lat = float(input(" latency ms [300]: ") or 300)
        rate = float(input(" request rate /s [200]: ") or 200)
    except ValueError:
        print(f" {RED}Not a number.{R}")
        return
    run_scenario(api, args, meta, "Custom fault", svc, cpu, mem, lat, rate, None, session)


def show_history(session):
    print()
    if not session:
        print(" no runs yet")
        return
    print(f" {B}{'Fault':<20}{'Flag':<6}{'RL':<14}{'LLM':<14}{'Gate':<18}{'Compute':>9}{R}")
    for label, flag, rl, llm, gate, total in session:
        print(f" {label[:19]:<20}{flag:<6}{rl:<14}{llm:<14}{gate:<18}{ms(total):>9}")


def banner(meta):
    print(f"\n{CYN}{B}" + "═" * WIDTH)
    print("  AGENTHEAL · SELF-HEALING LOOP · interactive terminal demo")
    print("  detect → explain → decide (RL ‖ LLM) → twin gate → act" + R)
    gem = f"{GRN}connected{R}" if meta.get("gemini_configured") else f"{YEL}no key (LLM uses a labelled fallback){R}"
    cl = f"{GRN}{meta.get('kube_context')}{R}" if meta.get("cluster_reachable") else f"{YEL}none reachable (plan-only / dry run){R}"
    print(f" Gemini: {gem}   Cluster: {cl}   Anomaly model: {'trained' if meta.get('detector_trained') else 'NOT trained'}")


def menu(args):
    print(f"\n {B}Choose a fault to inject{R}")
    for key, name, svc, cpu, mem, lat, rate, force in SCENARIOS:
        print(f"   {CYN}{key}{R}  {name:<52} {DIM}{svc} cpu {cpu:.0%} mem {mem:.0%}{R}")
    print(f"   {CYN}a{R}  run all of them     {CYN}c{R}  custom values     {CYN}r{R}  reset twin     {CYN}h{R}  history")
    print(f"   {CYN}s{R}  step mode [{'ON' if args.step else 'off'}]    {CYN}n{R}  narration [{'ON' if args.narrate else 'off'}]"
          f"    {CYN}x{R}  execute on cluster [{'ON' if args.execute else 'off'}]    {CYN}q{R}  quit")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="server URL (default: http://127.0.0.1:8000, else in-process)")
    ap.add_argument("--step", action="store_true", help="pause before each pipeline stage")
    ap.add_argument("--fast", action="store_true", help="no reveal delays")
    ap.add_argument("--no-narration", dest="narrate", action="store_false", help="hide the presenter 'SAY' lines")
    ap.add_argument("--execute", action="store_true", help="request real execution (only works if a cluster is reachable)")
    args = ap.parse_args()

    try:
        api = connect(args)
        meta = api.call("GET", "/api/meta")
    except Exception as e:  # noqa: BLE001
        print(f"{RED}Could not reach the server: {e}{R}")
        print("Start it with:  powershell -ExecutionPolicy Bypass -File scripts\\live_demo.ps1")
        return 2

    session = []
    banner(meta)
    api.call("POST", "/api/topology/reset")
    show_topology(api.call("GET", "/api/topology"))
    while True:
        menu(args)
        try:
            choice = input(f"\n {B}> {R}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if choice in ("q", "quit", "exit"):
            break
        if choice == "s":
            args.step = not args.step
        elif choice == "n":
            args.narrate = not args.narrate
        elif choice == "x":
            if not meta.get("cluster_reachable"):
                print(f" {YEL}No cluster is reachable from this server, so execution is unavailable (plan-only).{R}")
            elif args.execute:
                args.execute = False
            elif input(f" {RED}This changes the LIVE cluster '{meta.get('kube_context')}'. Type YES to enable: {R}").strip() == "YES":
                args.execute = True
        elif choice == "r":
            api.call("POST", "/api/topology/reset")
            show_topology(api.call("GET", "/api/topology"), title="Twin reset to healthy")
        elif choice == "h":
            show_history(session)
        elif choice == "c":
            custom(api, args, meta, session)
        elif choice == "a":
            for key, name, svc, cpu, mem, lat, rate, force in SCENARIOS:
                run_scenario(api, args, meta, name, svc, cpu, mem, lat, rate, force, session)
            show_history(session)
        else:
            hit = [s for s in SCENARIOS if s[0] == choice]
            if hit:
                _, name, svc, cpu, mem, lat, rate, force = hit[0]
                run_scenario(api, args, meta, name, svc, cpu, mem, lat, rate, force, session)
            else:
                print(f" {YEL}Unknown choice.{R}")
    if session:
        show_history(session)
    api.call("POST", "/api/topology/reset")
    print(f"\n {DIM}Twin reset. Bye.{R}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
