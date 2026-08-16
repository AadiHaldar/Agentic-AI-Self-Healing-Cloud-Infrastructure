import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from agentic_engine.tools.k8s_tools import K8sRemediationTools, _validate_k8s_name
from agentic_engine.tools.github_tools import GitHubManager, github_manager
from dashboard.backend.main import app


class TestK8sToolsHardening(unittest.TestCase):
    """
    Validates Bug 4 fixes in k8s_tools.py:
    - Input validation on Kubernetes resource names
    - Prevention of shell injection vectors
    - Guarantee of shell=False on all subprocess calls
    - Replica count boundaries
    """
    def setUp(self):
        self.k8s = K8sRemediationTools(default_namespace="online-boutique")

    def test_validate_k8s_name_valid_names(self):
        valid_names = [
            "frontend",
            "checkoutservice",
            "cart-service-123",
            "redis-cart",
            "service1",
            "a",
            "default"
        ]
        for name in valid_names:
            self.assertEqual(_validate_k8s_name(name), name)

    def test_validate_k8s_name_rejects_shell_injections(self):
        malicious_names = [
            "frontend; rm -rf /",
            "checkoutservice | cat /etc/passwd",
            "service`whoami`",
            "cart$(reboot)",
            "service && touch pwned",
            "service\nmalicious",
            "service 123",
            "-leading-hyphen",
            "trailing-hyphen-",
            "service'OR'1'='1",
            "",
            None
        ]
        for bad_name in malicious_names:
            with self.assertRaises(ValueError, msg=f"Failed to reject malicious input: {bad_name}"):
                _validate_k8s_name(bad_name)

    def test_scale_deployment_replica_bounds(self):
        # Valid replica count should not raise ValueError
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="scaled")
            res = self.k8s.scale_deployment("checkoutservice", replicas=3)
            self.assertEqual(res["status"], "success")

        # Invalid replicas: negative, excessive, or wrong type
        with self.assertRaises(ValueError):
            self.k8s.scale_deployment("checkoutservice", replicas=-1)
        with self.assertRaises(ValueError):
            self.k8s.scale_deployment("checkoutservice", replicas=101)
        with self.assertRaises(ValueError):
            self.k8s.scale_deployment("checkoutservice", replicas="three")

    @patch("subprocess.run")
    def test_all_k8s_methods_use_shell_false(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        # 1. restart_pod
        self.k8s.restart_pod("frontend")
        for call in mock_run.call_args_list:
            args, kwargs = call
            self.assertFalse(kwargs.get("shell", True), "restart_pod must pass shell=False")
            self.assertIsInstance(args[0], list, "Command must be passed as an argument list")

        mock_run.reset_mock()

        # 2. scale_deployment
        self.k8s.scale_deployment("checkoutservice", replicas=2)
        args, kwargs = mock_run.call_args
        self.assertFalse(kwargs.get("shell", True), "scale_deployment must pass shell=False")
        self.assertIsInstance(args[0], list, "Command must be passed as an argument list")

        mock_run.reset_mock()

        # 3. patch_resource_limits
        self.k8s.patch_resource_limits("cartservice", cpu_limit="500m", memory_limit="512Mi")
        args, kwargs = mock_run.call_args
        self.assertFalse(kwargs.get("shell", True), "patch_resource_limits must pass shell=False")
        self.assertIsInstance(args[0], list, "Command must be passed as an argument list")

        mock_run.reset_mock()

        # 4. rollout_restart
        self.k8s.rollout_restart("redis-cart")
        args, kwargs = mock_run.call_args
        self.assertFalse(kwargs.get("shell", True), "rollout_restart must pass shell=False")
        self.assertIsInstance(args[0], list, "Command must be passed as an argument list")


class TestGitHubToolsBugFixes(unittest.TestCase):
    """
    Validates Bug 1, 2, 3 fixes in github_tools.py:
    - Stub replacement for analyze_repository_integrity (Bug 2)
    - Removal of create_readme_architecture_pr and generate_codebase_readme_analysis (Bug 3)
    - Elimination of readme_commit_status NameError in webhook processing (Bug 1)
    - GitOps PR creation functionality
    """
    def setUp(self):
        self.gh = GitHubManager(repo_full_name="test-org/test-repo")

    def test_analyze_repository_integrity_is_safe_stub(self):
        res = self.gh.analyze_repository_integrity("test-org/test-repo")
        self.assertEqual(res["status"], "NOT_IMPLEMENTED")
        self.assertIn("pr_review_agent.pipeline", res["message"])
        self.assertNotIn("integrity_score", res, "Should not return fabricated scores")

    def test_fabricated_readme_methods_are_removed(self):
        self.assertFalse(
            hasattr(self.gh, "create_readme_architecture_pr"),
            "create_readme_architecture_pr must be deleted"
        )
        self.assertFalse(
            hasattr(self.gh, "generate_codebase_readme_analysis"),
            "generate_codebase_readme_analysis must be deleted"
        )

    def test_handle_webhook_event_no_name_error(self):
        payload = {
            "pull_request": {
                "number": 42,
                "title": "Fix memory leak in checkoutservice",
                "head": {"ref": "fix/leak"}
            },
            "repository": {
                "full_name": "test-org/test-repo"
            },
            "sender": {
                "login": "octocat"
            }
        }
        # Execute webhook event handling and ensure no NameError or unhandled exceptions occur
        res = self.gh.handle_webhook_event(payload, event_type="pull_request")
        self.assertEqual(res["status"], "PROCESSED")
        self.assertEqual(res["pr_number"], 42)
        self.assertEqual(res["target_service"], "checkoutservice")
        self.assertIn("report", res)
        self.assertEqual(self.gh.pr_history[0]["pr_number"], 42)

    def test_create_gitops_pr(self):
        res = self.gh.create_gitops_pr(service="checkoutservice", replicas=4, cpu_limit="1000m")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["type"], "GITOPS_SCALING")
        self.assertIn("Scale checkoutservice to 4 replicas", res["pr_title"])
        self.assertIn("checkoutservice", res["diff"])

    def test_create_code_patch_pr(self):
        res = self.gh.create_code_patch_pr(
            service="checkoutservice",
            file_path="src/handler.py",
            issue_summary="Circuit breaker timeout"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["type"], "CODE_PATCH")
        self.assertIn("Fix application exception", res["pr_title"])


