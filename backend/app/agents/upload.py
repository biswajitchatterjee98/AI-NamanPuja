import logging

from app.schemas import BatchStatus
from app.services.cms import cms_service
from app.services import mongodb as db

logger = logging.getLogger("upload_agent")


async def upload_batch_pages(batch_id: str) -> dict[str, str]:
    pages = await db.get_pages_for_batch(batch_id)
    if not pages:
        raise ValueError(f"No pages found for batch {batch_id}")

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

    failed = [slug for slug, status in results.items() if status == "failed"]
    succeeded = [slug for slug, status in results.items() if status != "failed"]

    if failed and succeeded:
        final_status = BatchStatus.UPLOAD_PARTIAL
    elif failed:
        final_status = BatchStatus.APPROVED
    else:
        final_status = BatchStatus.UPLOADED

    await db.update_batch_status(
        batch_id,
        final_status,
        generation_metadata={
            "upload_results": results,
            "upload_failed_slugs": failed,
            "upload_succeeded_slugs": succeeded,
        },
    )
    return results
