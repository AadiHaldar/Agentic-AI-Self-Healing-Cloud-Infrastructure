"""
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
