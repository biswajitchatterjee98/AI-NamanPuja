from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.logging import RequestLoggingMiddleware, configure_logging
from app.rate_limit import RateLimitMiddleware
from app.routes import router as api_router
from app.services.mongodb import ensure_indexes

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await ensure_indexes()
    yield


docs_url = None if settings.is_production else "/docs"
redoc_url = None if settings.is_production else "/redoc"

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
)

if settings.parsed_trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.parsed_trusted_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.include_router(api_router, prefix=settings.api_prefix)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    if settings.is_production:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
