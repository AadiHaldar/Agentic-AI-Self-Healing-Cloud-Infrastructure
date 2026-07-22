import simpy
import logging
from typing import Dict, Any
from .topology_graph import TopologyGraph

logger = logging.getLogger(__name__)

class SimPyDigitalTwin:
    """
    A discrete-event simulation engine for the Digital Twin using SimPy.
    Allows for "what-if" scenarios (e.g., simulating the impact of losing a node 
    or predicting resource exhaustion over time).
    """
    def __init__(self, topology: TopologyGraph):
        self.env = simpy.Environment()
        self.topology = topology
        self.simulation_state: Dict[str, Any] = {}
        
    def _pod_behavior(self, pod_id: str, initial_cpu: float, initial_mem: float):
        """Simulate the behavior of a single pod over time."""
        current_cpu = initial_cpu
        current_mem = initial_mem
        
        while True:
            # In a real scenario, this would use the predictive forecaster models.
            # For this MVP, we simulate a slight random walk or simple linear trend.
            # Here we just record state.
            self.simulation_state[pod_id] = {
                "cpu": current_cpu,
                "memory": current_mem,
                "time": self.env.now
            }
            
            # Simulate a time step of 1 unit (e.g., 1 minute)
            yield self.env.timeout(1)
            
            # Simple drift
            current_cpu *= 1.01
            current_mem *= 1.02

    def initialize_simulation(self):
        """Seed the simulation environment with the current state of the TopologyGraph."""
        for node_id in self.topology.graph.nodes:
            node_data = self.topology.get_node_state(node_id)
            if node_data.get("type") == "pod":
                cpu = node_data.get("cpu_usage", 0.0)
                mem = node_data.get("memory_usage", 0.0)
                self.env.process(self._pod_behavior(node_id, cpu, mem))

    def run_simulation(self, until: int):
        """Run the simulation for a specified number of time steps."""
        logger.info(f"Running simulation until t={until}")
        self.env.run(until=until)
        return self.simulation_state

    def reset(self):
        """Reset the simulation environment."""
        self.env = simpy.Environment()
        self.simulation_state = {}
