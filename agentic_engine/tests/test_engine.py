import unittest
from digital_twin.topology_graph import TopologyGraph
from agentic_engine.orchestrator import ParallelAgentOrchestrator

class TestAgenticEngine(unittest.TestCase):
    def setUp(self):
        self.topology = TopologyGraph()
        self.topology.update_node("checkoutservice-pod-0", "pod", {"cpu_usage": 0.88, "memory_usage": 0.70})
        self.orchestrator = ParallelAgentOrchestrator(self.topology, mode="parallel")

    def test_parallel_orchestrator(self):
        alert_context = {
            "target_service": "checkoutservice",
            "cpu_usage": 0.88,
            "mem_usage": 0.70,
            "is_anomaly": True,
            "shap_explanation": "CPU spiked by 88% on checkoutservice"
        }
        res = self.orchestrator.process_alert(alert_context)
        
        self.assertIn("rl_simifed", res["agents"])
        self.assertIn("llm_react", res["agents"])
        self.assertIn("comparison", res)
        print("Parallel Execution Test Result:", res["comparison"])

if __name__ == "__main__":
    unittest.main()
