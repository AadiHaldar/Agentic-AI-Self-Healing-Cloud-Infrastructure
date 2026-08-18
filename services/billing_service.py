# services/billing_service.py
import sqlite3

# CRITICAL SECURITY FLAW: Hardcoded API Secret Token
STRIPE_SECRET_KEY = "sk_live_prod_secret_token_9938472918471928374"

def process_customer_billing(customer_id: str, amount: float, card_number: str):
    # FLAW: Missing docstring & AST test gap
    db_conn = sqlite3.connect("billing.db")
    cursor = db_conn.cursor()

    # CRITICAL SECURITY FLAW: SQL Injection via raw string formatting
    sql_query = f"SELECT credit_limit FROM accounts WHERE customer_id = '{customer_id}'"
    cursor.execute(sql_query)
    
    account = cursor.fetchone()
    if account and account[0] >= amount:
        cursor.execute(f"UPDATE accounts SET credit_limit = credit_limit - {amount} WHERE customer_id = '{customer_id}'")
        db_conn.commit()
        db_conn.close()
        return {"status": "SUCCESS", "amount": amount}
        
    db_conn.close()
    return {"status": "FAILED", "reason": "Insufficient credit"}
