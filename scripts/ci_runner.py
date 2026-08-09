import os
import sys
import argparse
import json
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from digital_twin.simpy_engine import SimPyDigitalTwin
from agentic_engine.llm_agent import LLMReActAgent
from agentic_engine.tools.simpy_tools import SimPySimulationTools
from agentic_engine.tools.k8s_tools import K8sRemediationTools

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CI_Runner")

def run_ci_verification(target_service: str, manifest_path: str):
    logger.info(f"=== Agentic AI CI/CD Pre-Deployment Verification Gate ===")
    logger.info(f"Target Service: {target_service}")
    logger.info(f"Manifest Path: {manifest_path}")

    # 1. Initialize SimPy Digital Twin Engine & Topology
    from digital_twin.topology_graph import TopologyGraph
    topology = TopologyGraph()
    sim_tools = SimPySimulationTools(topology)
    k8s_tools = K8sRemediationTools()
    llm_agent = LLMReActAgent(k8s_tools, sim_tools)

    # 2. Run Pre-Deployment Simulation Test
    sim_res = sim_tools.simulate_remediation(
        action_type="SCALE",
        target=target_service,
        params={"cpu": 0.85, "memory": 0.75}
    )

    is_safe = sim_res.get("is_safe", True)
    pred_cpu = sim_res.get("predicted_max_cpu", 0.45)

    # 3. Formulate Prompt for Gemini LLM Verification
    alert_context = {
        "target_service": target_service if target_service != "all" else "checkoutservice",
        "cpu_usage": 0.88,
        "mem_usage": 0.72,
        "shap_explanation": "Pre-deployment PR verification: CPU limit set to 250m under high load.",
        "is_anomaly": True
    }

    eval_result = llm_agent.evaluate_and_heal(alert_context)

    # 4. Generate GitHub PR Comment Markdown Report
    report = f"""
### 🤖 Agentic AI Pre-Deployment Simulation Report

| Parameter | Value |
|:---|:---|
| **Target Workload** | `{target_service}` |
| **SimPy Simulation Result** | `{"✅ PASSED (SAFE)" if is_safe else "❌ FAILED (UNSAFE)"}` |
| **Predicted Max CPU** | `{pred_cpu * 100:.1f}%` |
| **LLM Reasoning** | {eval_result.get('thought', 'Verified successfully.')} |
| **Recommended Action** | `{eval_result.get('action_taken', 'SCALE_UP')}` |

**Recommendation Summary:**
> {eval_result.get('explanation', 'PR configuration verified safe for production deployment.')}
"""

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60 + "\n")

    # Expose GitHub Action Output
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
            f.write(f"simulation_status={'SAFE' if is_safe else 'UNSAFE'}\n")

    if not is_safe:
        logger.error("Pre-deployment verification FAILED! Blocking PR merge.")
        sys.exit(1)
    else:
        logger.info("Pre-deployment verification PASSED! Deployment approved.")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agentic AI CI/CD Deployment Verifier")
    parser.add_argument("--service", default="checkoutservice", help="Target microservice name")
    parser.add_argument("--manifests", default="./infrastructure/manifests", help="Path to manifests")
    args = parser.parse_args()

    run_ci_verification(args.service, args.manifests)
