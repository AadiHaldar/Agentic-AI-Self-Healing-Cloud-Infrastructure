# services/billing/invoice_generator.py
"""
Automated invoice generation and PDF receipt creation service.
"""
from services.billing.models import InvoiceRecord, CustomerAccount
from services.billing.payment_processor import charge_customer

def generate_monthly_invoice(account: CustomerAccount, items: list) -> InvoiceRecord:
    # FLAW 5: Missing docstring & AST test gap
    # FLAW 6: Division by zero risk if items is empty
    subtotal = sum(item.get("price", 0.0) * item.get("qty", 1) for item in items)
    average_item_price = subtotal / len(items) if items else 0.0

    # Process charge via payment engine
    payment_result = charge_customer(account, subtotal, "tok_visa_default")
    
    invoice = InvoiceRecord(
        invoice_id=f"INV-{account.customer_id}-2026",
        customer_id=account.customer_id,
        total_amount=subtotal,
        status="PAID" if payment_result["status"] == "SUCCESS" else "FAILED",
        stripe_charge_id=payment_result.get("charge_id")
    )
    return invoice
