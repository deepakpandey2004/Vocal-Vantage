"""Redis client with graceful degradation.

Redis powers rate limiting and report caching. If Redis is unavailable (or
disabled via env), the app keeps working — features that depend on it simply
no-op instead of crashing. This makes local dev and free-tier deploys easy.
"""
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger("vocal_vantage.redis")

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if not settings.redis_enabled:
        return None
    if _redis is None:
        try:
            _redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _redis.ping()
            logger.info("Connected to Redis.")
        except Exception as exc:  # pragma: no cover - depends on infra
            logger.warning("Redis unavailable (%s); continuing without it.", exc)
            _redis = None
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
