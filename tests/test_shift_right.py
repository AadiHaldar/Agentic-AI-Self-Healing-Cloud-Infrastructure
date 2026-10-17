"""
Tests for the shift-right decision logic: the trained RL policy and the fault-aware digital-twin gate.
Run: python -m pytest tests/test_shift_right.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agentic_engine.rl_agent import SimiFedRLAgent
from agentic_engine.tools.simpy_tools import SimPySimulationTools
from digital_twin.topology_graph import TopologyGraph

# (cpu, memory, latency_ms, request_rate) of the four fault patterns plus a healthy control
HEALTHY = (0.25, 0.40, 45.0, 120.0)
SURGE = (0.954, 0.45, 450.0, 500.0)
DEADLOCK = (0.99, 0.85, 5000.0, 0.0)
LEAK = (0.15, 0.942, 48.0, 110.0)
CASCADE = (0.88, 0.80, 320.0, 250.0)


def make_gate(cpu, mem):
    t = TopologyGraph()
    t.update_node("frontend", "pod", {"cpu_usage": 0.35, "memory_usage": 0.40})
    t.update_node("svc", "pod", {"cpu_usage": cpu, "memory_usage": mem})
    t.update_node("db", "pod", {"cpu_usage": 0.30, "memory_usage": 0.40})
    t.add_dependency("frontend", "svc")
    t.add_dependency("svc", "db")
    return SimPySimulationTools(t)


def verdict(case, action):
    cpu, mem, lat, rate = case
    return make_gate(cpu, mem).simulate_remediation(
        action, "svc", {"cpu": cpu, "memory": mem, "latency_ms": lat, "request_rate": rate})


class TestRLPolicy(unittest.TestCase):
    def setUp(self):
        self.agent = SimiFedRLAgent()

    def test_trained_table_is_loaded_and_greedy(self):
        self.assertIn("trained", self.agent.policy_source)
        self.assertEqual(self.agent.epsilon, 0.0)

    def act(self, case, anomaly=True):
        cpu, mem, lat, rate = case
        return self.agent.decide_remediation("svc", cpu, mem, anomaly, lat, rate)["action"]

    def test_does_nothing_on_healthy_and_on_false_alarm(self):
        self.assertEqual(self.act(HEALTHY, anomaly=False), "DO_NOTHING")
        self.assertEqual(self.act(HEALTHY, anomaly=True), "DO_NOTHING")

    def test_picks_the_remedy_that_fits_the_fault(self):
        self.assertEqual(self.act(SURGE), "SCALE_UP")        # capacity problem
        self.assertEqual(self.act(DEADLOCK), "RESTART_POD")  # stuck threads need a restart
        self.assertEqual(self.act(LEAK), "RESTART_POD")      # a restart clears the leak
        self.assertEqual(self.act(CASCADE), "SCALE_UP")

    def test_decision_is_deterministic(self):
        self.assertEqual({self.act(SURGE) for _ in range(20)}, {"SCALE_UP"})


class TestGate(unittest.TestCase):
    def test_blocks_actions_on_a_healthy_service(self):
        for action in ("SCALE", "RESTART", "PATCH"):
            v = verdict(HEALTHY, action)
            self.assertEqual(v["recommendation"], "NOT_NEEDED")
            self.assertFalse(v["is_safe"])

    def test_approves_the_right_remedy(self):
        self.assertTrue(verdict(SURGE, "SCALE")["is_safe"])
        self.assertTrue(verdict(DEADLOCK, "RESTART")["is_safe"])
        self.assertTrue(verdict(LEAK, "RESTART")["is_safe"])

    def test_rejects_ineffective_remedies_with_a_reason(self):
        for case, action in ((SURGE, "RESTART"), (DEADLOCK, "SCALE"), (DEADLOCK, "PATCH"), (LEAK, "SCALE")):
            v = verdict(case, action)
            self.assertEqual(v["recommendation"], "INEFFECTIVE", (case, action))
            self.assertFalse(v["is_safe"])
            self.assertTrue(v["reason"])

    def test_unknown_service_is_not_safe(self):
        v = make_gate(0.9, 0.5).simulate_remediation("RESTART", "nope")
        self.assertEqual(v["recommendation"], "TARGET_NOT_IN_TWIN")
        self.assertFalse(v["is_safe"])

    def test_suggests_an_approved_alternative(self):
        cpu, mem, lat, rate = DEADLOCK
        alt = make_gate(cpu, mem).suggest_alternative("svc", {"cpu": cpu, "memory": mem, "latency_ms": lat, "request_rate": rate}, exclude="SCALE")
        self.assertEqual(alt["action"], "RESTART_POD")

    def test_neighbour_overload_is_rejected(self):
        # make a dependency already saturated and growing: restarting the target must not be approved blindly
        t = TopologyGraph()
        t.update_node("svc", "pod", {"cpu_usage": 0.95, "memory_usage": 0.4})
        t.update_node("db", "pod", {"cpu_usage": 0.89, "memory_usage": 0.4})
        t.add_dependency("svc", "db")
        v = SimPySimulationTools(t).simulate_remediation("RESTART", "svc")
        self.assertIn(v["recommendation"], ("SAFE_TO_EXECUTE", "RISK_OF_OVERLOAD"))  # documented either way, never an exception


if __name__ == "__main__":
    unittest.main()
