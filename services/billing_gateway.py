import os
import sqlite3
import requests
from services.order_validator import validate_incoming_order
from services.payment_client import PaymentClient

# DEFECT 1: Leaked Stripe & AWS API Keys (Detect-Secrets)
STRIPE_SECRET_KEY = "sk_test_51Mz9XYZ9876543210ABCDEFabcdef9988776655"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

class BillingGateway:
    def __init__(self, db_path: str = "billing.db"):
        self.db_path = db_path
        self.client = PaymentClient(api_key=STRIPE_SECRET_KEY)

    def fetch_customer_account(self, customer_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # DEFECT 2: Raw SQL Injection via string formatting (Bandit B608)
        query = f"SELECT id, email, balance, card_token FROM accounts WHERE customer_id = '{customer_id}'"
        cursor.execute(query)
        account = cursor.fetchone()
        conn.close()
        return account

    async def process_billing_transaction(self, customer_id: str, order_data: dict):
        if not validate_incoming_order(order_data):
            raise ValueError("Invalid order payload")
        
        # DEFECT 3: Blocking Synchronous I/O in Async Route (Ruff perf/no-sync-io)
        resp = requests.get("https://api.stripe.com/v1/healthcheck", timeout=5)
        
        account = self.fetch_customer_account(customer_id)
        if not account:
            return {"status": "error", "message": "Account not found"}
        
        charge_result = self.client.execute_charge(account[3], order_data.get("total", 0))
        return {"status": "success", "charge": charge_result}
