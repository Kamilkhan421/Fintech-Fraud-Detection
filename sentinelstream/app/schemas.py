"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime


class TransactionRequest(BaseModel):
    """Transaction request schema"""
    user_id: str = Field(..., description="User identifier")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="USD", max_length=3, description="Currency code")
    location: Optional[str] = Field(None, description="Transaction location")
    merchant_id: Optional[str] = Field(None, description="Merchant identifier")
    card_number_hash: Optional[str] = Field(None, description="Hash of card number")
    transaction_type: str = Field(default="purchase", description="Type of transaction")
    idempotency_key: str = Field(..., description="Unique idempotency key")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v


class TransactionResponse(BaseModel):
    """Transaction response schema"""
    transaction_id: str
    status: str  # "approved" or "declined"
    is_fraud: bool
    risk_score: float = Field(..., ge=0.0, le=1.0)
    rule_score: float = Field(..., ge=0.0, le=1.0)
    ml_score: float = Field(..., ge=0.0, le=1.0)
    message: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserBalanceResponse(BaseModel):
    """User balance response"""
    user_id: str
    balance: float
    currency: str


class TransactionHistoryResponse(BaseModel):
    """Transaction history response"""
    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class RuleCreate(BaseModel):
    """Fraud rule creation schema"""
    rule_name: str
    rule_description: Optional[str] = None
    rule_condition: Dict[str, Any]
    rule_actions: Dict[str, Any]
    priority: int = Field(default=0, ge=0)
    is_active: bool = True


class RuleResponse(BaseModel):
    """Fraud rule response"""
    id: int
    rule_name: str
    rule_description: Optional[str]
    rule_condition: Dict[str, Any]
    rule_actions: Dict[str, Any]
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    database: str
    redis: str
    timestamp: datetime

