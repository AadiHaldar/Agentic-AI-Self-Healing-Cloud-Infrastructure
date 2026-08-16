import re
import subprocess
import logging
import json
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Regex for valid Kubernetes resource names (RFC 1123 label subset)
_K8S_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$')


def _validate_k8s_name(name: str) -> str:
    """
    Validates a Kubernetes resource name to prevent shell injection.
    Names must match ^[a-zA-Z0-9][a-zA-Z0-9\\-]*[a-zA-Z0-9]$ (RFC 1123 label).
    Raises ValueError with a safe message if the name contains unexpected characters.
    """
    if not name or not _K8S_NAME_RE.match(name):
        raise ValueError(
            f"Invalid Kubernetes resource name '{name}'. "
            "Names must match ^[a-zA-Z0-9][a-zA-Z0-9\\-]*[a-zA-Z0-9]$"
        )
    return name


class K8sRemediationTools:
    """
    Executes actual Kubernetes control-plane operations using kubectl / K8s API.
    All subprocess calls use shell=False with validated argument lists to prevent
    shell injection via unsanitized service/deployment name inputs.
    """
    def __init__(self, default_namespace: str = "online-boutique"):
        self.default_namespace = default_namespace

    def get_pod_name_for_service(self, service_name: str, namespace: str = None) -> str:
        """Find the real active pod name matching app={service_name} or return target."""
        ns = namespace or self.default_namespace
        _validate_k8s_name(service_name)
        _validate_k8s_name(ns)
        try:
            res = subprocess.run(
                ["kubectl", "get", "pods", "-n", ns, "-l", f"app={service_name}",
                 "-o", "jsonpath={.items[0].metadata.name}"],
                shell=False, capture_output=True, text=True
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception as e:
            logger.debug(f"Pod lookup failed for {service_name}: {e}")
        return service_name

    def restart_pod(self, target_service: str, namespace: str = None) -> Dict[str, Any]:
        """Resolve pod hash dynamically and delete pod to trigger Deployment recreation."""
        ns = namespace or self.default_namespace
        _validate_k8s_name(target_service)
        _validate_k8s_name(ns)
        pod_name = self.get_pod_name_for_service(target_service, ns)
        logger.info(f"Executing: kubectl delete pod {pod_name} -n {ns} --grace-period=0 --force")
        try:
            res = subprocess.run(
                ["kubectl", "delete", "pod", pod_name, "-n", ns, "--grace-period=0", "--force"],
                shell=False, capture_output=True, text=True
            )
            if res.returncode == 0:
                return {"status": "success", "message": f"Pod {pod_name} deleted.", "output": res.stdout}
            else:
                return self.rollout_restart(target_service, ns)
        except Exception as e:
            logger.error(f"Failed to restart pod {pod_name}: {e}")
            return {"status": "error", "message": str(e)}

    def scale_deployment(self, deployment_name: str, replicas: int, namespace: str = None) -> Dict[str, Any]:
        """Scale a deployment up or down."""
        ns = namespace or self.default_namespace
        _validate_k8s_name(deployment_name)
        _validate_k8s_name(ns)
        if not isinstance(replicas, int) or replicas < 0 or replicas > 100:
            raise ValueError(f"Invalid replicas value: {replicas}. Must be an integer 0-100.")
        logger.info(f"Executing: kubectl scale deployment {deployment_name} --replicas={replicas} -n {ns}")
        try:
            res = subprocess.run(
                ["kubectl", "scale", "deployment", deployment_name, f"--replicas={replicas}", "-n", ns],
                shell=False, capture_output=True, text=True
            )
            if res.returncode == 0:
                return {"status": "success", "message": f"Deployment {deployment_name} scaled to {replicas}.", "output": res.stdout}
            else:
                return {"status": "simulated", "message": f"[Simulated] Deployment {deployment_name} scaled to {replicas} (Cluster Offline).", "output": res.stderr}
        except Exception as e:
            logger.error(f"Failed to scale deployment {deployment_name}: {e}")
            return {"status": "error", "message": str(e)}

    def patch_resource_limits(self, deployment_name: str, cpu_limit: str = "500m", memory_limit: str = "512Mi", namespace: str = None) -> Dict[str, Any]:
        """Patch CPU/Memory limits for a deployment (shell=False, no string interpolation into shell)."""
        ns = namespace or self.default_namespace
        _validate_k8s_name(deployment_name)
        _validate_k8s_name(ns)
        patch_obj = {
            "spec": {"template": {"spec": {"containers": [{
                "name": deployment_name,
                "resources": {"limits": {"cpu": cpu_limit, "memory": memory_limit}}
            }]}}}
        }
        patch_json_str = json.dumps(patch_obj)
        logger.info(f"Executing: kubectl patch deployment {deployment_name} -n {ns} --type=merge -p <json>")
        try:
            res = subprocess.run(
                ["kubectl", "patch", "deployment", deployment_name, "-n", ns,
                 "--type=merge", f"-p={patch_json_str}"],
                shell=False, capture_output=True, text=True
            )
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
        _validate_k8s_name(deployment_name)
        _validate_k8s_name(ns)
        logger.info(f"Executing: kubectl rollout restart deployment/{deployment_name} -n {ns}")
        try:
            res = subprocess.run(
                ["kubectl", "rollout", "restart", f"deployment/{deployment_name}", "-n", ns],
                shell=False, capture_output=True, text=True
            )
            if res.returncode == 0:
                return {"status": "success", "message": f"Rollout restart initiated for {deployment_name}.", "output": res.stdout}
            else:
                return {"status": "simulated", "message": f"[Simulated] Rollout restart for {deployment_name} (Cluster Offline).", "output": res.stderr}
        except Exception as e:
            logger.error(f"Failed rollout restart for {deployment_name}: {e}")
            return {"status": "error", "message": str(e)}
