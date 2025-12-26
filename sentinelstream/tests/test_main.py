"""Tests for main API endpoints"""
import pytest
from fastapi import status


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "database" in data
    assert "redis" in data


def test_process_transaction(client, sample_transaction_request):
    """Test transaction processing"""
    response = client.post("/transaction", json=sample_transaction_request)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "transaction_id" in data
    assert "status" in data
    assert "risk_score" in data
    assert "rule_score" in data
    assert "ml_score" in data
    assert 0.0 <= data["risk_score"] <= 1.0


def test_idempotency(client, sample_transaction_request):
    """Test idempotency key handling"""
    # First request
    response1 = client.post("/transaction", json=sample_transaction_request)
    assert response1.status_code == status.HTTP_200_OK
    transaction_id_1 = response1.json()["transaction_id"]
    
    # Second request with same idempotency key
    response2 = client.post("/transaction", json=sample_transaction_request)
    assert response2.status_code == status.HTTP_200_OK
    transaction_id_2 = response2.json()["transaction_id"]
    
    # Should return same transaction
    assert transaction_id_1 == transaction_id_2


def test_transaction_validation(client):
    """Test transaction request validation"""
    # Invalid: negative amount
    invalid_request = {
        "user_id": "user123",
        "amount": -100.0,
        "currency": "USD",
        "idempotency_key": "test-key-456"
    }
    response = client.post("/transaction", json=invalid_request)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Invalid: missing required field
    invalid_request2 = {
        "user_id": "user123",
        "amount": 100.0
    }
    response2 = client.post("/transaction", json=invalid_request2)
    assert response2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_balance(client, sample_transaction_request):
    """Test get balance endpoint"""
    # First create a transaction
    client.post("/transaction", json=sample_transaction_request)
    
    # Get balance
    response = client.get(f"/balance/{sample_transaction_request['user_id']}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "user_id" in data
    assert "balance" in data
    assert "currency" in data


def test_get_transaction_history(client, sample_transaction_request):
    """Test transaction history endpoint"""
    # Create a transaction
    client.post("/transaction", json=sample_transaction_request)
    
    # Get history
    response = client.get(f"/history/{sample_transaction_request['user_id']}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "transactions" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["transactions"], list)

