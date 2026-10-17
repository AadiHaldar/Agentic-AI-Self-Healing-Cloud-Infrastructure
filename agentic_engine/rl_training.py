"""
agentic_engine/rl_training.py - offline training of the remediation policy.

The Q-learning agent is trained against a small FAULT-DYNAMICS SIMULATOR (below), not a real
cluster. The simulator encodes standard SRE failure-mode knowledge:

  surge     load-driven CPU saturation  -> more capacity helps; a restart only helps for ~2 steps
  deadlock  stuck threads, CPU pegged   -> a restart clears them; adding replicas does not
  leak      memory grows every step     -> a restart clears it; raising limits only delays OOM
  overload  cascading CPU + memory      -> scaling out helps most

so the learned policy is "what is best inside this simulator". It has NOT been validated on a real
cluster, and the simulator's numbers are assumptions. Each action also has a cost (a restart means
downtime, scaling costs resources), so doing nothing on a healthy service is the best action.

Run:  python -m agentic_engine.rl_training          (writes models/rl_qtable.json + docs/rl_training_report.md)
"""
import json
import os
import sys
import time
from typing import Dict, List, Tuple

import numpy as np

ACTIONS = ["DO_NOTHING", "SCALE_UP", "RESTART_POD", "PATCH_LIMITS"]
ACTION_COST = {"DO_NOTHING": 0.0, "SCALE_UP": 0.10, "RESTART_POD": 0.18, "PATCH_LIMITS": 0.08}
STEPS = 10

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "rl_qtable.json")
REPORT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "rl_training_report.md"))


# ── state discretisation (shared with SimiFedRLAgent) ────────────────────────

def bins(cpu: float, mem: float, lat: float, rate: float) -> Tuple[int, int, int, int]:
    c = 0 if cpu < 0.3 else 1 if cpu < 0.6 else 2 if cpu < 0.8 else 3 if cpu < 0.95 else 4
    m = 0 if mem < 0.5 else 1 if mem < 0.75 else 2 if mem < 0.9 else 3
    l = 0 if lat < 100 else 1 if lat < 1000 else 2
    r = 0 if rate < 20 else 1 if rate < 400 else 2
    return c, m, l, r


def state_key(cpu: float, mem: float, lat: float, rate: float, anomaly: bool) -> str:
    c, m, l, r = bins(cpu, mem, lat, rate)
    return f"c{c}_m{m}_l{l}_r{r}_a{int(anomaly)}"


# ── fault-dynamics simulator ─────────────────────────────────────────────────

def classify(cpu: float, mem: float, lat: float, rate: float) -> str:
    if cpu >= 0.9 and rate < 50:
        return "deadlock"
    if mem >= 0.85 and cpu < 0.6:
        return "leak"
    if rate >= 400 and cpu >= 0.8:
        return "surge"
    if cpu >= 0.8 or mem >= 0.8:
        return "overload"
    return "healthy"


def _danger(cpu: float, mem: float) -> float:
    """Penalty for being near saturation: hard above 0.8 CPU / 0.85 memory, plus a soft headroom term."""
    d = max(0.0, cpu - 0.8) * 2.0 + max(0.0, mem - 0.85) * 3.0
    d += 0.6 * max(0.0, cpu - 0.6) + 0.6 * max(0.0, mem - 0.7)
    if mem >= 0.99:
        d += 1.0  # out-of-memory kill
    return d


