"""Simple sliding-window-ish rate limiter backed by Redis.

Falls back to allowing the request when Redis is down so the app never
hard-fails because of infra. The limit is per client key (IP or user id).
"""
from fastapi import HTTPException, Request, status

from app.config import settings
from app.core.redis_client import get_redis


def _client_key(request: Request) -> str:
    # Prefer the authenticated user if present, else the client IP.
    user = getattr(request.state, "user_id", None)
    if user:
        return f"rl:user:{user}"
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"rl:ip:{ip}"


async def enforce_rate_limit(request: Request) -> None:
    redis = await get_redis()
    if redis is None:
        return  # graceful no-op

    key = _client_key(request)
    try:
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, settings.rate_limit_window_seconds)
        if current > settings.rate_limit_requests:
            ttl = await redis.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {ttl}s.",
            )
    except HTTPException:
        raise
    except Exception:
        return  # if Redis hiccups mid-request, don't block the user
