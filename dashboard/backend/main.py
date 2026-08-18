import logging
import os
import json
import time
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, Optional

from digital_twin.topology_graph import TopologyGraph
from agentic_engine.orchestrator import ParallelAgentOrchestrator
from agentic_engine.tools.k8s_tools import K8sRemediationTools
from detection.anomaly.isolation_forest import MetricsAnomalyDetector
from detection.explainer.shap_explainer import SHAPExplainer

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic AI Self-Healing Infrastructure Dashboard API",
    version="2.0.0"
)

# ── Mount PR Review Agent router ──────────────────────────────────────────────
try:
    from pr_review_agent.webhook_handler import router as pr_review_router
    app.include_router(pr_review_router)
    logger.info("[main] pr_review_agent router mounted")
except Exception as _pr_import_err:
    logger.warning(
        "[main] pr_review_agent not mounted (dependency missing?): %s", _pr_import_err
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


# ── Auto-seed demo data on startup ───────────────────────────────────────────
@app.on_event("startup")
def seed_demo_on_startup():
    """Seed AadiHaldar's real repos + PR review history into SQLite on every boot."""
    try:
        from pr_review_agent.db import (
            _conn, init_db, upsert_installation, add_installation_repo,
            set_app_config, get_app_config,
        )

        # Must initialise tables before any writes
        init_db()

        # 1. App config
        if not get_app_config("GITHUB_APP_ID"):
            set_app_config("GITHUB_APP_ID", "4622895")
            set_app_config("GITHUB_APP_SLUG", "agentic-review-agent-65012")

        # 2. Real installation + repos
        INSTALLATION_ID = 154382391
        upsert_installation(
            installation_id=INSTALLATION_ID,
            account_login="AadiHaldar",
            account_type="User",
            app_id=4622895,
        )
        REAL_REPOS = [
            "AadiHaldar/MFC3_C4_ADMM_Based_Network_Anomaly_Detection",
            "AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure",
        ]
        for repo in REAL_REPOS:
            add_installation_repo(INSTALLATION_ID, repo)

        # 3. PR review history (skip if already seeded)
        with _conn() as con:
            existing = con.execute(
                "SELECT COUNT(*) FROM review_log WHERE repo_full_name LIKE 'AadiHaldar/%'"
            ).fetchone()[0]
            if existing == 0:
                demo_reviews = [
                    ("AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure",
                     1, "a04fef7b", 3, 1, "gate_passed", "2026-08-17 10:22:39"),
                    ("AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure",
                     2, "d1c8fa22", 7, 2, "gate_failed", "2026-08-17 09:14:05"),
                    ("AadiHaldar/MFC3_C4_ADMM_Based_Network_Anomaly_Detection",
                     1, "b3e9120c", 2, 0, "gate_passed", "2026-08-16 18:45:11"),
                    ("AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure",
                     3, "f7a2091d", 5, 1, "gate_failed", "2026-08-16 14:33:22"),
                    ("AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure",
                     4, "c9b3412e", 1, 0, "gate_passed", "2026-08-15 21:10:47"),
                    ("AadiHaldar/MFC3_C4_ADMM_Based_Network_Anomaly_Detection",
                     2, "e5d1293a", 4, 1, "gate_failed", "2026-08-15 11:22:08"),
                    ("AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure",
                     5, "77fa3b1c", 0, 0, "gate_passed", "2026-08-14 16:05:31"),
                ]
                con.executemany(
                    "INSERT INTO review_log "
                    "(repo_full_name, pr_number, commit_sha, findings_count, critical_count, status, reviewed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    demo_reviews
                )
                logger.info("[startup] Seeded %d demo PR reviews into SQLite", len(demo_reviews))
            else:
                logger.info("[startup] Demo data already present (%d rows), skipping seed.", existing)

        logger.info("[startup] AadiHaldar repos seeded successfully: %s", REAL_REPOS)
    except Exception as seed_err:
        import traceback
        logger.error("[startup] Demo seed FAILED: %s\n%s", seed_err, traceback.format_exc())


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

    # 4. Live Kubernetes Actuation (if connected to live cluster)
    if request.is_anomaly:
        try:
            chosen_action = result.get("agents", {}).get("llm_react", {}).get("action_taken", "SCALE_UP")
            if "SCALE" in chosen_action.upper():
                k8s_res = k8s_tools.scale_deployment(request.target_service, replicas=4, namespace="default")
            elif "RESTART" in chosen_action.upper():
                k8s_res = k8s_tools.restart_pod(request.target_service, namespace="default")
            else:
                k8s_res = {"status": "skipped", "message": "Action marked DO_NOTHING"}
            result["k8s_live_actuation"] = k8s_res
            logger.info(f"[main] Live K8s Actuation Executed: {k8s_res}")
        except Exception as k8s_err:
            logger.debug(f"[main] Live K8s Actuation bypassed: {k8s_err}")
            result["k8s_live_actuation"] = {"status": "bypassed", "reason": str(k8s_err)}

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
async def github_webhook(request: Request):
    """
    GitHub App Webhook Endpoint.
    Receives pull_request/push/issues HTTP POST events from GitHub
    and triggers the legacy infra-healing audit comment.
    Real PR review analysis is handled by pr_review_agent.webhook_handler (Phase 3).
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    event_type = request.headers.get("X-GitHub-Event", "pull_request")
    res = github_manager.handle_webhook_event(payload, event_type=event_type)
    return res

@app.get("/api/github/app-config")
def get_github_app_config():
    """Return instructions and webhook URL for 1-click GitHub App / Webhook integration."""
    tunnel_url = "https://crunching-avenging-transport.ngrok-free.dev"
    return {
        "webhook_url": f"{tunnel_url}/api/github/webhook",
        "manifest_setup_url": f"{tunnel_url}/api/github/app-manifest-form",
        "events_supported": ["pull_request", "push", "issues"],
        "setup_steps": [
            "1. Click '1-Click Register GitHub App' to pre-fill GitHub permissions",
            "2. Click 'Create GitHub App' on GitHub",
            "3. Select repositories (e.g. Amrita-Express) to install",
            "4. Done! App can now automatically open PRs & post review comments with 0 user access sharing."
        ]
    }

@app.get("/api/github/app-manifest-form", response_class=HTMLResponse)
def get_github_app_manifest_form():
    """Redirect to the new /install page (handled by pr_review_agent router)."""
    return HTMLResponse(
        '<meta http-equiv="refresh" content="0; url=/install">'
        '<p>Redirecting to <a href="/install">/install</a>...</p>'
    )



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

# Primary dashboard UI: mounts dashboard/frontend (single-page interactive app)
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))

if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    logger.info("[main] Mounted frontend dashboard from %s", frontend_path)
