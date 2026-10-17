"""
scripts/run_evaluation.py

Measures the AgentHeal runtime pipeline on four injected fault scenarios plus a
healthy control, and writes docs/paper/eval_results.json.

Every number in the output comes from this script running the real components
(Isolation Forest, KernelSHAP, SimiFed Q-agent, SimPy safety gate and, when
GEMINI_API_KEY is set, the live Gemini agent). Nothing is hard-coded and there
is no fallback: if a stage raises, the script exits non-zero and writes nothing.

What is NOT measured here (and is therefore not reported): Kubernetes actuation
time (no cluster is driven), and any HPA/Keptn baseline.

Usage:
    PYTHONPATH=. python scripts/run_evaluation.py [--trials 15] [--llm-trials 5]
                                                  [--control-samples 1000] [--seed 0]
"""
import argparse
import datetime
import json
import logging
import math
import os
import platform
import statistics
import sys
import time
import warnings

os.environ.setdefault("TQDM_DISABLE", "1")  # silence shap progress bars
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

import numpy as np  # noqa: E402

FEATURES = ["cpu_usage", "memory_usage", "latency_ms", "request_rate"]
HEALTHY_SERVICES = ["frontend", "checkoutservice", "cartservice", "paymentservice", "emailservice", "redis-cart"]
# Online Boutique call graph subset used for the twin: caller -> callee
EDGES = [
    ("frontend", "checkoutservice"), ("frontend", "cartservice"),
    ("checkoutservice", "cartservice"), ("checkoutservice", "paymentservice"),
    ("checkoutservice", "emailservice"), ("cartservice", "redis-cart"),
]
HEALTHY_POD = {"cpu_usage": 0.25, "memory_usage": 0.40}  # means of datasets/healthy_telemetry.csv

SCENARIOS = [
    {"id": "S1", "name": "Flash Sale Surge",  "svc": "checkoutservice", "cpu": 0.954, "ram": 0.45,  "lat": 450.0,  "rate": 500.0},
    {"id": "S2", "name": "Thread Deadlock",   "svc": "cartservice",     "cpu": 0.99,  "ram": 0.85,  "lat": 5000.0, "rate": 0.0},
    {"id": "S3", "name": "Memory Leak",       "svc": "redis-cart",      "cpu": 0.15,  "ram": 0.942, "lat": 48.0,   "rate": 110.0},
    {"id": "S4", "name": "Cascading Overload", "svc": "frontend",       "cpu": 0.88,  "ram": 0.80,  "lat": 320.0,  "rate": 250.0},
]

RL_TO_SIM = {"SCALE_UP": "SCALE", "RESTART_POD": "RESTART", "PATCH_LIMITS": "PATCH", "DO_NOTHING": "DO_NOTHING"}
JITTER = 0.03  # relative (multiplicative) Gaussian jitter applied to every feature per trial


def stats(data):
    if not data:
        return {"mean": None, "std": None, "p95": None, "n": 0}
    return {
        "mean": statistics.mean(data),
        "std": statistics.stdev(data) if len(data) > 1 else 0.0,
        "p95": float(np.percentile(data, 95)),
        "n": len(data),
    }


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


def build_topology(target_svc=None, cpu=None, mem=None):
    """Healthy Online Boutique twin; the target pod (if any) carries the injected cpu/mem."""
    from digital_twin.topology_graph import TopologyGraph
    topo = TopologyGraph()
    for s in HEALTHY_SERVICES:
        attrs = dict(HEALTHY_POD)
        if s == target_svc:
            attrs = {"cpu_usage": cpu, "memory_usage": mem}
        topo.update_node(f"{s}-pod", "pod", attrs)
    for a, b in EDGES:
        topo.add_dependency(f"{a}-pod", f"{b}-pod")
    return topo


def make_components():
    from detection.anomaly.isolation_forest import MetricsAnomalyDetector
    from detection.explainer.shap_explainer import SHAPExplainer
    from agentic_engine.rl_agent import SimiFedRLAgent
    detector = MetricsAnomalyDetector()
    if not detector.is_trained:
        raise RuntimeError("Isolation Forest is untrained: datasets/healthy_telemetry.csv missing")
    explainer = SHAPExplainer(detector.model)
    rl = SimiFedRLAgent(epsilon=0.0)  # greedy inference; exploration is a training-time concern
    return detector, explainer, rl


def detect(detector, x):
    t0 = time.perf_counter()
    pred = detector.predict(x)
    score = float(detector.model.decision_function(x.reshape(1, -1))[0])
    return bool(pred[0] == -1), score, (time.perf_counter() - t0) * 1000


