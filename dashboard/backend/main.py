import os
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional

from digital_twin.topology_graph import TopologyGraph
from agentic_engine.orchestrator import ParallelAgentOrchestrator
from agentic_engine.tools.k8s_tools import K8sRemediationTools
from detection.anomaly.isolation_forest import MetricsAnomalyDetector
from detection.explainer.shap_explainer import SHAPExplainer

app = FastAPI(
    title="Agentic AI Self-Healing Infrastructure Dashboard API",
    version="2.0.0"
)

# Enable CORS for local UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State & ML Models
topology = TopologyGraph()
k8s_tools = K8sRemediationTools()
orchestrator = ParallelAgentOrchestrator(topology, mode="parallel")
anomaly_detector = MetricsAnomalyDetector()
shap_explainer = SHAPExplainer(anomaly_detector.model)

# Initialize seed topology with clean service IDs
topology.update_node("frontend", "pod", {"cpu_usage": 0.35, "memory_usage": 0.40, "status": "Healthy"})
topology.update_node("checkoutservice", "pod", {"cpu_usage": 0.88, "memory_usage": 0.72, "status": "Warning"})
topology.update_node("cartservice", "pod", {"cpu_usage": 0.45, "memory_usage": 0.50, "status": "Healthy"})
topology.update_node("redis-cart", "pod", {"cpu_usage": 0.20, "memory_usage": 0.30, "status": "Healthy"})

topology.add_dependency("frontend", "checkoutservice")
topology.add_dependency("checkoutservice", "cartservice")
topology.add_dependency("cartservice", "redis-cart")


class AlertRequest(BaseModel):
    target_service: str
    cpu_usage: float
    mem_usage: float
    is_anomaly: bool = True
    shap_explanation: Optional[str] = None

class OverrideRequest(BaseModel):
    target_service: str
    override_action: str
    reason: str


@app.get("/api/status")
def get_system_status():
    """Return overall infrastructure and agent status."""
    nodes = topology.graph.nodes
    anomalous_pods = [n for n, d in nodes.items() if d.get("cpu_usage", 0.0) > 0.8]
    return {
        "status": "DEGRADED" if anomalous_pods else "HEALTHY",
        "total_pods": len(nodes),
        "active_anomalies": len(anomalous_pods),
        "anomalous_pods": anomalous_pods,
        "active_mode": orchestrator.mode
    }

@app.get("/api/topology")
def get_topology():
    """Return Digital Twin graph topology representation."""
    return topology.to_dict()

@app.post("/api/evaluate")
def evaluate_alert(request: AlertRequest):
    """Run Dynamic SHAP attribution and Parallel Orchestration evaluation."""
    sample = np.array([[request.cpu_usage, request.mem_usage, request.cpu_usage * 100, request.mem_usage * 200]])
    
    # 1. Run dynamic SHAP feature importance calculation
    shap_dict = shap_explainer.explain_instance(sample)
    formatted_shap_str = shap_explainer.format_explanation_for_llm(shap_dict)

    context = {
        "target_service": request.target_service,
        "cpu_usage": request.cpu_usage,
        "mem_usage": request.mem_usage,
        "is_anomaly": request.is_anomaly,
        "shap_explanation": formatted_shap_str,
        "shap_dict": shap_dict
    }
    
    # 2. Update Topology Graph state
    topology.update_node(request.target_service, "pod", {
        "cpu_usage": request.cpu_usage,
        "memory_usage": request.mem_usage,
        "status": "Critical" if request.cpu_usage > 0.8 else "Healthy"
    })
    
    # 3. Evaluate Parallel Agent Pipeline
    result = orchestrator.process_alert(context)
    result["shap_summary"] = formatted_shap_str
    result["shap_scores"] = shap_dict
    return result

from agentic_engine.tools.github_tools import github_manager

@app.get("/api/github/prs")
def get_github_prs():
    """Return history of generated GitOps and Code Patch Pull Requests."""
    return {
        "prs": github_manager.get_pr_history(),
        "is_live_mode": github_manager.is_live,
        "repo": github_manager.repo
    }

class GitOpsPRRequest(BaseModel):
    service: str
    replicas: int = 3
    cpu_limit: str = "1000m"
    pr_type: str = "GITOPS"  # "GITOPS" or "CODE_PATCH"

@app.post("/api/github/create-pr")
def create_github_pr(request: GitOpsPRRequest):
    """Manually trigger GitOps Scaling PR or Code Patch PR."""
    if request.pr_type == "CODE_PATCH":
        res = github_manager.create_code_patch_pr(
            service=request.service,
            file_path=f"src/{request.service}/handler.py",
            issue_summary="Operator-triggered Code Patch PR for unhandled exception"
        )
    else:
        res = github_manager.create_gitops_pr(
            service=request.service,
            replicas=request.replicas,
            cpu_limit=request.cpu_limit
        )
    return res

@app.post("/api/github/webhook")
async def github_webhook(request: Dict[str, Any]):
    """
    GitHub App Webhook Endpoint.
    Receives pull_request/push/issues HTTP POST events from GitHub and triggers Agentic AI verification.
    """
    event_type = "pull_request"
    res = github_manager.handle_webhook_event(request, event_type=event_type)
    return res

@app.get("/api/github/app-config")
def get_github_app_config():
    """Return instructions and webhook URL for 1-click GitHub App / Webhook integration."""
    return {
        "webhook_url": "http://localhost:8085/api/github/webhook",
        "events_supported": ["pull_request", "push", "issues"],
        "setup_steps": [
            "1. Open your target GitHub Repository (e.g. HRA_Final)",
            "2. Go to Settings -> Webhooks -> Add Webhook",
            "3. Paste Payload URL: http://<your-host>:8085/api/github/webhook",
            "4. Select Content Type: application/json",
            "5. Select Events: 'Pull requests' and 'Pushes'",
            "6. Click 'Add Webhook'. Done! Zero YAML files or code changes needed."
        ]
    }

@app.get("/api/github/scan-integrity")
def scan_code_integrity(repo: str = "AadiHaldar/continuum-forge"):
    """
    Triggers a Deep Code Integrity & Vulnerability Audit on the specified GitHub repository.
    Scans for secret leaks, unhandled timeouts, memory leak hazards, and manifest limit compliance.
    """
    res = github_manager.analyze_repository_integrity(repo)
    return res

@app.post("/api/override")
def manual_override(request: OverrideRequest):
    """Manual operator override for an AI decision executing real K8s commands."""
    action = request.override_action.upper()
    if "RESTART" in action:
        res = k8s_tools.restart_pod(request.target_service)
    elif "SCALE" in action:
        res = k8s_tools.scale_deployment(request.target_service, replicas=4)
    elif "PATCH" in action:
        res = k8s_tools.patch_resource_limits(request.target_service, cpu_limit="1000m", memory_limit="1024Mi")
    else:
        res = {"status": "skipped", "message": "Manual override action marked DO_NOTHING."}
        
    return {
        "status": "success",
        "message": f"Operator manually applied '{request.override_action}' on '{request.target_service}'. Result: {res.get('message')}",
        "k8s_output": res,
        "reason": request.reason
    }

# Mount static frontend if available
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
