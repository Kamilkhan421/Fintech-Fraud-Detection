"""SQLAlchemy database models"""
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user")
    user_profile = relationship("UserProfile", back_populates="user", uselist=False)


class Transaction(Base):
    """Transaction model - immutable ledger"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(String(100), ForeignKey("users.user_id"), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    location = Column(String(255))
    merchant_id = Column(String(100), index=True)
    card_number_hash = Column(String(64))  # SHA-256 hash of last 4 digits
    transaction_type = Column(String(50), default="purchase")
    
    # Fraud detection results
    rule_score = Column(Float, default=0.0)
    ml_score = Column(Float, default=0.0)
    final_risk_score = Column(Float, default=0.0)
    is_fraud = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)
    
    # Idempotency
    idempotency_key = Column(String(100), unique=True, index=True)
    
    # Additional metadata (renamed from 'metadata' as it's reserved in SQLAlchemy)
    transaction_metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    webhook_logs = relationship("WebhookLog", back_populates="transaction")


class UserProfile(Base):
    """User profile with risk indicators (cached in Redis)"""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), ForeignKey("users.user_id"), unique=True, index=True, nullable=False)
    
    # Risk indicators
    risk_score = Column(Float, default=0.1)
    home_location = Column(String(255))
    average_transaction_amount = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)
    
    # Behavioral patterns
    preferred_merchants = Column(JSON)
    transaction_hours = Column(JSON)  # Peak transaction times
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_profile")


class FraudRule(Base):
    """Dynamic fraud detection rules"""
    __tablename__ = "fraud_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(100), unique=True, nullable=False)
    rule_description = Column(Text)
    
    # Rule configuration (stored as JSON for flexibility)
    rule_condition = Column(JSON, nullable=False)  # e.g., {"field": "amount", "operator": ">", "value": 5000}
    rule_actions = Column(JSON)  # e.g., {"risk_score": 0.8, "flag": true}
    
    # Rule metadata
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority rules evaluated first
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class IdempotencyKey(Base):
    """Idempotency key tracking"""
    __tablename__ = "idempotency_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)
    request_hash = Column(String(64))  # Hash of request payload
    response_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), index=True)


class WebhookLog(Base):
    """Webhook delivery logs"""
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    webhook_url = Column(String(500), nullable=False)
    payload = Column(JSON, nullable=False)
    status_code = Column(Integer)
    response_body = Column(Text)
    attempt_number = Column(Integer, default=1)
    is_success = Column(Boolean, default=False)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True))
    
    # Relationships
    transaction = relationship("Transaction", back_populates="webhook_logs")

