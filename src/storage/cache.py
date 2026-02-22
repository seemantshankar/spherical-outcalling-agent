import os
import json
import redis
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    logger.warning(f"Could not connect to Redis at {REDIS_URL}: {e}")
    redis_client = None

def get_spec_from_cache(derived_variant_id: str, feature_id: str):
    """Retrieves a cached spec fact for O(1) latency."""
    if not redis_client:
        return None
        
    key = f"spec:{derived_variant_id}:{feature_id}"
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Redis get error for {key}: {e}")
    return None

def set_spec_in_cache(derived_variant_id: str, feature_id: str, payload: dict, ttl_seconds: int = 86400):
    """Caches a spec fact with a default 24h TTL."""
    if not redis_client:
        return
        
    key = f"spec:{derived_variant_id}:{feature_id}"
    try:
        redis_client.setex(key, ttl_seconds, json.dumps(payload))
    except Exception as e:
        logger.error(f"Redis set error for {key}: {e}")
