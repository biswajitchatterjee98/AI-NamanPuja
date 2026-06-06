import asyncio
import logging

from app.schemas import BatchStatus, PageDocument
from app.services.cms import cms_service
from app.services import mongodb as db

logger = logging.getLogger("upload_agent")


async def upload_batch_pages(batch_id: str) -> dict[str, str]:
    pages = await db.get_pages_for_batch(batch_id)
    results: dict[str, str] = {}

    for page in pages:
        try:
            upload_result = await cms_service.upload_page(page)
            status = upload_result.get("status", "uploaded")
            page.upload_status = status
            await db.upsert_page(page)
            results[page.slug] = status
            logger.info("uploaded_page batch_id=%s slug=%s status=%s", batch_id, page.slug, status)
        except Exception as exc:
            page.upload_status = "failed"
            await db.upsert_page(page)
            results[page.slug] = "failed"
            logger.error("upload_failed batch_id=%s slug=%s error=%s", batch_id, page.slug, exc)

    await db.update_batch_status(batch_id, BatchStatus.UPLOADED)
    return results


def upload_batch_pages_sync(batch_id: str) -> dict[str, str]:
    return asyncio.run(upload_batch_pages(batch_id))
