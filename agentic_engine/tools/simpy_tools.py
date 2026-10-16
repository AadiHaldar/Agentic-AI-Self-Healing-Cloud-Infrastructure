import logging
from typing import Dict, Any
from digital_twin.simpy_engine import SimPyDigitalTwin
from digital_twin.topology_graph import TopologyGraph

logger = logging.getLogger(__name__)

class SimPySimulationTools:
    """
    Exposes dry-run capabilities to the AI agent via the SimPy Digital Twin.
    Runs genuine action-dependent dry-run simulations before applying to K8s.
    """
    def __init__(self, topology: TopologyGraph):
        self.topology = topology

    def simulate_remediation(self, action_type: str, target: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Simulate an action against the in-memory Digital Twin.
        `action_type`: 'SCALE', 'RESTART', 'PATCH'
        """
        logger.info(f"[SimPyTools] Simulating action '{action_type}' on target '{target}'...")

        if not self.topology.graph.has_node(target):
            return {
                "action_type": action_type,
                "target": target,
                "simulation_steps": 0,
                "is_safe": False,
                "predicted_max_cpu": None,
                "blast_radius": [],
                "recommendation": "TARGET_NOT_IN_TWIN",
            }

        twin = SimPyDigitalTwin(self.topology)

        # Apply target action to simulation model
        twin.apply_remediation_action(target, action_type)
        twin.initialize_simulation()

        # Run simulation for 10 steps
        history = twin.run_simulation(until=10)

        # The gate judges the blast radius of THIS action: the target plus its direct
        # dependencies/dependents. Unrelated pods that are already hot do not veto it.
        radius = [target] + [
            n for n in (self.topology.get_dependencies(target) + self.topology.get_dependents(target))
            if n != target
        ]
        predicted = {}
        is_safe = True
        for pod in radius:
            pod_history = history.get(pod)
            if not pod_history:
                continue
            initial_cpu, final_cpu = pod_history[0]["cpu"], pod_history[-1]["cpu"]
            predicted[pod] = round(final_cpu, 4)
            if pod == target:
                is_safe = is_safe and final_cpu < 0.90
            else:
                # A neighbour passes if it stays under the ceiling, or the action did not
                # push it materially higher than where it started (<= 25% growth).
                is_safe = is_safe and (final_cpu < 0.90 or final_cpu <= initial_cpu * 1.25)

        max_final_cpu = max(predicted.values()) if predicted else 0.0

        return {
            "action_type": action_type,
            "target": target,
            "simulation_steps": 10,
            "is_safe": is_safe,
            "predicted_max_cpu": round(max_final_cpu, 4),
            "predicted_cpu": predicted,
            "blast_radius": radius,
            "recommendation": "SAFE_TO_EXECUTE" if is_safe else "RISK_OF_OVERLOAD"
        }

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
