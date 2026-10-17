# Shift-right (self-healing) - what it is, what you can claim, what to say

The runtime loop: **telemetry → detect (Isolation Forest) → explain (KernelSHAP) → decide (RL policy ‖ Gemini ReAct) → gate (digital twin) → act (kubectl)**.
This page says exactly what each stage is, so you never claim more than the code supports.

## Component by component

| Stage | What it really is | Evidence | Claim you can make | Do NOT say |
|---|---|---|---|---|
| Detect | scikit-learn Isolation Forest trained on a healthy-telemetry CSV (4 features) | 5/5 injected faults flagged, healthy control not flagged; ~8-20 ms | "An unsupervised anomaly detector flags abnormal telemetry in milliseconds" | "high accuracy" - the faults are synthetic and extreme, and ~5 % of healthy samples are flagged by construction (contamination = 0.05) |
| Explain | KernelSHAP over the forest's anomaly score, healthy background sample | Top feature is `memory_usage` for the leak, `cpu_usage` for CPU faults | "It tells you which signal drove the alert" | "causal root cause" - SHAP shows contribution to the score, not causation |
| Decide (RL) | **Tabular Q-learning policy trained offline inside a fault simulator** (`agentic_engine/rl_training.py`); frozen and greedy at inference | `docs/rl_training_report.md`: held-out mean reward -0.095 vs -0.242 for "always restart" and -0.090 for the simulator oracle | "A baseline policy learned from simulated incidents: scale for surges/overload, restart for deadlocks/leaks, do nothing on false alarms" | "learned from real clusters", "federated", "adaptive online" (it does not learn online) |
| Decide (LLM) | Gemini (`gemini-3.6-flash`) given the SHAP summary and a twin forecast, returns JSON | Live calls, ~5-10 s, different answers per fault | "An LLM reasons over the evidence and proposes an action with an explanation" | "it understands the cluster" |
| Gate | Digital-twin sanity check (SimPy topology twin + the same fault model): blocks an action when the service is predicted to stay healthy (`NOT_NEEDED`), when the action would not relieve the predicted fault (`INEFFECTIVE`), or when it would overload a neighbour (`RISK_OF_OVERLOAD`); suggests an approved alternative | Unit tests (`tests/test_shift_right.py`): false alarm → NOT_NEEDED; restart on a surge, scale on a deadlock/leak → INEFFECTIVE | "No action runs unless a simulation says it is needed, effective and safe for neighbours" | "validated simulation", "M/M/c queueing model", "guarantees safety" - its effects are modelled assumptions |
| Act | `kubectl scale / delete pod / patch` with validated names, `shell=False`, replica bounds | Dry-run on VM1/laptop (no cluster attached); plan-only unless Execute is ticked | "Execution is opt-in, gated and validated" | "self-healed a cluster" unless you ran it against a live cluster |

## What the numbers do and do not show

- Everything in the console is measured per request on the server (detect ≈ 8-20 ms, SHAP ≈ 15-30 ms, RL ≈ 1 ms, Gemini ≈ 5-10 s).
- The RL and gate results are **inside a simulator whose dynamics I (the authors) encoded**. They show the policy is internally consistent and sensible; they do **not** show it would work on a real cluster.
- RL vs LLM agreement on the live run: surge ✔, cascade ✔; deadlock ✘ (Gemini says scale up, the gate marks that INEFFECTIVE and suggests restart); leak ✘ (RL restart, Gemini patch limits; the gate approves both).
- The gate used to approve everything (the earlier evaluation found it approved every false alarm). It now blocks false alarms, but the "effective for this fault" test uses the same fault model the RL was trained on, so the two are not independent.

## Good questions and honest answers

| Question | Answer |
|---|---|
| Is the RL real RL? | Yes: Q-learning with a reward (danger over a 10-step rollout minus an action cost). But it is single-step (a contextual bandit, γ = 0), trained offline on a simulator, and frozen at runtime. |
| Why not train on a real cluster? | Time, cost and safety: exploring restarts on a live system is risky. Next step is to log real incidents and fine-tune. |
| How do you know the simulator is right? | We don't. It encodes standard SRE heuristics (restart clears deadlocks and leaks, more replicas relieve load, a restart only briefly relieves a sustained surge). Validating it against real incident data is the main missing piece. |
| Why do RL and Gemini sometimes disagree? | They use different information and assumptions. Disagreement is surfaced; the gate then judges each proposal and can suggest the alternative. |
| What stops a bad action? | Plan-only by default; Execute needs a reachable cluster; the gate must approve; names are validated; replicas are bounded. |
| Is anything faked? | No. The console labels fallbacks, dry runs and assumptions. The earlier "paper" numbers were found to be fallback constants and were removed. |

## How to reproduce

```bash
python -m agentic_engine.rl_training                 # retrain; writes models/rl_qtable.json and docs/rl_training_report.md
python -m pytest tests/test_shift_right.py           # policy and gate behaviour
python scripts/demo_e2e.py --base http://127.0.0.1:8000
```
