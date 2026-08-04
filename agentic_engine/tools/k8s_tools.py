import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class K8sRemediationTools:
    """
    Executes actual Kubernetes control-plane operations using kubectl / K8s API.
    """
    def __init__(self, default_namespace: str = "online-boutique"):
        self.default_namespace = default_namespace

    def restart_pod(self, pod_name: str, namespace: str = None) -> Dict[str, Any]:
        """Delete a pod to trigger its Deployment/StatefulSet to recreate it."""
        ns = namespace or self.default_namespace
        cmd = f"kubectl delete pod {pod_name} -n {ns} --grace-period=0 --force"
        logger.info(f"Executing: {cmd}")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return {"status": "success", "message": f"Pod {pod_name} deleted.", "output": res.stdout}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart pod {pod_name}: {e.stderr}")
            return {"status": "error", "message": e.stderr}

    def scale_deployment(self, deployment_name: str, replicas: int, namespace: str = None) -> Dict[str, Any]:
        """Scale a deployment up or down."""
        ns = namespace or self.default_namespace
        cmd = f"kubectl scale deployment {deployment_name} --replicas={replicas} -n {ns}"
        logger.info(f"Executing: {cmd}")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return {"status": "success", "message": f"Deployment {deployment_name} scaled to {replicas}.", "output": res.stdout}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to scale deployment {deployment_name}: {e.stderr}")
            return {"status": "error", "message": e.stderr}

    def patch_resource_limits(self, deployment_name: str, cpu_limit: str, memory_limit: str, namespace: str = None) -> Dict[str, Any]:
        """Patch CPU/Memory limits for a deployment."""
        ns = namespace or self.default_namespace
        patch_json = f'{{"spec": {{"template": {{"spec": {{"containers": [{{"name": "{deployment_name}", "resources": {{"limits": {{"cpu": "{cpu_limit}", "memory": "{memory_limit}"}}}}}}]}}}}}}}}'
        cmd = f"kubectl patch deployment {deployment_name} -n {ns} --type=merge -p '{patch_json}'"
        logger.info(f"Executing: {cmd}")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return {"status": "success", "message": f"Patched resources for {deployment_name}.", "output": res.stdout}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to patch deployment {deployment_name}: {e.stderr}")
            return {"status": "error", "message": e.stderr}

    def rollout_restart(self, deployment_name: str, namespace: str = None) -> Dict[str, Any]:
        """Perform a graceful rollout restart of a deployment."""
        ns = namespace or self.default_namespace
        cmd = f"kubectl rollout restart deployment/{deployment_name} -n {ns}"
        logger.info(f"Executing: {cmd}")
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return {"status": "success", "message": f"Rollout restart initiated for {deployment_name}.", "output": res.stdout}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed rollout restart for {deployment_name}: {e.stderr}")
            return {"status": "error", "message": e.stderr}