def rollout(cpu0: float, mem0: float, lat: float, rate: float, action: str, steps: int = STEPS) -> float:
    """Total danger over the horizon for one action under the simulated fault."""
    kind = classify(cpu0, mem0, lat, rate)
    total = 0.0
    for t in range(1, steps + 1):
        cpu, mem = cpu0, mem0
        if kind == "healthy":
            pass
        elif kind == "surge":
            if action == "SCALE_UP":
                cpu = cpu0 * (0.7 if t == 1 else 0.34)           # new replicas need a step to warm up
            elif action == "RESTART_POD":
                cpu = cpu0 * (0.3 if t <= 2 else 1.0)            # cold start relief, then the load returns
            elif action == "PATCH_LIMITS":
                cpu = cpu0 / 1.25                                # a higher CPU limit only helps if the pod is throttled
        elif kind == "deadlock":
            cpu = 0.99
            if action == "RESTART_POD":
                cpu = 0.35                                       # restart clears the stuck threads
            elif action == "SCALE_UP":
                cpu = 0.97                                       # the stuck pod stays stuck
        elif kind == "leak":
            grown = mem0 + 0.035 * t
            mem = grown
            if action == "RESTART_POD":
                mem = 0.30 + 0.035 * t
            elif action == "PATCH_LIMITS":
                mem = grown / 1.2                                # higher limit delays, does not fix
            elif action == "SCALE_UP":
                mem = grown                                      # every replica leaks the same way
        elif kind == "overload":
            if action == "SCALE_UP":
                cpu, mem = cpu0 * 0.4, mem0 * 0.7
            elif action == "RESTART_POD":
                cpu, mem = cpu0 * (0.3 if t <= 2 else 1.0), mem0 * 0.4
            elif action == "PATCH_LIMITS":
                cpu, mem = cpu0 * 0.8, mem0 * 0.8
        total += _danger(min(cpu, 1.0), min(mem, 1.0))
    return total / steps


def reward(cpu: float, mem: float, lat: float, rate: float, action: str) -> float:
    return -rollout(cpu, mem, lat, rate, action) - ACTION_COST[action]


# ── scenario sampling ────────────────────────────────────────────────────────

def sample_state(rng: np.random.Generator) -> Tuple[float, float, float, float, bool]:
    """Draw a telemetry state plus the anomaly-detector flag. Mixture of healthy, false alarms, the four faults, and uniform noise."""
    u = rng.random()
    if u < 0.22:        # healthy, correctly not flagged
        return (rng.normal(0.25, 0.06), rng.normal(0.40, 0.08), rng.normal(45, 6), rng.normal(120, 15), False)
    if u < 0.30:        # false alarm: healthy telemetry the detector flagged
        return (rng.normal(0.25, 0.06), rng.normal(0.40, 0.08), rng.normal(45, 6), rng.normal(120, 15), True)
    if u < 0.42:        # surge
        return (rng.uniform(0.85, 1.0), rng.uniform(0.3, 0.6), rng.uniform(250, 900), rng.uniform(420, 1500), True)
    if u < 0.54:        # deadlock
        return (rng.uniform(0.93, 1.0), rng.uniform(0.5, 0.9), rng.uniform(1500, 6000), rng.uniform(0, 15), True)
    if u < 0.66:        # leak
        return (rng.uniform(0.05, 0.45), rng.uniform(0.86, 0.99), rng.uniform(30, 120), rng.uniform(60, 200), True)
    if u < 0.78:        # cascading overload
        return (rng.uniform(0.8, 0.93), rng.uniform(0.7, 0.9), rng.uniform(200, 700), rng.uniform(100, 380), True)
    # uniform coverage so every state bucket is visited
    return (rng.uniform(0.05, 1.0), rng.uniform(0.1, 1.0), rng.uniform(20, 5000), rng.uniform(0, 1500), bool(rng.random() < 0.7))


def _clip(s):
    cpu, mem, lat, rate, a = s
    return float(np.clip(cpu, 0.02, 1.0)), float(np.clip(mem, 0.02, 1.0)), float(max(lat, 1.0)), float(max(rate, 0.0)), a


# ── training ─────────────────────────────────────────────────────────────────

def train(episodes: int = 120_000, alpha: float = 0.08, seed: int = 7) -> Dict[str, List[float]]:
    rng = np.random.default_rng(seed)
    q: Dict[str, np.ndarray] = {}
    for ep in range(episodes):
        eps = max(0.05, 0.4 * (1 - ep / episodes))
        cpu, mem, lat, rate, anomaly = _clip(sample_state(rng))
        k = state_key(cpu, mem, lat, rate, anomaly)
        if k not in q:
            q[k] = np.zeros(len(ACTIONS))
        a = int(rng.integers(len(ACTIONS))) if rng.random() < eps else int(np.argmax(q[k]))
        r = reward(cpu, mem, lat, rate, ACTIONS[a])
        # one decision per episode, so there is no next state (gamma = 0): a contextual-bandit Q update
        q[k][a] += alpha * (r - q[k][a])
    return {k: [round(float(x), 5) for x in v] for k, v in q.items()}


def policy_action(table: Dict[str, List[float]], cpu, mem, lat, rate, anomaly) -> str:
    v = table.get(state_key(cpu, mem, lat, rate, anomaly))
    return ACTIONS[int(np.argmax(v))] if v else "DO_NOTHING"


