import logging
import json
import hashlib
from typing import Any, Optional
from redis import asyncio as aioredis
from config.settings import settings

logger = logging.getLogger("cache")

# Global Redis instance
_redis = None

async def get_redis():
    """Get the Redis asynchronous client."""
    global _redis
    if _redis is None:
        try:
            logger.info(f"Connecting to Redis at {settings.REDIS_URL}...")
            _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=False, socket_connect_timeout=5)
            await _redis.ping()
            logger.info("✅ Redis connected successfully.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect to Redis: {e}. Falling back to non-cached behavior.")
            _redis = None
    return _redis

async def close_redis():
    """Close the Redis asynchronous client."""
    global _redis
    if _redis:
        await _redis.close()
        logger.info("🛑 Redis connection closed.")
        _redis = None

def make_cache_key(prefix: str, identifier: str) -> str:
    """Generate a stable cache key using MD5 hashing."""
    hashed = hashlib.md5(identifier.encode('utf-8')).hexdigest()
    return f"{prefix}:{hashed}"

async def get_cached(key: str) -> Optional[Any]:
    """Retrieve an item from Redis and deserialize it."""
    client = await get_redis()
    if not client:
        return None
    try:
        data = await client.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Error reading from cache: {e}")
    return None

async def set_cached(key: str, value: Any, ttl: int = None):
    """Serialize and store an item in Redis with an optional TTL."""
    client = await get_redis()
    if not client:
        return
    if ttl is None:
        ttl = settings.CACHE_TTL
    try:
        await client.set(key, json.dumps(value), ex=ttl)
    except Exception as e:
        logger.error(f"Error writing to cache: {e}")
