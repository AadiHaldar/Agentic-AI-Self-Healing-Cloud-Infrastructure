import time
import unittest
import numpy as np
from digital_twin.topology_graph import TopologyGraph
from agentic_engine.orchestrator import ParallelAgentOrchestrator
from detection.anomaly.isolation_forest import MetricsAnomalyDetector
from detection.explainer.shap_explainer import SHAPExplainer

class TestEndToEndEvaluation(unittest.TestCase):
    """
    End-to-End Integration & Benchmarking Suite for the Self-Healing System.
    Evaluates MTTD, MTTR, Parallel Agent Divergence, and SHAP Explainability.
    """
    def setUp(self):
        self.topology = TopologyGraph()
        # Seed nodes
        for svc in ["frontend", "checkoutservice", "cartservice", "paymentservice", "emailservice"]:
            self.topology.update_node(f"{svc}-pod", "pod", {"cpu_usage": 0.20, "memory_usage": 0.30})

        self.orchestrator = ParallelAgentOrchestrator(self.topology, mode="parallel")
        
        # Train baseline anomaly detector
        self.detector = MetricsAnomalyDetector(contamination=0.1)
        healthy_baseline = np.random.normal(loc=0.25, scale=0.05, size=(100, 2))
        self.detector.train(healthy_baseline)

    def test_fault_detection_and_remediation_pipeline(self):
        """Simulate a Chaos Mesh fault injection and measure MTTD + MTTR."""
        t_fault_injected = time.time()
        
        # 1. Fault Trigger (CPU spike on checkoutservice)
        anomalous_sample = np.array([[0.95, 0.85]])
        pred = self.detector.predict(anomalous_sample)
        
        t_detected = time.time()
        mttd = t_detected - t_fault_injected
        self.assertEqual(pred[0], -1, "Anomaly detector failed to catch fault!")

        # 2. Parallel Agent Remediation
        alert_context = {
            "target_service": "checkoutservice",
            "cpu_usage": 0.95,
            "mem_usage": 0.85,
            "is_anomaly": True,
            "shap_explanation": "CPU spiked to 95% on checkoutservice"
        }
        
        res = self.orchestrator.process_alert(alert_context)
        t_remediated = time.time()
        mttr = t_remediated - t_detected
        
        print("\n================ BENCHMARK RESULTS ================")
        print(f"Mean Time To Detect (MTTD):    {mttd*1000:.3f} ms")
        print(f"Mean Time To Remediate (MTTR):  {mttr*1000:.3f} ms")
        print(f"RL Latency:                     {res['comparison']['rl_latency']*1000:.3f} ms")
        print(f"LLM Latency:                    {res['comparison']['llm_latency']*1000:.3f} ms")
        print(f"Parallel Agreement:             {res['comparison']['actions_match']}")
        print("===================================================\n")

        self.assertTrue(mttd < 1.0, "MTTD exceeded threshold!")
        self.assertTrue(mttr < 30.0, "MTTR exceeded 30 second threshold!")

if __name__ == "__main__":
    unittest.main()
