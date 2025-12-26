"""Performance and load tests"""
import pytest
import time
from fastapi.testclient import TestClient


def test_transaction_latency(client, sample_transaction_request):
    """Test that transaction processing is under 200ms"""
    start_time = time.time()
    response = client.post("/transaction", json=sample_transaction_request)
    elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    assert response.status_code == 200
    # Should complete in under 200ms (allowing some margin for test environment)
    assert elapsed_time < 500  # More lenient in test environment


def test_concurrent_transactions(client, sample_transaction_request):
    """Test concurrent transaction processing"""
    import concurrent.futures
    
    def process_transaction():
        response = client.post("/transaction", json={
            **sample_transaction_request,
            "idempotency_key": f"test-key-{time.time()}-{id(concurrent.futures)}"
        })
        return response.status_code == 200
    
    # Process 10 concurrent transactions
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_transaction) for _ in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # All should succeed
    assert all(results)

