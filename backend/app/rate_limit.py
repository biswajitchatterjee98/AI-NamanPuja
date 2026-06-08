import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.queue import redis_conn

logger = logging.getLogger("rate_limit")


def _client_identity(request: Request) -> str:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key[:12]}"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for and request.client:
        proxy_host = request.client.host
        if not settings.parsed_trusted_proxy_ips or proxy_host in settings.parsed_trusted_proxy_ips:
            return forwarded_for.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.rate_limit_enabled or "/health" in request.url.path:
            return await call_next(request)

        identity = _client_identity(request)
        window = int(time.time() // 60)
        bucket_key = f"rl:namanpuja:{identity}:{window}"
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
            logger.error("rate_limiter_error error=%s", exc)
            if settings.rate_limit_fail_closed:
                return JSONResponse(status_code=503, content={"detail": "Rate limiter unavailable"})
        return await call_next(request)
