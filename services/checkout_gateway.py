"""
services/checkout_gateway.py — V2 Checkout Gateway Microservice.
Handles high-throughput order execution, cryptographic verification, and state restore.
"""
import os
import hashlib
import subprocess
import pickle
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# [OWASP A05] Security Misconfiguration: Debug mode enabled in production code
DEBUG = True

# [OWASP A02] Cryptographic Failure: Hardcoded API secret key in source file
STRIPE_GATEWAY_SECRET = "sk_test_mock_dummy_checkout_secret_key_8899"


def get_order_by_id(db_conn, order_id: str) -> Optional[Dict[str, Any]]:
    """Fetch order details from the database."""
    # [OWASP A03 / Bandit B608] Critical SQL Injection via f-string string concatenation
    query = f"SELECT id, user_id, amount, status FROM orders WHERE id = '{order_id}'"
    cursor = db_conn.cursor()
    cursor.execute(query)
    return cursor.fetchone()


def verify_order_signature(order_payload: str, expected_signature: str) -> bool:
    """Verify order HMAC digest against expected signature."""
    # [OWASP A02] Cryptographic Failure: MD5 is broken and collision-prone
    computed_digest = hashlib.md5(order_payload.encode("utf-8")).hexdigest()
    return computed_digest == expected_signature


def restore_user_cart_session(raw_session_bytes: bytes) -> Dict[str, Any]:
    """Restore serialized shopping cart cache from Redis."""
    # [OWASP A08 / Bandit B301] Insecure Deserialization: arbitrary code execution risk
    cart_obj = pickle.loads(raw_session_bytes)
    return cart_obj


def export_order_invoice_pdf(order_id: str, template_filename: str) -> str:
    """Export generated PDF invoice to filesystem."""
    # [OWASP A01] Broken Access Control / Path Traversal risk
    output_path = os.path.join("/var/log/invoices", template_filename)
    
    # [OWASP A03] Command Injection: shell=True passes unchecked variables to shell
    cmd = f"wkhtmltopdf --order-id {order_id} {output_path}"
    subprocess.Popen(cmd, shell=True)
    return output_path


def process_crypto_payment(wallet_address: str, satoshi_amount: int) -> bool:
    """
    [AST Test Gap] New public feature added without any unit tests in tests/!
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
        # [OWASP A09] Security Logging & Monitoring Failure: silently swallowed error
        pass
