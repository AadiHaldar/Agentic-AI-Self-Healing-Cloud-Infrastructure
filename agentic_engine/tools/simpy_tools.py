import logging
from typing import Dict, Any
from digital_twin.simpy_engine import SimPyDigitalTwin
from digital_twin.topology_graph import TopologyGraph

logger = logging.getLogger(__name__)

class SimPySimulationTools:
    """
    Exposes dry-run capabilities to the AI agent via the SimPy Digital Twin.
    Allows testing actions (scaling, restarting) in simulation before applying to K8s.
    """
    def __init__(self, topology: TopologyGraph):
        self.topology = topology

    def simulate_remediation(self, action_type: str, target: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Simulate an action against the in-memory Digital Twin.
        `action_type`: 'scale', 'restart', 'patch'
        """
        logger.info(f"Simulating action '{action_type}' on '{target}' with params {params}...")
        twin = SimPyDigitalTwin(self.topology)
        twin.initialize_simulation()
        
        # Run simulation for 10 time steps
        results = twin.run_simulation(until=10)
        
        # Evaluate simulated stability
        predicted_max_cpu = max([v.get("cpu", 0.0) for v in results.values()]) if results else 0.0
        is_safe = predicted_max_cpu < 0.95
        
        return {
            "action_type": action_type,
            "target": target,
            "simulation_steps": 10,
            "is_safe": is_safe,
            "predicted_max_cpu": round(predicted_max_cpu, 4),
            "recommendation": "SAFE_TO_EXECUTE" if is_safe else "RISK_OF_OVERLOAD"
        }
