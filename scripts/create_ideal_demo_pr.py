"""
scripts/create_ideal_demo_pr.py — Script to generate the ideal end-to-end demo Pull Request on GitHub.

Creates a realistic microservice feature PR with:
  • OWASP Top 10 Vulnerabilities:
      - A01: Path Traversal
      - A02: Weak MD5 Hashing & Plaintext Secret
      - A03: SQL Injection (f-string) & Command Injection
      - A06: Vulnerable Dependencies (PyYAML / Requests CVEs)
      - A08: Insecure Deserialization (pickle)
      - A09: Silently Swallowed Exceptions
  • AST Test Coverage Gaps (functions missing in tests/)
  • Multi-service Call Graph for Mermaid.js rendering
  • Automated Quality Gate Failure (Red ❌)
"""
import os
import sys
import subprocess
import time
import json

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pr_review_agent.owasp_auditor import OWASPAuditor
from pr_review_agent.pipeline import (
    _build_review_body,
    _build_inline_comments,
    detect_unit_test_gaps,
    generate_mermaid_diagram,
    run_static_analysis,
    deduplicate_findings
)


CHECKOUT_GATEWAY_CODE = '''"""
services/checkout_gateway.py — V2 Checkout Gateway Microservice.
Handles high-throughput order execution, cryptographic verification, session restoration, and external webhooks.
"""
import os
import hashlib
import subprocess
import pickle
import logging
import requests
import jwt
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# [OWASP A05:2021] Security Misconfiguration: Debug mode enabled in production code
DEBUG = True

# [OWASP A02:2021] Cryptographic Failures: Hardcoded API secret key in source file
STRIPE_GATEWAY_SECRET = "sk_test_mock_dummy_checkout_secret_key_8899"

# [OWASP A07:2021] Identification & Authentication Failures: Hardcoded JWT authentication token
JWT_AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock_unverified_payload_secret_key_77"


def get_order_by_id(db_conn, order_id: str) -> Optional[Dict[str, Any]]:
    """Fetch order details from the database."""
    # [OWASP A03:2021 / CWE-89] SQL Injection via f-string string concatenation
    query = f"SELECT id, user_id, amount, status FROM orders WHERE id = '{order_id}'"
    cursor = db_conn.cursor()
    cursor.execute(query)
    return cursor.fetchone()


def verify_order_signature(order_payload: str, expected_signature: str) -> bool:
    """Verify order HMAC digest against expected signature."""
    # [OWASP A02:2021 / CWE-328] Cryptographic Failure: MD5 is broken and collision-prone
    computed_digest = hashlib.md5(order_payload.encode("utf-8")).hexdigest()
    return computed_digest == expected_signature


def restore_user_cart_session(raw_session_bytes: bytes) -> Dict[str, Any]:
    """Restore serialized shopping cart cache from Redis."""
    # [OWASP A08:2021 / CWE-502] Insecure Deserialization: arbitrary code execution risk
    cart_obj = pickle.loads(raw_session_bytes)
    return cart_obj


def export_order_invoice_pdf(order_id: str, template_filename: str) -> str:
    """Export generated PDF invoice to filesystem."""
    # [OWASP A01:2021 / CWE-22] Broken Access Control / Path Traversal risk
    output_path = os.path.join("/var/log/invoices", template_filename)
    
    # [OWASP A03:2021 / CWE-78] Command Injection: shell=True passes unchecked variables to shell
    cmd = f"wkhtmltopdf --order-id {order_id} {output_path}"
    subprocess.Popen(cmd, shell=True)
    return output_path


def decode_user_session_token(token: str) -> Dict[str, Any]:
    """Decode and authenticate JWT session token without cryptographic verification."""
    # [OWASP A07:2021 / CWE-287] Identification & Authentication Failure: unverified signature decode
    user_claims = jwt.decode(token, verify=False)
    return user_claims


def fetch_unbounded_order_archive(db_conn) -> List[Dict[str, Any]]:
    """Fetch entire historical order database without pagination limits."""
    # [OWASP A04:2021 / CWE-400] Insecure Design: unconstrained memory consumption & OOM DoS risk
    return fetch_unbounded(db_conn)


def send_payment_webhook(target_url: str, payload: Dict[str, Any]) -> int:
    """Send payment notification webhook to external partner endpoint."""
    # [OWASP A10:2021 / CWE-918] Server-Side Request Forgery (SSRF) to unvalidated URL
    response = requests.get(target_url)
    return response.status_code


def process_crypto_payment(wallet_address: str, satoshi_amount: int) -> bool:
    """
    [AST Test Gap] New public payment gateway feature added without unit tests in tests/!
    """
    if satoshi_amount <= 0:
        return False
    logger.info(f"Submitting {satoshi_amount} satoshis to wallet {wallet_address}")
    return True


def audit_transaction_metrics(order_id: str, amount: float) -> None:
    """Record metrics to internal telemetry log."""
    try:
        if amount < 0:
            raise ValueError("Negative transaction amount")
    except Exception:
        # [OWASP A09:2021 / CWE-778] Security Logging & Monitoring Failure: silently swallowed error
        pass


def fetch_unbounded(db_conn) -> List[Dict[str, Any]]:
    """Helper representing unconstrained query execution."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM orders")
    return cursor.fetchall()
'''

ORDER_ORCHESTRATOR_CODE = '''"""
services/order_orchestrator.py — Microservice Call Router.
Demonstrates inter-service import dependencies for Mermaid.js graph rendering.
"""
from services.checkout_gateway import get_order_by_id, process_crypto_payment
from services.billing_gateway import charge_customer_card
from services.payment_client import PaymentServiceClient

class OrderOrchestrator:
    def __init__(self):
        self.client = PaymentServiceClient()

    def handle_checkout(self, user_id: str, amount: float):
        order = get_order_by_id(None, user_id)
        charge_customer_card(user_id, amount)
        return order
'''

