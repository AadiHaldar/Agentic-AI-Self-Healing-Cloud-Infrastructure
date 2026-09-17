"""
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
