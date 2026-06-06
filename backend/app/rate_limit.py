import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.queue import redis_conn

settings = get_settings()
logger = logging.getLogger("rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled or "/health" in request.url.path:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        window = int(time.time() // 60)
        bucket_key = f"rl:namanpuja:{client_host}:{window}"
        try:
            count = redis_conn.incr(bucket_key)
            if count == 1:
                redis_conn.expire(bucket_key, 65)
            if count > settings.rate_limit_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "limit": settings.rate_limit_per_minute},
                )
        except Exception as exc:
            logger.warning("rate_limiter_fail_open error=%s", exc)
        return await call_next(request)
