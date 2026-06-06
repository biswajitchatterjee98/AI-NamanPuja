from fastapi import APIRouter

from app.routes.batches import batch_router, batches_router
from app.routes.health import router as health_router

router = APIRouter()
router.include_router(health_router)
router.include_router(batch_router)
router.include_router(batches_router)
