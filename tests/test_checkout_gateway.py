"""
tests/test_checkout_gateway.py — Comprehensive Unit Tests resolving AST Coverage Gaps.
"""
import pytest
from unittest.mock import MagicMock
from services.checkout_gateway import (
    get_order_by_id,
    verify_order_signature,
    restore_user_cart_session,
    export_order_invoice_pdf,
    process_crypto_payment,
    audit_transaction_metrics
)


def test_get_order_by_id_parameterized():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {"id": "ord_101", "amount": 99.9}

    res = get_order_by_id(mock_conn, "ord_101")
    assert res["id"] == "ord_101"
    mock_cursor.execute.assert_called_once()
    args, kwargs = mock_cursor.execute.call_args
    assert "?" in args[0]
    assert args[1] == ("ord_101",)


def test_process_crypto_payment():
    assert process_crypto_payment("0x1234abcd", 5000) is True
    assert process_crypto_payment("0x1234abcd", -10) is False
    assert process_crypto_payment("", 5000) is False


def test_restore_user_cart_session_safe_json():
    valid_json = '{"cart_id": "c99", "items": ["item1", "item2"]}'
    data = restore_user_cart_session(valid_json)
    assert data["cart_id"] == "c99"
    assert len(data["items"]) == 2

    # Invalid JSON returns empty dict safely without crashing
    assert restore_user_cart_session("invalid-bytes") == {}


def test_audit_transaction_metrics():
    # Verify no unhandled crash on valid or negative amount
    audit_transaction_metrics("ord_101", 150.0)
    audit_transaction_metrics("ord_102", -50.0)