def run_scenario(sc, detector, explainer, rl, n_trials, llm_trials, rng):
    from agentic_engine.tools.simpy_tools import SimPySimulationTools
    from agentic_engine.tools.k8s_tools import K8sRemediationTools
    from agentic_engine.llm_agent import LLMReActAgent

    target = f"{sc['svc']}-pod"
    base = np.array([sc["cpu"], sc["ram"], sc["lat"], sc["rate"]], dtype=np.float64)

    # Gate counterfactuals on the un-jittered fault: does the gate actually see the injected load?
    topo0 = build_topology(sc["svc"], sc["cpu"], sc["ram"])
    sim0 = SimPySimulationTools(topo0)
    gate_matrix = {}
    for act in ["DO_NOTHING", "SCALE", "RESTART", "PATCH"]:
        r = sim0.simulate_remediation(act, target)
        gate_matrix[act] = {"is_safe": r["is_safe"], "predicted_target_cpu": r["predicted_cpu"].get(target),
                            "recommendation": r["recommendation"]}

    llm_agent = None
    if llm_trials > 0:
        llm_agent = LLMReActAgent(K8sRemediationTools(), sim0)

    rec = {k: [] for k in ["detect_ms", "score", "shap_ms", "rl_ms", "gate_ms", "compute_ms",
                           "gate_target_cpu", "llm_s", "loop_with_llm_s"]}
    shap_sum = {f: [] for f in FEATURES}
    rl_actions, gate_safe, detected = [], [], 0
    llm_rows = []

    for trial in range(n_trials):
        x = base.copy() if trial == 0 else base * rng.normal(1.0, JITTER, size=4)
        x[0] = min(max(x[0], 0.01), 1.0)
        x[1] = min(max(x[1], 0.01), 1.0)
        x[2:] = np.maximum(x[2:], 0.0)
        x32 = x.astype(np.float32)

        t_start = time.perf_counter()
        is_anom, score, d_ms = detect(detector, x32)
        rec["detect_ms"].append(d_ms)
        rec["score"].append(score)
        if not is_anom:
            continue
        detected += 1

        t0 = time.perf_counter()
        phi = explainer.explain_instance(x32)
        rec["shap_ms"].append((time.perf_counter() - t0) * 1000)
        for f in FEATURES:
            shap_sum[f].append(phi[f])

        t0 = time.perf_counter()
        d = rl.decide_remediation(target, float(x[0]), float(x[1]), True,
                                  latency_ms=float(x[2]), request_rate=float(x[3]))
        rec["rl_ms"].append((time.perf_counter() - t0) * 1000)
        rl_actions.append(d["action"])

        # Seed the twin with this trial's injected cpu/mem so the gate sees the fault.
        topo = build_topology(sc["svc"], float(x[0]), float(x[1]))
        sim = SimPySimulationTools(topo)
        t0 = time.perf_counter()
        g = sim.simulate_remediation(RL_TO_SIM[d["action"]], target)
        rec["gate_ms"].append((time.perf_counter() - t0) * 1000)
        gate_safe.append(g["is_safe"])
        rec["gate_target_cpu"].append(g["predicted_cpu"].get(target))
        compute_ms = (time.perf_counter() - t_start) * 1000
        rec["compute_ms"].append(compute_ms)

        if llm_agent is not None and len(llm_rows) < llm_trials:
            ctx = {"target_service": target, "cpu_usage": float(x[0]), "mem_usage": float(x[1]),
                   "shap_explanation": explainer.format_explanation_for_llm(phi), "is_anomaly": True}
            llm_agent.sim_tools = sim
            t0 = time.perf_counter()
            out = llm_agent.evaluate_and_heal(ctx, execute=False)
            llm_s = time.perf_counter() - t0
            row = {"source": out.get("source"), "llm_s": llm_s, "rl_action": d["action"],
                   "llm_action": out.get("proposed_action"), "llm_gate_safe": out["simulation"].get("is_safe")}
            llm_rows.append(row)

    # Aggregate
    shap_mean = {f: (statistics.mean(v) if v else None) for f, v in shap_sum.items()}
    dominant = max(shap_mean, key=lambda f: abs(shap_mean[f])) if all(v is not None for v in shap_mean.values()) else None
    live = [r for r in llm_rows if str(r["source"]).startswith("gemini")]
    llm_block = {
        "attempted": len(llm_rows),
        "gemini_responses": len(live),
        "fallback_responses": len(llm_rows) - len(live),
        "latency_s": stats([r["llm_s"] for r in live]),
        "agree_with_rl": sum(1 for r in live if r["llm_action"] == r["rl_action"]),
        "llm_actions": sorted({str(r["llm_action"]) for r in live}),
        "sources": sorted({str(r["source"]) for r in llm_rows}),
    }
    for r in live:
        rec["loop_with_llm_s"].append(statistics.mean(rec["compute_ms"]) / 1000 + r["llm_s"])

    return {
        "scenario_id": sc["id"], "scenario_name": sc["name"], "target": target,
        "injected": {"cpu": sc["cpu"], "ram": sc["ram"], "latency_ms": sc["lat"], "request_rate": sc["rate"]},
        "n_trials": n_trials,
        "detection_rate": detected / n_trials,
        "detection_latency_ms": stats(rec["detect_ms"]),
        "anomaly_score": stats(rec["score"]),
        "shap_ms": stats(rec["shap_ms"]),
        "shap_mean_phi": shap_mean,
        "shap_dominant_feature": dominant,
        "rl_latency_ms": stats(rec["rl_ms"]),
        "rl_action_counts": {a: rl_actions.count(a) for a in sorted(set(rl_actions))},
        "gate_ms": stats(rec["gate_ms"]),
        "gate_predicted_target_cpu": stats([c for c in rec["gate_target_cpu"] if c is not None]),
        "gate_approval_rate": (sum(gate_safe) / len(gate_safe)) if gate_safe else None,
        "gate_counterfactual": gate_matrix,
        "compute_ms": stats(rec["compute_ms"]),
        "llm": llm_block,
        "loop_with_llm_s": stats(rec["loop_with_llm_s"]),
    }


