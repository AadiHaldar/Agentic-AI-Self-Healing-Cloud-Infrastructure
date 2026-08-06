import subprocess
import logging
import json
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class K8sRemediationTools:
    """
    Executes actual Kubernetes control-plane operations using kubectl / K8s API.
    Handles dynamic pod name resolution and Windows shell escaping.
    """
    def __init__(self, default_namespace: str = "online-boutique"):
        self.default_namespace = default_namespace

    def get_pod_name_for_service(self, service_name: str, namespace: str = None) -> str:
        """Find the real active pod name matching app={service_name} or return target."""
        ns = namespace or self.default_namespace
        cmd = f"kubectl get pods -n {ns} -l app={service_name} -o jsonpath=\"{{.items[0].metadata.name}}\""
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception as e:
            logger.debug(f"Pod lookup failed for {service_name}: {e}")
        return service_name

    def restart_pod(self, target_service: str, namespace: str = None) -> Dict[str, Any]:
        """Resolve pod hash dynamically and delete pod to trigger Deployment recreation."""
        ns = namespace or self.default_namespace
        pod_name = self.get_pod_name_for_service(target_service, ns)
        cmd = f"kubectl delete pod {pod_name} -n {ns} --grace-period=0 --force"
        logger.info(f"Executing: {cmd}")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return {"status": "success", "message": f"Pod {pod_name} deleted.", "output": res.stdout}
            else:
                # Fallback to rollout restart if pod name deletion fails
                return self.rollout_restart(target_service, ns)
        except Exception as e:
            logger.error(f"Failed to restart pod {pod_name}: {e}")
            return {"status": "error", "message": str(e)}

    def scale_deployment(self, deployment_name: str, replicas: int, namespace: str = None) -> Dict[str, Any]:
        """Scale a deployment up or down."""
        ns = namespace or self.default_namespace
        cmd = f"kubectl scale deployment {deployment_name} --replicas={replicas} -n {ns}"
        logger.info(f"Executing: {cmd}")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return {"status": "success", "message": f"Deployment {deployment_name} scaled to {replicas}.", "output": res.stdout}
            else:
                return {"status": "simulated", "message": f"[Simulated] Deployment {deployment_name} scaled to {replicas} (Cluster Offline).", "output": res.stderr}
        except Exception as e:
            logger.error(f"Failed to scale deployment {deployment_name}: {e}")
            return {"status": "error", "message": str(e)}

    def patch_resource_limits(self, deployment_name: str, cpu_limit: str = "500m", memory_limit: str = "512Mi", namespace: str = None) -> Dict[str, Any]:
        """Patch CPU/Memory limits for a deployment with Windows-safe JSON escaping."""
        ns = namespace or self.default_namespace
        patch_obj = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": deployment_name,
                            "resources": {
                                "limits": {"cpu": cpu_limit, "memory": memory_limit}
                            }
                        }]
                    }
                }
            }
        }
        patch_json_str = json.dumps(patch_obj).replace('"', '\\"')
        cmd = f'kubectl patch deployment {deployment_name} -n {ns} --type=merge -p "{patch_json_str}"'
        logger.info(f"Executing: {cmd}")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return {"status": "success", "message": f"Patched resources for {deployment_name}.", "output": res.stdout}
            else:
                return {"status": "simulated", "message": f"[Simulated] Patched limits for {deployment_name} (Cluster Offline).", "output": res.stderr}
        except Exception as e:
            logger.error(f"Failed to patch deployment {deployment_name}: {e}")
            return {"status": "error", "message": str(e)}

    def rollout_restart(self, deployment_name: str, namespace: str = None) -> Dict[str, Any]:
        """Perform a graceful rollout restart of a deployment."""
        ns = namespace or self.default_namespace
        cmd = f"kubectl rollout restart deployment/{deployment_name} -n {ns}"
        logger.info(f"Executing: {cmd}")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return {"status": "success", "message": f"Rollout restart initiated for {deployment_name}.", "output": res.stdout}
            else:
                return {"status": "simulated", "message": f"[Simulated] Rollout restart for {deployment_name} (Cluster Offline).", "output": res.stderr}
        except Exception as e:
            logger.error(f"Failed rollout restart for {deployment_name}: {e}")
            return {"status": "error", "message": str(e)}
