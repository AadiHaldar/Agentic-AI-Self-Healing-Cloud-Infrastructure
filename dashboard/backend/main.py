from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os

from digital_twin.topology_graph import TopologyGraph
from agentic_engine.orchestrator import ParallelAgentOrchestrator

app = FastAPI(
    title="Agentic AI Self-Healing Infrastructure Dashboard API",
    version="1.0.0"
)

# Enable CORS for local UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
topology = TopologyGraph()
orchestrator = ParallelAgentOrchestrator(topology, mode="parallel")

# Initialize seed topology
topology.update_node("frontend-pod-0", "pod", {"cpu_usage": 0.35, "memory_usage": 0.40, "status": "Healthy"})
topology.update_node("checkoutservice-pod-0", "pod", {"cpu_usage": 0.88, "memory_usage": 0.72, "status": "Warning"})
topology.update_node("cartservice-pod-0", "pod", {"cpu_usage": 0.45, "memory_usage": 0.50, "status": "Healthy"})
topology.update_node("redis-cart-0", "pod", {"cpu_usage": 0.20, "memory_usage": 0.30, "status": "Healthy"})

topology.add_dependency("frontend-pod-0", "checkoutservice-pod-0")
topology.add_dependency("checkoutservice-pod-0", "cartservice-pod-0")
topology.add_dependency("cartservice-pod-0", "redis-cart-0")


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
    """Run Parallel Orchestration evaluation for an alert."""
    context = {
        "target_service": request.target_service,
        "cpu_usage": request.cpu_usage,
        "mem_usage": request.mem_usage,
        "is_anomaly": request.is_anomaly,
        "shap_explanation": request.shap_explanation or f"SHAP: CPU spiked by {request.cpu_usage*100:.1f}% on {request.target_service}"
    }
    
    # Update topology state
    topology.update_node(request.target_service, "pod", {
        "cpu_usage": request.cpu_usage,
        "memory_usage": request.mem_usage,
        "status": "Critical" if request.cpu_usage > 0.8 else "Healthy"
    })
    
    result = orchestrator.process_alert(context)
    return result

@app.post("/api/override")
def manual_override(request: OverrideRequest):
    """Manual operator override for an AI decision."""
    return {
        "status": "success",
        "message": f"Operator manually applied '{request.override_action}' on '{request.target_service}'.",
        "reason": request.reason
    }

# Mount static frontend if available
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
