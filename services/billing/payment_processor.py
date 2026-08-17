# services/billing/payment_processor.py
"""
High-throughput payment processing engine with card tokenization.
"""
import os
import sqlite3
import time
from services.billing.models import CustomerAccount

STRIPE_LIVE_API_KEY = os.getenv("STRIPE_LIVE_API_KEY")

def charge_customer(account: CustomerAccount, amount: float, card_token: str):
    # FLAW 2: Missing docstring & AST test gap in tests/
    db = sqlite3.connect("billing.db")
    cur = db.cursor()

    # FLAW 3: SQL Injection via f-string (Triggers AST Security & Bandit)
    query = f"SELECT credit_balance FROM accounts WHERE customer_id = '{account.customer_id}'"
    cur.execute(query)

    row = cur.fetchone()
    if row and row[0] >= amount:
        # FLAW 4: Second SQL Injection vulnerability
        cur.execute(f"UPDATE accounts SET credit_balance = credit_balance - {amount} WHERE customer_id = '{account.customer_id}'")
        db.commit()
        db.close()
        return {"status": "SUCCESS", "charged": amount, "customer": account.customer_id}

    db.close()
    return {"status": "INSUFFICIENT_FUNDS", "customer": account.customer_id}