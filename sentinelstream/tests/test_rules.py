"""Tests for rule engine"""
import pytest
from app.rules import RuleEngine


@pytest.mark.asyncio
async def test_rule_engine_evaluation(test_db):
    """Test rule engine evaluation"""
    from app.db import TestSessionLocal
    
    async with TestSessionLocal() as db:
        rule_engine = RuleEngine(db)
        
        # Test transaction data
        transaction = {
            "amount": 6000.0,
            "location": "Mumbai, India",
            "user_id": "user123"
        }
        
        # Evaluate (no rules yet, should return default scores)
        result = await rule_engine.evaluate_transaction(transaction)
        assert "rule_score" in result
        assert "triggered_rules" in result
        assert "flags" in result
        assert 0.0 <= result["rule_score"] <= 1.0


@pytest.mark.asyncio
async def test_rule_condition_evaluation():
    """Test rule condition evaluation"""
    from app.db import TestSessionLocal
    from app.rules import RuleEngine
    
    async with TestSessionLocal() as db:
        rule_engine = RuleEngine(db)
        
        transaction = {
            "amount": 6000.0,
            "location": "Mumbai, India"
        }
        
        # Test greater than condition
        condition = {
            "field": "amount",
            "operator": ">",
            "value": 5000
        }
        
        result = rule_engine.evaluate_condition(condition, transaction)
        assert result is True
        
        # Test less than condition
        condition2 = {
            "field": "amount",
            "operator": "<",
            "value": 5000
        }
        
        result2 = rule_engine.evaluate_condition(condition2, transaction)
        assert result2 is False

