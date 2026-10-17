import logging
from typing import Dict, Any
from digital_twin.simpy_engine import SimPyDigitalTwin
from digital_twin.topology_graph import TopologyGraph
from agentic_engine import rl_training

logger = logging.getLogger(__name__)

class SimPySimulationTools:
    """
    Exposes dry-run capabilities to the AI agent via the SimPy Digital Twin.
    Runs genuine action-dependent dry-run simulations before applying to K8s.
    """
    def __init__(self, topology: TopologyGraph):
        self.topology = topology

    # Gate thresholds
    DANGER_CPU = 0.85          # without intervention the twin must predict CPU at/above this ...
    DANGER_MEM = 0.88          # ... or memory at/above this, otherwise acting is unnecessary
    MIN_IMPROVEMENT = 0.15     # the action must cut the resource pressure by at least 15 %
    NEIGHBOUR_CEILING = 0.90   # a neighbour may not be pushed past this, unless it grows <= 25 %
    MIN_FAULT_IMPROVEMENT = 0.30  # fault-aware check: the action must remove >= 30 % of the predicted danger
    _ACTION_MAP = {"SCALE": "SCALE_UP", "RESTART": "RESTART_POD", "PATCH": "PATCH_LIMITS"}

    def _run(self, target: str, action_type=None):
        twin = SimPyDigitalTwin(self.topology)
        if action_type:
            twin.apply_remediation_action(target, action_type)
        twin.initialize_simulation()
        return twin.run_simulation(until=10)

    def simulate_remediation(self, action_type: str, target: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Dry-run an action in the digital twin and compare it with doing nothing.
        `action_type`: 'SCALE', 'RESTART', 'PATCH'

        Verdicts (`recommendation`; `is_safe` is True only for SAFE_TO_EXECUTE):
          TARGET_NOT_IN_TWIN  the service is unknown to the twin
          NOT_NEEDED          the twin predicts the service stays healthy WITHOUT intervention (blocks false alarms)
          RISK_OF_OVERLOAD    a neighbouring service would be pushed into overload
          INEFFECTIVE         the action would not reduce resource pressure by MIN_IMPROVEMENT
          SAFE_TO_EXECUTE     the service is in danger, the action helps, and neighbours stay safe
        The twin applies fixed per-action effects, so this is a sanity check, not a calibrated simulation.
        """
        logger.info(f"[SimPyTools] Simulating action '{action_type}' on target '{target}'...")

        if not self.topology.graph.has_node(target):
            return {
                "action_type": action_type, "target": target, "simulation_steps": 0, "is_safe": False,
                "predicted_max_cpu": None, "predicted_cpu": {}, "blast_radius": [],
                "recommendation": "TARGET_NOT_IN_TWIN", "reason": "The service is not in the digital twin.",
            }

        baseline = self._run(target, None)
        history = self._run(target, action_type)

        t_base, t_act = baseline.get(target) or [], history.get(target) or []
        if not t_base or not t_act:
            return {
                "action_type": action_type, "target": target, "simulation_steps": 0, "is_safe": False,
                "predicted_max_cpu": None, "predicted_cpu": {}, "blast_radius": [],
                "recommendation": "TARGET_NOT_IN_TWIN", "reason": "The twin has no pod state for this service.",
            }
        base_peak_cpu = max(h["cpu"] for h in t_base)
        base_peak_mem = max(h["memory"] for h in t_base)
        base_final, act_final = t_base[-1], t_act[-1]
        in_danger = base_peak_cpu >= self.DANGER_CPU or base_peak_mem >= self.DANGER_MEM

        radius = [target] + [
            n for n in (self.topology.get_dependencies(target) + self.topology.get_dependents(target)) if n != target
        ]
        predicted: Dict[str, float] = {}
        neighbour_risk = False
        for pod in radius:
            ph = history.get(pod)
            if not ph:
                continue
            initial_cpu, final_cpu = ph[0]["cpu"], ph[-1]["cpu"]
            predicted[pod] = round(final_cpu, 4)
            if pod != target and not (final_cpu < self.NEIGHBOUR_CEILING or final_cpu <= initial_cpu * 1.25):
                neighbour_risk = True

        pressure = lambda h: max(h["cpu"] / self.DANGER_CPU, h["memory"] / self.DANGER_MEM)  # noqa: E731
        improvement = (pressure(base_final) - pressure(act_final)) / max(pressure(base_final), 1e-9)

        # Fault-aware check (when latency and request rate are known): what kind of fault is this, and does THIS
        # action actually relieve it? e.g. a restart only helps a surge for a couple of steps, and extra replicas
        # do not clear a deadlocked pod. Uses the same fault-dynamics model the RL policy is trained on.
        fault_kind, fault_improvement = None, None
        p = params or {}
        if p.get("latency_ms") is not None and p.get("request_rate") is not None and action_type.upper() in self._ACTION_MAP:
            cpu0 = p.get("cpu", t_base[0]["cpu"])
            mem0 = p.get("memory", t_base[0]["memory"])
            fault_kind = rl_training.classify(cpu0, mem0, p["latency_ms"], p["request_rate"])
            d0 = rl_training.rollout(cpu0, mem0, p["latency_ms"], p["request_rate"], "DO_NOTHING")
            d1 = rl_training.rollout(cpu0, mem0, p["latency_ms"], p["request_rate"], self._ACTION_MAP[action_type.upper()])
            fault_improvement = (d0 - d1) / d0 if d0 > 1e-6 else 0.0
            if fault_kind == "healthy":
                in_danger = False

        if not in_danger:
            verdict, reason = "NOT_NEEDED", (
                f"Without intervention the twin predicts {target} stays healthy (peak CPU {base_peak_cpu:.0%}, memory {base_peak_mem:.0%}).")
        elif neighbour_risk:
            verdict, reason = "RISK_OF_OVERLOAD", "The action would push a neighbouring service into overload."
        elif fault_improvement is not None and fault_improvement < self.MIN_FAULT_IMPROVEMENT:
            verdict, reason = "INEFFECTIVE", (
                f"For a {fault_kind} fault, {action_type.upper()} is predicted to remove only {max(fault_improvement, 0):.0%} of the danger "
                f"(needs at least {self.MIN_FAULT_IMPROVEMENT:.0%}).")
        elif improvement < self.MIN_IMPROVEMENT:
            verdict, reason = "INEFFECTIVE", f"The action would reduce resource pressure by only {improvement:.0%}."
        else:
            verdict, reason = "SAFE_TO_EXECUTE", (
                f"{target} is predicted to stay under pressure without action; the action cuts pressure by {improvement:.0%} "
                f"and neighbours stay safe.")

        return {
            "action_type": action_type,
            "target": target,
            "simulation_steps": 10,
            "is_safe": verdict == "SAFE_TO_EXECUTE",
            "predicted_max_cpu": round(max(predicted.values()), 4) if predicted else 0.0,
            "predicted_cpu": predicted,
            "predicted_memory": round(act_final["memory"], 4),
            "baseline": {"final_cpu": round(base_final["cpu"], 4), "final_memory": round(base_final["memory"], 4),
                         "peak_cpu": round(base_peak_cpu, 4), "peak_memory": round(base_peak_mem, 4)},
            "improvement": round(improvement, 4),
            "fault_kind": fault_kind,
            "fault_improvement": None if fault_improvement is None else round(fault_improvement, 4),
            "blast_radius": radius,
            "recommendation": verdict,
            "reason": reason,
        }

    def suggest_alternative(self, target: str, params: Dict[str, Any] = None, exclude: str = None) -> Dict[str, Any]:
        """The gate's own recommendation: among the other actions, the approved one that removes the most danger."""
        best = None
        for act in ("SCALE", "RESTART", "PATCH"):
            if exclude and act == str(exclude).upper().replace("_UP", "").replace("_POD", "").replace("_LIMITS", ""):
                continue
            r = self.simulate_remediation(act, target, params)
            if r["is_safe"]:
                score = r.get("fault_improvement") if r.get("fault_improvement") is not None else r["improvement"]
                if best is None or score > best[0]:
                    best = (score, act, r)
        if not best:
            return {"action": None}
        return {"action": self._ACTION_MAP[best[1]], "improvement": round(best[0], 4), "reason": best[2]["reason"]}

    def evaluate_action_matrix(self, target: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Runs multi-action matrix dry-runs (SCALE vs RESTART vs PATCH) concurrently in SimPy Digital Twin.
        Returns safety scores and optimal choice for the Gemini LLM agent.
        """
        logger.info(f"[SimPyTools] Running Multi-Action Safety Matrix Dry-Run for '{target}'...")
        results = {}
        for act in ["SCALE", "RESTART", "PATCH"]:
            results[act] = self.simulate_remediation(action_type=act, target=target, params=params)

        # Select safest action with lowest predicted max CPU
        best_action = min(results.keys(), key=lambda a: results[a]["predicted_max_cpu"])
        
        return {
            "target": target,
            "matrix": results,
            "recommended_action": best_action,
            "best_safety_score": round(1.0 - results[best_action]["predicted_max_cpu"], 4)
        }
