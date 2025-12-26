"""Main FastAPI application for SentinelStream"""
import time
import uuid
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    # Fallback: create dummy limiter
    class Limiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    limiter = Limiter()
    def get_remote_address(request):
        return request.client.host if request.client else "127.0.0.1"

from app.config import settings
from app.db import get_db, init_db
from app.schemas import (
    TransactionRequest,
    TransactionResponse,
    UserBalanceResponse,
    TransactionHistoryResponse,
    UserLogin,
    Token,
    RuleCreate,
    RuleResponse,
    HealthResponse
)
from app.models import Transaction, User, UserProfile, FraudRule
from app.redis_cache import (
    get_user_profile,
    set_user_profile,
    increment_rate_limit
)
from app.idempotency import check_idempotency_key, store_idempotency_key
from app.rules import RuleEngine
from app.model_scorer import FraudModelScorer
from app.tasks import send_webhook, send_fraud_alert_email, update_user_profile
from app.auth import (
    create_access_token,
    get_current_active_user,
    verify_password,
    get_password_hash
)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-Time Fraud Detection Engine for Financial Transactions"
)

# Rate limiting
if SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Apply rate limiting decorator wrapper
    def rate_limit_decorator(limit_str: str):
        def decorator(func):
            return limiter.limit(limit_str)(func)
        return decorator
else:
    # Dummy limiter that does nothing
    def rate_limit_decorator(limit_str: str):
        def decorator(func):
            return func
        return decorator

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ML model scorer (singleton)
model_scorer = FraudModelScorer()


@app.on_event("startup")
async def startup_event():
    """Initialize database and load models on startup"""
    try:
        await init_db()
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
        print("Server will continue but database operations may fail")
    try:
        model_scorer.load_model()
    except Exception as e:
        print(f"Warning: Model loading failed: {e}")
        print("Server will continue but ML scoring may fail")


@app.get("/test")
async def test_endpoint():
    """Simple test endpoint without database"""
    return {"message": "Server is working!", "status": "ok"}


@app.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Check database
        await db.execute(select(1))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    # Check Redis
    try:
        from app.redis_cache import get_redis
        redis_client = await get_redis()
        await redis_client.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "disconnected"
    
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        database=db_status,
        redis=redis_status,
        timestamp=datetime.utcnow()
    )


