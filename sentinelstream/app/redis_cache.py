"""Redis caching utilities"""
import json
import redis.asyncio as redis
from typing import Optional, Dict, Any
from app.config import settings

# Redis connection pool
redis_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis connection"""
    global redis_pool
    if redis_pool is None:
        redis_pool = await redis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            decode_responses=True,
            max_connections=50
        )
    return redis_pool


async def close_redis():
    """Close Redis connections"""
    global redis_pool
    if redis_pool:
        await redis_pool.close()
        redis_pool = None


async def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user profile from Redis cache"""
    redis_client = await get_redis()
    data = await redis_client.get(f"user_profile:{user_id}")
    if data:
        return json.loads(data)
    return None


async def set_user_profile(user_id: str, profile: Dict[str, Any], ttl: Optional[int] = None):
    """Set user profile in Redis cache"""
    redis_client = await get_redis()
    ttl = ttl or settings.REDIS_TTL
    await redis_client.setex(
        f"user_profile:{user_id}",
        ttl,
        json.dumps(profile)
    )


async def get_idempotency_response(idempotency_key: str) -> Optional[Dict[str, Any]]:
    """Get cached response for idempotency key"""
    redis_client = await get_redis()
    data = await redis_client.get(f"idempotency:{idempotency_key}")
    if data:
        return json.loads(data)
    return None


async def set_idempotency_response(idempotency_key: str, response: Dict[str, Any], ttl: int = 3600):
    """Cache response for idempotency key"""
    redis_client = await get_redis()
    await redis_client.setex(
        f"idempotency:{idempotency_key}",
        ttl,
        json.dumps(response)
    )


async def increment_rate_limit(key: str, limit: int, window: int = 60) -> tuple[bool, int]:
    """Increment rate limit counter and check if limit exceeded"""
    redis_client = await get_redis()
    pipe = redis_client.pipeline()
    
    # Increment counter
    count_key = f"rate_limit:{key}:{window}"
    current = await redis_client.incr(count_key)
    
    # Set expiry on first request
    if current == 1:
        await redis_client.expire(count_key, window)
    
    # Check if limit exceeded
    is_allowed = current <= limit
    return is_allowed, current

