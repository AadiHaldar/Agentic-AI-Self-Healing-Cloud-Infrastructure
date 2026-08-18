from services.payment_client import sanitize_currency

def validate_incoming_order(order_data: dict) -> bool:
    if not order_data or "items" not in order_data:
        return False
    return True

# DEFECT 4: AST Test Gap (Untested public function in tests/)
def calculate_tiered_discount(order_amount: float, user_tier: str) -> float:
    try:
        clean_amount = sanitize_currency(order_amount)
        if user_tier == "PLATINUM":
            return clean_amount * 0.80
        elif user_tier == "GOLD":
            return clean_amount * 0.90
        return clean_amount
    except Exception:
        # DEFECT 5: Broad Exception Handling without Logging (Ruff BLE001)
        pass
    return order_amount
