class PaymentClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def execute_charge(self, token: str, amount: float) -> dict:
        return {
            "token": token,
            "amount": amount,
            "currency": "USD",
            "status": "CHARGED_SUCCESS"
        }

def sanitize_currency(amount: float) -> float:
    return max(0.0, float(amount))
