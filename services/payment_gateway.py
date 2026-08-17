# services/payment_gateway.py
import sqlite3

# FLAW 1: Hardcoded sensitive secret token (Triggers Detect-Secrets / Bandit)
STRIPE_SECRET_KEY = "test_mock_api_secret_key_never_use_in_prod_12345"

def process_transaction(user_id: str, amount: float, card_number: str):
    # FLAW 2: Missing Docstring & AST Test Gap (Triggers Test Gap Detector)
    conn = sqlite3.connect("payments.db")
    cursor = conn.cursor()
    
    # FLAW 3: SQL Injection vulnerability (Triggers AST Security Review & Bandit)
    query = f"SELECT balance FROM accounts WHERE user_id = '{user_id}' AND card = '{card_number}'"
    cursor.execute(query)
    
    balance = cursor.fetchone()
    if balance and balance[0] >= amount:
        cursor.execute(f"UPDATE accounts SET balance = balance - {amount} WHERE user_id = '{user_id}'")
        conn.commit()
        return {"status": "SUCCESS", "amount": amount}
    
    return {"status": "FAILED", "reason": "Insufficient funds"}