class TestBackendAPIRoutes(unittest.TestCase):
    """
    Validates Phase 2 and dashboard API endpoints:
    - Verifies /api/github/scan-integrity is removed (returns 404)
    - Verifies all standard routes operate correctly (/status, /topology, /github/prs, /override, /github/webhook)
    """
    def setUp(self):
        self.client = TestClient(app)

    def test_scan_integrity_route_is_removed(self):
        response = self.client.get("/api/github/scan-integrity")
        self.assertEqual(
            response.status_code, 404,
            "Fabricated route /api/github/scan-integrity must return 404 Not Found"
        )

    def test_get_status_endpoint(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("total_pods", data)
        self.assertIn("active_anomalies", data)
        self.assertIn("anomalous_pods", data)

    def test_get_topology_endpoint(self):
        response = self.client.get("/api/topology")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("nodes", data)
        self.assertIn("links", data)

    def test_get_github_prs_endpoint(self):
        response = self.client.get("/api/github/prs")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("prs", data)
        self.assertIn("is_live_mode", data)
        self.assertIn("repo", data)

    def test_post_github_create_pr_endpoint(self):
        payload = {
            "service": "cartservice",
            "replicas": 3,
            "cpu_limit": "500m",
            "pr_type": "GITOPS"
        }
        response = self.client.post("/api/github/create-pr", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["service"], "cartservice")

    def test_post_github_webhook_endpoint(self):
        payload = {
            "pull_request": {
                "number": 99,
                "title": "Scaling update for redis-cart",
                "head": {"ref": "patch/redis"}
            },
            "repository": {"full_name": "AadiHaldar/test-repo"},
            "sender": {"login": "dev-user"}
        }
        response = self.client.post("/api/github/webhook", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "PROCESSED")
        self.assertEqual(data["pr_number"], 99)

    def test_manual_override_endpoint(self):
        payload = {
            "target_service": "frontend",
            "override_action": "RESTART_POD",
            "reason": "Test operator intervention"
        }
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="deleted")
            response = self.client.post("/api/override", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("Operator manually applied", data["message"])


if __name__ == "__main__":
    unittest.main()
