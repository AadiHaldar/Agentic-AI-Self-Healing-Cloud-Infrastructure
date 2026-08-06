import simpy
import logging
from typing import Dict, Any, List
from .topology_graph import TopologyGraph

logger = logging.getLogger(__name__)

class SimPyDigitalTwin:
    """
    A discrete-event simulation engine for the Digital Twin using SimPy.
    Allows for "what-if" scenarios (e.g., simulating the impact of scaling, restarting,
    or resource patching on connected microservices over time).
    """
    def __init__(self, topology: TopologyGraph):
        self.env = simpy.Environment()
        self.topology = topology
        self.simulation_history: Dict[str, List[Dict[str, Any]]] = {}
        self.active_actions: Dict[str, str] = {}

    def apply_remediation_action(self, target: str, action_type: str):
        """Apply a simulated action to a target service/pod."""
        self.active_actions[target] = action_type.upper()

    def _pod_behavior(self, pod_id: str, initial_cpu: float, initial_mem: float):
        """Simulate the behavior of a single pod over time with action feedback."""
        current_cpu = initial_cpu
        current_mem = initial_mem
        self.simulation_history[pod_id] = []

        while True:
            # Record state at current time step
            self.simulation_history[pod_id].append({
                "time": self.env.now,
                "cpu": round(current_cpu, 4),
                "memory": round(current_mem, 4)
            })

            # Simulate 1 time step (e.g. 1 minute)
            yield self.env.timeout(1)

            # Check if an action was applied to this target or its dependencies
            action = self.active_actions.get(pod_id, "NONE")
            if "RESTART" in action:
                # Restart resets resource metrics to baseline
                current_cpu = max(0.15, current_cpu * 0.3)
                current_mem = max(0.20, current_mem * 0.4)
            elif "SCALE" in action:
                # Scaling divides load across replicas
                current_cpu = max(0.15, current_cpu * 0.5)
                current_mem = max(0.20, current_mem * 0.6)
            elif "PATCH" in action:
                # Patching increases capacity ceiling, reducing pressure
                current_cpu = max(0.15, current_cpu * 0.7)
            else:
                # Natural load drift
                current_cpu = min(1.0, current_cpu * 1.02)
                current_mem = min(1.0, current_mem * 1.01)

    def initialize_simulation(self):
        """Seed the simulation environment with the current state of the TopologyGraph."""
        for node_id in self.topology.graph.nodes:
            node_data = self.topology.get_node_state(node_id)
            if node_data.get("type") == "pod":
                cpu = node_data.get("cpu_usage", 0.30)
                mem = node_data.get("memory_usage", 0.40)
                self.env.process(self._pod_behavior(node_id, cpu, mem))

    def run_simulation(self, until: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Run the simulation for a specified number of time steps."""
        logger.info(f"[SimPyDigitalTwin] Running simulation until t={until}")
        self.env.run(until=until)
        return self.simulation_history
