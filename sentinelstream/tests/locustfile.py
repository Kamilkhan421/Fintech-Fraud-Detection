"""Locust load testing configuration"""
from locust import HttpUser, task, between
import uuid


class TransactionUser(HttpUser):
    """Load test user for transaction endpoint"""
    wait_time = between(0.1, 0.5)  # Wait between 0.1 and 0.5 seconds
    
    @task(10)
    def process_transaction(self):
        """Process a transaction"""
        payload = {
            "user_id": f"user_{uuid.uuid4().hex[:8]}",
            "amount": 100.0,
            "currency": "USD",
            "location": "New York, NY",
            "merchant_id": f"merchant_{uuid.uuid4().hex[:8]}",
            "transaction_type": "purchase",
            "idempotency_key": str(uuid.uuid4()),
            "metadata": {}
        }
        self.client.post("/transaction", json=payload)
    
    @task(2)
    def health_check(self):
        """Check health endpoint"""
        self.client.get("/health")
    
    @task(1)
    def get_balance(self):
        """Get user balance"""
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        self.client.get(f"/balance/{user_id}")

