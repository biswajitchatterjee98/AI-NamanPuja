from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth import require_auth
from app.config import get_settings
from app.queue import ping_redis
from app.schemas import HealthResponse
from app.services.cms import cms_service
from app.services.llm import llm_service
from app.services.mongodb import ping_database
from app.services.storage import image_storage

settings = get_settings()
router = APIRouter(tags=["health"])


async def _dependency_report() -> tuple[str, dict]:
    mongo_ok = await ping_database()
    redis_ok = ping_redis()
    storage_ok = image_storage.ping()
    cms_ok = await cms_service.ping()

    dependencies = {
        "mongodb": "ok" if mongo_ok else "down",
        "redis": "ok" if redis_ok else "down",
        "storage": "ok" if storage_ok else "down",
        "cms": "ok" if cms_ok else "down",
    }

    critical = [dependencies["mongodb"], dependencies["redis"]]
    if settings.use_s3_storage:
        critical.append(dependencies["storage"])

    status = "ok" if all(value == "ok" for value in critical) else "degraded"
    return status, dependencies


@router.get("/health", response_model=HealthResponse)
async def health_live() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@router.get("/health/ready")
async def health_ready() -> JSONResponse:
    status, dependencies = await _dependency_report()
    code = 200 if status == "ok" else 503
    return JSONResponse(status_code=code, content={"status": status, "dependencies": dependencies})


@router.get("/health/dependencies")
async def health_dependencies(_: None = Depends(require_auth)) -> dict:
    status, dependencies = await _dependency_report()
    return {"status": status, "dependencies": dependencies}


@router.get("/health/llm")
async def health_llm() -> dict:
    """Quick check that the configured LLM provider (Groq/OpenAI/mock) responds."""
    try:
        return llm_service.ping()
    except Exception as exc:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "provider": llm_service.provider,
                "model": llm_service.model,
                "detail": str(exc),
            },
        )
