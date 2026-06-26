import os
import json
import logging
from redis import Redis
from typing import Optional, Dict, Any

logger = logging.getLogger("uvicorn.error")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

_redis_client: Optional[Redis] = None

def get_redis_client() -> Optional[Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        client = Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
            decode_responses=True
        )
        # Test connection
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis is unavailable at {REDIS_HOST}:{REDIS_PORT} ({type(e).__name__}). Caching is disabled.")
        return None

def get_cached_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve ticket analysis from cache."""
    client = get_redis_client()
    if not client:
        return None
    try:
        cached_data = client.get(f"ticket:{ticket_id}")
        if cached_data:
            logger.info(f"Cache hit for ticket_id: {ticket_id}")
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Failed to read from Redis cache: {e}")
    return None

def set_cached_ticket(ticket_id: str, response_data: Dict[str, Any], ttl: int = 86400) -> None:
    """Store ticket analysis in cache with TTL (default 24 hours)."""
    client = get_redis_client()
    if not client:
        return
    try:
        client.setex(
            f"ticket:{ticket_id}",
            ttl,
            json.dumps(response_data)
        )
        logger.info(f"Cached ticket_id: {ticket_id}")
    except Exception as e:
        logger.warning(f"Failed to write to Redis cache: {e}")