def evaluate(table: Dict[str, List[float]], n: int = 6000, seed: int = 99) -> Dict[str, Dict]:
    """Held-out episodes (different seed). Mean reward per policy, overall and per fault class."""
    rng = np.random.default_rng(seed)
    policies = {
        "trained policy": lambda s: policy_action(table, *s),
        "always RESTART_POD": lambda s: "RESTART_POD" if s[4] else "DO_NOTHING",
        "always SCALE_UP": lambda s: "SCALE_UP" if s[4] else "DO_NOTHING",
        "restart on every anomaly flag, random otherwise": lambda s: "RESTART_POD" if s[4] else ACTIONS[int(rng.integers(4))],
        "do nothing": lambda s: "DO_NOTHING",
        "oracle (best action in the simulator)": lambda s: max(ACTIONS, key=lambda a: reward(s[0], s[1], s[2], s[3], a)),
    }
    states = [_clip(sample_state(rng)) for _ in range(n)]
    out: Dict[str, Dict] = {}
    for name, fn in policies.items():
        by_kind: Dict[str, List[float]] = {}
        total = []
        for s in states:
            r = reward(s[0], s[1], s[2], s[3], fn(s))
            total.append(r)
            by_kind.setdefault(classify(*s[:4]), []).append(r)
        out[name] = {"mean": float(np.mean(total)), **{k: float(np.mean(v)) for k, v in by_kind.items()}}
    # per-class action chosen by the trained policy
    chosen: Dict[str, Dict[str, int]] = {}
    for s in states:
        if s[4]:
            kind = classify(*s[:4])
            chosen.setdefault(kind, {})
            a = policy_action(table, *s)
            chosen[kind][a] = chosen[kind].get(a, 0) + 1
    out["_chosen"] = chosen
    return out


def write_report(table: Dict, results: Dict, episodes: int) -> None:
    kinds = ["healthy", "surge", "deadlock", "leak", "overload"]
    lines = [
        "# RL policy training report", "",
        f"Generated by `python -m agentic_engine.rl_training` ({time.strftime('%Y-%m-%d')}). "
        f"Tabular Q-learning, {episodes:,} episodes, {len(table)} visited states.", "",
        "**What this is:** the policy is trained inside a *fault-dynamics simulator* (`agentic_engine/rl_training.py`) that encodes "
        "assumed failure-mode behaviour. It is **not** validated on a real cluster, and the simulator's numbers are assumptions.", "",
        "## Held-out results (6,000 simulated episodes, mean reward, higher is better)", "",
        "| Policy | overall | " + " | ".join(kinds) + " |", "|---|---:|" + "---:|" * len(kinds),
    ]
    for name, r in results.items():
        if name.startswith("_"):
            continue
        lines.append(f"| {name} | {r['mean']:.3f} | " + " | ".join(f"{r.get(k, float('nan')):.3f}" for k in kinds) + " |")
    lines += ["", "## Actions the trained policy picks when the detector flags an anomaly", "",
              "| Fault class | action counts |", "|---|---|"]
    for k in kinds:
        c = results["_chosen"].get(k, {})
        lines.append(f"| {k} | " + ", ".join(f"{a}: {n}" for a, n in sorted(c.items(), key=lambda x: -x[1])) + " |")
    lines += ["", "A `healthy` row with actions other than DO_NOTHING would mean the policy acts on false alarms; "
              "the training reward charges a cost for every action, so it should not.", ""]
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main() -> int:
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 120_000
    t0 = time.time()
    table = train(episodes)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "w", encoding="utf-8") as fh:
        json.dump({"episodes": episodes, "actions": ACTIONS, "trained_on": "fault-dynamics simulator (assumed dynamics)", "q": table}, fh)
    results = evaluate(table)
    write_report(table, results, episodes)
    print(f"trained {episodes:,} episodes in {time.time() - t0:.1f}s, {len(table)} states -> {MODEL_PATH}")
    for name, r in results.items():
        if not name.startswith("_"):
            print(f"  {name:<50} overall {r['mean']:+.3f}")
    for k, c in results["_chosen"].items():
        print(f"  flagged {k:<9} ->", dict(sorted(c.items(), key=lambda x: -x[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