def healthy_control(detector, rl, n, seed):
    """Fresh healthy telemetry (same generator distribution as the training set, different seed)."""
    import pandas as pd
    from agentic_engine.tools.simpy_tools import SimPySimulationTools
    rng = np.random.default_rng(seed + 1)
    X = np.column_stack([
        np.clip(rng.normal(0.25, 0.05, n), 0.05, 0.50),
        np.clip(rng.normal(0.40, 0.08, n), 0.10, 0.65),
        np.clip(rng.normal(45.0, 5.0, n), 20.0, 80.0),
        np.clip(rng.normal(120.0, 15.0, n), 50.0, 200.0),
    ]).astype(np.float32)
    flagged = detector.predict(X) == -1
    k = int(flagged.sum())

    train = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "datasets", "healthy_telemetry.csv"))
    tr_flag = int((detector.predict(train[FEATURES].values.astype(np.float32)) == -1).sum())

    # What would the pipeline do on a false alarm? RL picks an action, the gate judges it.
    approved, actions = 0, []
    for i in np.where(flagged)[0]:
        svc = HEALTHY_SERVICES[i % len(HEALTHY_SERVICES)]
        topo = build_topology(svc, float(X[i, 0]), float(X[i, 1]))
        d = rl.decide_remediation(f"{svc}-pod", float(X[i, 0]), float(X[i, 1]), True,
                                  latency_ms=float(X[i, 2]), request_rate=float(X[i, 3]))
        actions.append(d["action"])
        g = SimPySimulationTools(topo).simulate_remediation(RL_TO_SIM[d["action"]], f"{svc}-pod")
        approved += int(g["is_safe"])
    return {
        "n_samples": n,
        "false_positives": k,
        "false_positive_rate": k / n,
        "fpr_wilson95": wilson(k, n),
        "training_set_flag_rate": tr_flag / len(train),
        "training_set_n": len(train),
        "false_alarm_rl_actions": {a: actions.count(a) for a in sorted(set(actions))},
        "false_alarms_approved_by_gate": approved,
    }


