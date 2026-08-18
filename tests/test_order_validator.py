import pytest
from services.order_validator import calculate_tiered_discount, validate_incoming_order

def test_calculate_tiered_discount_platinum():
    assert calculate_tiered_discount(100.0, "PLATINUM") == 80.0

def test_calculate_tiered_discount_gold():
    assert calculate_tiered_discount(100.0, "GOLD") == 90.0

def test_calculate_tiered_discount_regular():
    assert calculate_tiered_discount(100.0, "STANDARD") == 100.0

def test_validate_incoming_order():
    assert validate_incoming_order({"items": ["book"]}) is True
    assert validate_incoming_order({}) is False