@app.post("/transaction", response_model=TransactionResponse)
async def process_transaction(
    request: Request,
    txn: TransactionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process transaction with fraud detection.
    Must complete in under 200ms for production.
    Works even if database/Redis are unavailable (graceful degradation).
    """
    """
    Process transaction with fraud detection.
    Must complete in under 200ms for production.
    """
    start_time = time.time()
    
    # Check idempotency key
    request_body = txn.dict()
    try:
        cached_response = await check_idempotency_key(db, txn.idempotency_key, request_body)
        if cached_response:
            return TransactionResponse(**cached_response)
    except Exception as e:
        print(f"Warning: Idempotency check failed: {e}")
        # Continue processing
    
    # Get user profile from cache
    try:
        user_profile = await get_user_profile(txn.user_id)
    except Exception as e:
        print(f"Warning: Redis cache unavailable: {e}")
        user_profile = None
    
    if not user_profile:
        # Create default profile (in production, load from database)
        user_profile = {
            "risk_score": 0.1,
            "home_location": None,
            "average_transaction_amount": 0.0,
            "transaction_count": 0
        }
        try:
            await set_user_profile(txn.user_id, user_profile)
        except Exception as e:
            print(f"Warning: Failed to cache user profile: {e}")
    
    # Prepare transaction data for fraud detection
    transaction_data = {
        "amount": txn.amount,
        "location": txn.location,
        "user_id": txn.user_id,
        "merchant_id": txn.merchant_id,
        "transaction_type": txn.transaction_type
    }
    
    # 1. Evaluate rules
    try:
        rule_engine = RuleEngine(db)
        rule_result = await rule_engine.evaluate_transaction(transaction_data)
        rule_score = rule_result["rule_score"]
    except Exception as e:
        print(f"Warning: Rule engine evaluation failed: {e}")
        rule_score = 0.0
    
    # 2. Evaluate ML model
    ml_score = model_scorer.score_transaction(transaction_data, user_profile)
    
    # 3. Calculate final risk score (weighted combination)
    final_risk_score = (rule_score * 0.4 + ml_score * 0.6)
    
    # 4. Decision logic
    is_fraud = final_risk_score > 0.7  # Threshold for fraud
    is_approved = final_risk_score < 0.8  # Threshold for approval
    
    # Generate transaction ID
    transaction_id = str(uuid.uuid4())
    
    # Create transaction record (skip if database unavailable)
    try:
        db_transaction = Transaction(
            transaction_id=transaction_id,
            user_id=txn.user_id,
            amount=txn.amount,
            currency=txn.currency,
            location=txn.location,
            merchant_id=txn.merchant_id,
            card_number_hash=txn.card_number_hash,
            transaction_type=txn.transaction_type,
            rule_score=rule_score,
            ml_score=ml_score,
            final_risk_score=final_risk_score,
            is_fraud=is_fraud,
            is_approved=is_approved,
            idempotency_key=txn.idempotency_key,
            transaction_metadata=txn.metadata
        )
        
        db.add(db_transaction)
        await db.commit()
        await db.refresh(db_transaction)
        created_at = db_transaction.created_at
    except Exception as e:
        print(f"Warning: Database unavailable, transaction not saved: {e}")
        created_at = datetime.utcnow()
    
    # Prepare response
    response_data = TransactionResponse(
        transaction_id=transaction_id,
        status="approved" if is_approved else "declined",
        is_fraud=is_fraud,
        risk_score=final_risk_score,
        rule_score=rule_score,
        ml_score=ml_score,
        message="Transaction processed successfully" if is_approved else "Transaction declined due to high risk",
        created_at=created_at
    )
    
    # Store idempotency key (skip if database unavailable)
    try:
        await store_idempotency_key(
            db,
            txn.idempotency_key,
            request_body,
            response_data.dict()
        )
    except Exception as e:
        print(f"Warning: Failed to store idempotency key: {e}")
    
    # Asynchronous tasks (non-blocking)
    if is_fraud:
        # Send fraud alert email
        send_fraud_alert_email.delay(txn.user_id, transaction_id, final_risk_score)
    
    # Update user profile asynchronously
    update_user_profile.delay(txn.user_id, transaction_data)
    
    # Send webhook if configured (example)
    # webhook_url = "https://merchant.com/webhook"
    # send_webhook.delay(webhook_url, response_data.dict(), transaction_id)
    
    # Verify latency (should be < 200ms)
    elapsed_time = (time.time() - start_time) * 1000
    if elapsed_time > 200:
        # Log warning but don't fail
        print(f"WARNING: Transaction processing took {elapsed_time:.2f}ms")
    
    return response_data


@app.get("/balance/{user_id}", response_model=UserBalanceResponse)
async def get_balance(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user current balance"""
    # In production: calculate from transaction ledger
    # For now, return a placeholder
    stmt = select(func.sum(Transaction.amount)).where(
        Transaction.user_id == user_id,
        Transaction.is_approved == True
    )
    result = await db.execute(stmt)
    balance = result.scalar() or 0.0
    
    return UserBalanceResponse(
        user_id=user_id,
        balance=balance,
        currency="USD"
    )


@app.get("/history/{user_id}", response_model=TransactionHistoryResponse)
async def get_transaction_history(
    request: Request,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get user transaction history"""
    offset = (page - 1) * page_size
    
    # Get transactions
    stmt = select(Transaction).where(
        Transaction.user_id == user_id
    ).order_by(Transaction.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    transactions = result.scalars().all()
    
    # Get total count
    count_stmt = select(func.count(Transaction.id)).where(
        Transaction.user_id == user_id
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    transaction_responses = [
        TransactionResponse(
            transaction_id=tx.transaction_id,
            status="approved" if tx.is_approved else "declined",
            is_fraud=tx.is_fraud,
            risk_score=tx.final_risk_score,
            rule_score=tx.rule_score,
            ml_score=tx.ml_score,
            message=None,
            created_at=tx.created_at
        )
        for tx in transactions
    ]
    
    return TransactionHistoryResponse(
        transactions=transaction_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@app.post("/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_fraud_rule(
    rule: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new fraud detection rule"""
    # Check if rule name already exists
    stmt = select(FraudRule).where(FraudRule.rule_name == rule.rule_name)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rule with this name already exists"
        )
    
    db_rule = FraudRule(
        rule_name=rule.rule_name,
        rule_description=rule.rule_description,
        rule_condition=rule.rule_condition,
        rule_actions=rule.rule_actions,
        priority=rule.priority,
        is_active=rule.is_active
    )
    
    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)
    
    return RuleResponse(
        id=db_rule.id,
        rule_name=db_rule.rule_name,
        rule_description=db_rule.rule_description,
        rule_condition=db_rule.rule_condition,
        rule_actions=db_rule.rule_actions,
        is_active=db_rule.is_active,
        priority=db_rule.priority,
        created_at=db_rule.created_at,
        updated_at=db_rule.updated_at
    )


@app.get("/rules", response_model=list[RuleResponse])
async def list_fraud_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all fraud detection rules"""
    rule_engine = RuleEngine(db)
    rules = await rule_engine.get_all_rules()
    
    return [
        RuleResponse(
            id=rule.id,
            rule_name=rule.rule_name,
            rule_description=rule.rule_description,
            rule_condition=rule.rule_condition,
            rule_actions=rule.rule_actions,
            is_active=rule.is_active,
            priority=rule.priority,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
        for rule in rules
    ]


@app.post("/token", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and get JWT token"""
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return Token(access_token=access_token, token_type="bearer")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