def _round(o, nd=6):
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, dict):
        return {k: _round(v, nd) for k, v in o.items()}
    if isinstance(o, list):
        return [_round(v, nd) for v in o]
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=15)
    ap.add_argument("--llm-trials", type=int, default=5, help="live Gemini calls per scenario (0 = skip)")
    ap.add_argument("--control-samples", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), '..', 'docs', 'paper', 'eval_results.json'))
    args = ap.parse_args()

    np.random.seed(args.seed)
    rng = np.random.default_rng(args.seed)

    llm_trials = args.llm_trials
    has_key = bool(os.getenv("GEMINI_API_KEY"))
    if llm_trials > 0 and not has_key:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
        has_key = bool(os.getenv("GEMINI_API_KEY"))
    if llm_trials > 0 and not has_key:
        print("GEMINI_API_KEY not set: skipping live LLM measurements (llm.attempted will be 0)")
        llm_trials = 0

    print("=" * 64)
    print(f"AgentHeal evaluation  trials={args.trials} llm_trials={llm_trials} control={args.control_samples} seed={args.seed}")
    print("=" * 64)

    detector, explainer, rl = make_components()
    # warm-up so first-call import/JIT cost is not attributed to scenario S1
    detect(detector, np.array([0.25, 0.4, 45.0, 120.0], dtype=np.float32))
    explainer.explain_instance(np.array([0.25, 0.4, 45.0, 120.0], dtype=np.float32))

    results = []
    for sc in SCENARIOS:
        print(f"\n[{sc['id']}] {sc['name']} ...", flush=True)
        r = run_scenario(sc, detector, explainer, rl, args.trials, llm_trials, rng)
        results.append(r)
        print(f"  detect {r['detection_latency_ms']['mean']:.2f} ms | rate {r['detection_rate']*100:.0f}% | "
              f"SHAP {r['shap_ms']['mean']} ms | RL {r['rl_latency_ms']['mean']} ms | gate {r['gate_ms']['mean']} ms | "
              f"compute {r['compute_ms']['mean']} ms | dominant {r['shap_dominant_feature']}")
        if r["llm"]["attempted"]:
            print(f"  LLM: {r['llm']['gemini_responses']}/{r['llm']['attempted']} live, "
                  f"agree {r['llm']['agree_with_rl']}, latency {r['llm']['latency_s']['mean']}")

    print("\n[H0] Healthy control ...", flush=True)
    ctrl = healthy_control(detector, rl, args.control_samples, args.seed)
    print(f"  FPR {ctrl['false_positive_rate']*100:.1f}% ({ctrl['false_positives']}/{ctrl['n_samples']}), "
          f"gate approved {ctrl['false_alarms_approved_by_gate']} of those false alarms")

    det_all = [r["detection_rate"] for r in results]
    live_n = sum(r["llm"]["gemini_responses"] for r in results)
    out = {
        "meta": {
            "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "script": "scripts/run_evaluation.py",
            "args": {"trials": args.trials, "llm_trials": llm_trials, "control_samples": args.control_samples, "seed": args.seed},
            "host": {"platform": platform.platform(), "processor": platform.processor(),
                     "cpu_count": os.cpu_count(), "python": platform.python_version()},
            "definitions": {
                "detection_latency_ms": "Isolation Forest predict + decision_function wall time for one vector (inference latency, not time-to-detect on a live stream)",
                "compute_ms": "detect + KernelSHAP + RL decision + SimPy gate, perf_counter wall time; excludes LLM, actuation",
                "loop_with_llm_s": "mean compute_ms plus each live Gemini call latency",
                "actuation": "NOT MEASURED - no Kubernetes cluster is driven by this script",
            },
            "gemini_model_candidates": [m for m in [os.getenv("GEMINI_MODEL"), "gemini-3.6-flash", "gemini-3.8-flash"] if m],
            "rl_epsilon": 0.0,
            "jitter_relative_sigma": JITTER,
        },
        "scenarios": results,
        "healthy_control": ctrl,
        "aggregate": {
            "total_fault_trials": args.trials * len(results),
            "detection_rate": statistics.mean(det_all),
            "detection_latency_ms_mean_of_means": statistics.mean(r["detection_latency_ms"]["mean"] for r in results),
            "shap_ms_mean_of_means": statistics.mean(r["shap_ms"]["mean"] for r in results),
            "rl_ms_mean_of_means": statistics.mean(r["rl_latency_ms"]["mean"] for r in results),
            "gate_ms_mean_of_means": statistics.mean(r["gate_ms"]["mean"] for r in results),
            "compute_ms_mean_of_means": statistics.mean(r["compute_ms"]["mean"] for r in results),
            "gate_approval_rate": statistics.mean(r["gate_approval_rate"] for r in results),
            "llm_live_responses": live_n,
            "llm_agree_with_rl": sum(r["llm"]["agree_with_rl"] for r in results),
            "llm_latency_s_mean": (statistics.mean(x for r in results if r["llm"]["latency_s"]["mean"] is not None
                                                   for x in [r["llm"]["latency_s"]["mean"]]) if live_n else None),
        },
    }
    out_path = os.path.abspath(args.out)
    with open(out_path, "w") as f:
        json.dump(_round(out), f, indent=2)
    print(f"\nResults saved to: {out_path}")
    return out


if __name__ == "__main__":
    main()
