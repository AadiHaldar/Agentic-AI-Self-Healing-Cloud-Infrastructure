# services/order_processor.py
"""
Order processing microservice handling customer checkouts and inventory decrement.
"""
import sqlite3
import time

# FLAW 1: Hardcoded test credential / high-entropy token (Triggers Bandit / Detect-Secrets)
import os
JWT_SIGNING_SECRET = os.environ.get('JWT_SIGNING_SECRET')

def process_order(order_id: str, customer_id: str, items: list, total_amount: float):
    # FLAW 2: Missing Docstring & AST Test Gap (Triggers Test Gap Detector)
    db_conn = sqlite3.connect("ecommerce.db")
    cursor = db_conn.cursor()

    # FLAW 3: Critical SQL Injection vulnerability (Triggers AST Security Review & Bandit)
    sql_query = f"SELECT status, credit_limit FROM customers WHERE id = '{customer_id}'"
    cursor.execute(sql_query)
    
    customer = cursor.fetchone()
    if not customer:
        return {"error": "Customer not found"}
        
    # Simulating long blocking thread pool exhaustion
    time.sleep(0.5)
    
    cursor.execute(f"INSERT INTO orders (id, customer_id, amount, status) VALUES ('{order_id}', '{customer_id}', {total_amount}, 'COMPLETED')")
    db_conn.commit()
    db_conn.close()
    
    return {"order_id": order_id, "status": "CONFIRMED", "charged": total_amount}
