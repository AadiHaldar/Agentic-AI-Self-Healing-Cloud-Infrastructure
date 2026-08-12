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
        twin = SimPyDigitalTwin(self.topology)
        
        # Apply target action to simulation model
        twin.apply_remediation_action(target, action_type)
        twin.initialize_simulation()
        
        # Run simulation for 10 steps
        history = twin.run_simulation(until=10)
        
        # Evaluate simulated post-action stability
        final_cpus = []
        for pod_history in history.values():
            if pod_history:
                final_cpus.append(pod_history[-1]["cpu"])
                
        max_final_cpu = max(final_cpus) if final_cpus else 0.0
        is_safe = max_final_cpu < 0.90
        
        return {
            "action_type": action_type,
            "target": target,
            "simulation_steps": 10,
            "is_safe": is_safe,
            "predicted_max_cpu": round(max_final_cpu, 4),
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
