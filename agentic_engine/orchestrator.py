import time
import logging
from typing import Dict, Any, List
from .rl_agent import SimiFedRLAgent
from .llm_agent import LLMReActAgent
from .tools.k8s_tools import K8sRemediationTools
from .tools.simpy_tools import SimPySimulationTools
from digital_twin.topology_graph import TopologyGraph

logger = logging.getLogger(__name__)

class ParallelAgentOrchestrator:
    """
    Orchestrates both the RL SimiFed Agent and the LLM ReAct Agent in parallel.
    Enables side-by-side comparison of speed, decision quality, and explainability.
    """
    def __init__(self, topology: TopologyGraph, mode: str = "parallel"):
        """
        `mode`: 'parallel' (runs both and compares), 'rl_only', or 'llm_only'.
        """
        self.topology = topology
        self.mode = mode
        
        self.k8s_tools = K8sRemediationTools()
        self.sim_tools = SimPySimulationTools(self.topology)
        
        self.rl_agent = SimiFedRLAgent()
        self.llm_agent = LLMReActAgent(self.k8s_tools, self.sim_tools)

    def process_alert(self, alert_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an infrastructure alert through the configured agent pipeline.
        """
        service = alert_context.get("target_service", "unknown-service")
        cpu_usage = alert_context.get("cpu_usage", 0.0)
        mem_usage = alert_context.get("mem_usage", 0.0)
        is_anomaly = alert_context.get("is_anomaly", True)

        results = {
            "timestamp": time.time(),
            "target_service": service,
            "mode": self.mode,
            "agents": {}
        }

        # 1. Evaluate RL SimiFed Agent
        if self.mode in ["parallel", "rl_only"]:
            t0 = time.time()
            rl_decision = self.rl_agent.decide_remediation(service, cpu_usage, mem_usage, is_anomaly)
            rl_duration = time.time() - t0
            rl_decision["latency_seconds"] = round(rl_duration, 4)
            results["agents"]["rl_simifed"] = rl_decision

        # 2. Evaluate LLM ReAct Agent
        if self.mode in ["parallel", "llm_only"]:
            t0 = time.time()
            llm_decision = self.llm_agent.evaluate_and_heal(alert_context)
            llm_duration = time.time() - t0
            llm_decision["latency_seconds"] = round(llm_duration, 4)
            results["agents"]["llm_react"] = llm_decision

        # 3. Parallel Comparison Summary
        if self.mode == "parallel":
            rl_act = results["agents"]["rl_simifed"]["action"]
            llm_act = results["agents"]["llm_react"]["action_taken"]
            agreed = (rl_act == llm_act)
            
            results["comparison"] = {
                "actions_match": agreed,
                "rl_latency": results["agents"]["rl_simifed"]["latency_seconds"],
                "llm_latency": results["agents"]["llm_react"]["latency_seconds"],
                "recommendation": f"Both agents agreed on {rl_act}" if agreed else f"Divergence: RL proposed {rl_act}, LLM proposed {llm_act}"
            }

        logger.info(f"[Orchestrator] Completed evaluation for {service} in mode '{self.mode}'")
        return results