VULNERABLE_REQUIREMENTS_TXT = """fastapi==0.115.0
pydantic==2.8.2
pyyaml==5.3
requests==2.28.0
scikit-learn==1.4.0
simpy==4.1.1
"""


def main():
    print("=" * 70)
    print("[*] AgentHeal Ideal Demo PR Generator (Shift-Left + OWASP Top 10)")
    print("=" * 70)

    # 1. Check git status
    curr_branch = subprocess.check_output(["git", "branch", "--show-current"]).decode("utf-8").strip()
    print(f"[*] Current branch: {curr_branch}")

    demo_branch = "feature/v2-checkout-gateway"
    print(f"[*] Creating demo branch: {demo_branch}")
    subprocess.run(["git", "checkout", "-B", demo_branch], check=True)

    # 2. Write demo files
    os.makedirs("services", exist_ok=True)
    with open("services/checkout_gateway.py", "w", encoding="utf-8") as f:
        f.write(CHECKOUT_GATEWAY_CODE)
    with open("services/order_orchestrator.py", "w", encoding="utf-8") as f:
        f.write(ORDER_ORCHESTRATOR_CODE)
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(VULNERABLE_REQUIREMENTS_TXT)

    print("[*] Modified files written:")
    print("    - services/checkout_gateway.py (OWASP A01, A02, A03, A08, A09 + AST Test Gap)")
    print("    - services/order_orchestrator.py (Mermaid dependency call graph)")
    print("    - requirements.txt (OWASP A06 / Dependabot CVEs)")

    # 3. Commit and push
    subprocess.run(["git", "add", "services/checkout_gateway.py", "services/order_orchestrator.py", "requirements.txt"], check=True)
    subprocess.run(["git", "commit", "-m", "feat(checkout): add v2 checkout gateway & dynamic order processing"], check=True)
    
    print(f"[*] Pushing branch '{demo_branch}' to origin...")
    subprocess.run(["git", "push", "-u", "origin", demo_branch, "--force"], check=True)

    # 4. Open Pull Request with GitHub CLI
    print("[*] Opening Pull Request on GitHub...")
    pr_body = """### [PR Overview]
This PR implements the **V2 Checkout Gateway Microservice** with crypto payment settlement, session caching, and asynchronous PDF invoice generation.

### Changes:
1. `services/checkout_gateway.py`: New checkout order query engine and Redis cart session restorer.
2. `services/order_orchestrator.py`: Inter-service routing connecting `frontend -> checkout_gateway -> billing_gateway`.
3. `requirements.txt`: Updated library requirements for YAML templates and HTTP clients.

---
*Awaiting automated review by @review-bot and Quality Gate validation.*"""

    try:
        pr_out = subprocess.check_output([
            "gh", "pr", "create",
            "--title", "feat(checkout): add v2 checkout gateway & dynamic order processing",
            "--body", pr_body,
            "--base", "main",
            "--head", demo_branch
        ]).decode("utf-8").strip()
        print(f"\n[SUCCESS] PR Created successfully: {pr_out}")
    except subprocess.CalledProcessError:
        print(f"[*] Note: PR might already exist. Viewing existing PR info...")
        try:
            pr_out = subprocess.check_output(["gh", "pr", "view", demo_branch, "--json", "url", "-q", ".url"]).decode("utf-8").strip()
            print(f"[*] Existing PR URL: {pr_out}")
        except Exception:
            pr_out = "https://github.com/AadiHaldar/Agentic-AI-Self-Healing-Cloud-Infrastructure/pulls"

    # 5. Run OWASP Audit & Generate Local Review Simulation
    print("\n" + "=" * 70)
    print("[*] Running AgentHeal 12-Stage Audit & OWASP Top 10 Security Engine")
    print("=" * 70)
    
    auditor = OWASPAuditor()
    findings = auditor.audit_python_code(CHECKOUT_GATEWAY_CODE, "services/checkout_gateway.py")
    req_findings = auditor.audit_requirements_txt(VULNERABLE_REQUIREMENTS_TXT, "requirements.txt")

    diff_payload = [
        {"filename": "services/checkout_gateway.py", "patch": "\n".join(["+" + l for l in CHECKOUT_GATEWAY_CODE.splitlines()])},
        {"filename": "services/order_orchestrator.py", "patch": "\n".join(["+" + l for l in ORDER_ORCHESTRATOR_CODE.splitlines()])},
        {"filename": "requirements.txt", "patch": VULNERABLE_REQUIREMENTS_TXT},
    ]

    owasp_result = auditor.audit_pr_diff(diff_payload)
    print(f"\n[+] OWASP Compliance Score: {owasp_result.compliance_score}% (Grade: {owasp_result.grade})")
    print(f"[+] Total Violations Detected: {owasp_result.total_findings}")
    for cat_id, count in owasp_result.findings_by_category.items():
        print(f"    - {cat_id}: {count} issue(s)")

    # Test Gap
    gaps = detect_unit_test_gaps(diff_payload)
    print(f"\n[+] AST Test Coverage Gaps: {len(gaps)} function(s) missing unit tests")
    for g in gaps:
        print(f"    - {g['file']}:{g['line']} -> {g['message']}")

    # Mermaid
    mermaid = generate_mermaid_diagram(diff_payload, min_files=1)
    print(f"\n[+] Mermaid Call Graph Generated:\n```mermaid\n{mermaid}\n```")

    # Switch back to main
    subprocess.run(["git", "checkout", "main"], check=True)
    print("\n[OK] Switched local workspace back to 'main' branch.")
    print(f"[DEMO LINK] You can present this PR live in your browser: {pr_out}")


if __name__ == "__main__":
    main()
