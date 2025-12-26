"""Idempotency key middleware and utilities"""
import hashlib
import json
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.models import IdempotencyKey
from app.redis_cache import get_idempotency_response, set_idempotency_response


def generate_request_hash(request_body: Dict[str, Any]) -> str:
    """Generate hash of request body for idempotency checking"""
    # Sort keys to ensure consistent hashing
    sorted_body = json.dumps(request_body, sort_keys=True)
    return hashlib.sha256(sorted_body.encode()).hexdigest()


async def check_idempotency_key(
    db: AsyncSession,
    idempotency_key: str,
    request_body: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Check if idempotency key exists and return cached response if valid.
    Returns None if key doesn't exist or is invalid.
    """
    # First check Redis cache
    cached_response = await get_idempotency_response(idempotency_key)
    if cached_response:
        return cached_response
    
    # Check database
    request_hash = generate_request_hash(request_body)
    
    stmt = select(IdempotencyKey).where(
        IdempotencyKey.idempotency_key == idempotency_key
    )
    result = await db.execute(stmt)
    idempotency_record = result.scalar_one_or_none()
    
    if idempotency_record:
        # Check if request hash matches (same request)
        if idempotency_record.request_hash == request_hash:
            # Check if expired
            if idempotency_record.expires_at > datetime.utcnow():
                # Cache in Redis and return
                response_data = idempotency_record.response_data or {}
                await set_idempotency_response(idempotency_key, response_data)
                return response_data
            else:
                # Key expired, delete it
                await db.delete(idempotency_record)
                await db.commit()
        else:
            # Same key but different request - conflict
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key already used with different request parameters"
            )
    
    return None


async def store_idempotency_key(
    db: AsyncSession,
    idempotency_key: str,
    request_body: Dict[str, Any],
    response_data: Dict[str, Any],
    ttl_hours: int = 24
) -> None:
    """Store idempotency key and response in database and cache"""
    request_hash = generate_request_hash(request_body)
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
    
    idempotency_record = IdempotencyKey(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        response_data=response_data,
        expires_at=expires_at
    )
    
    db.add(idempotency_record)
    await db.commit()
    
    # Also cache in Redis
    await set_idempotency_response(idempotency_key, response_data, ttl=ttl_hours * 3600)

