"""Tests for ML model scorer"""
import pytest
from app.model_scorer import FraudModelScorer


def test_model_scorer_initialization():
    """Test model scorer initialization"""
    scorer = FraudModelScorer()
    assert scorer.model_path is not None
    assert scorer.feature_names is not None


def test_model_scorer_load():
    """Test model loading"""
    scorer = FraudModelScorer()
    scorer.load_model()
    assert scorer.model is not None


def test_model_scorer_extract_features():
    """Test feature extraction"""
    scorer = FraudModelScorer()
    
    transaction = {
        "amount": 100.0,
        "location": "New York, NY"
    }
    
    user_profile = {
        "average_transaction_amount": 50.0,
        "transaction_count": 10,
        "home_location": "New York, NY"
    }
    
    features = scorer.extract_features(transaction, user_profile)
    assert features.shape[0] == 1
    assert features.shape[1] == len(scorer.feature_names)


def test_model_scorer_score():
    """Test transaction scoring"""
    scorer = FraudModelScorer()
    scorer.load_model()
    
    transaction = {
        "amount": 100.0,
        "location": "New York, NY"
    }
    
    score = scorer.score_transaction(transaction)
    assert 0.0 <= score <= 1.0

