import os
import sqlite3
import httpx
from services.order_validator import validate_incoming_order
from services.payment_client import PaymentClient

# [AUTO-FIX] Loaded secrets securely from environment variables
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY", "")

class BillingGateway:
    def __init__(self, db_path: str = "billing.db"):
        self.db_path = db_path
        self.client = PaymentClient(api_key=STRIPE_SECRET_KEY)

    def fetch_customer_account(self, customer_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # [AUTO-FIX] Parameterized query to completely eliminate SQL injection (Bandit B608)
        query = "SELECT id, email, balance, card_token FROM accounts WHERE customer_id = ?"
        cursor.execute(query, (customer_id,))
        account = cursor.fetchone()
        conn.close()
        return account

    async def process_billing_transaction(self, customer_id: str, order_data: dict):
        if not validate_incoming_order(order_data):
            raise ValueError("Invalid order payload")
        
        # [AUTO-FIX] Non-blocking async HTTP client (Ruff perf/no-sync-io)
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.stripe.com/v1/healthcheck", timeout=5.0)
        
        account = self.fetch_customer_account(customer_id)
        if not account:
            return {"status": "error", "message": "Account not found"}
        
        charge_result = self.client.execute_charge(account[3], order_data.get("total", 0))
        return {"status": "success", "charge": charge_result}
