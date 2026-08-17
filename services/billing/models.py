# services/billing/models.py
"""
Data structures and domain models for the billing system.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class CustomerAccount:
    customer_id: str
    name: str
    email: str
    tier: str = "standard"
    credit_balance: float = 0.0

@dataclass
class InvoiceRecord:
    invoice_id: str
    customer_id: str
    total_amount: float
    status: str = "PENDING"
    stripe_charge_id: Optional[str] = None
