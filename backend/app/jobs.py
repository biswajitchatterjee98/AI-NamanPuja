import asyncio
import logging
from datetime import datetime, timezone

from app.agents.upload import upload_batch_pages
from app.graph.pipeline import BatchCancelled, run_pipeline
from app.schemas import BatchStatus
from app.services import mongodb as db

logger = logging.getLogger("jobs")


async def _build_feedback_context() -> str:
    feedback_items = await db.get_recent_feedback(limit=10)
    if not feedback_items:
        return ""
    lines = [f"- {item.comments}" for item in feedback_items]
    return "Previous reviewer feedback to avoid:\n" + "\n".join(lines)


async def _is_cancelled(batch_id: str) -> bool:
    batch = await db.get_batch(batch_id)
    return batch is None or batch.status == BatchStatus.CANCELLED


def run_batch_generation(batch_id: str) -> None:
    asyncio.run(_run_batch_generation(batch_id))


async def _run_batch_generation(batch_id: str) -> None:
    batch = await db.get_batch(batch_id)
    if not batch:
        logger.error("batch_not_found batch_id=%s", batch_id)
        return

    if batch.status == BatchStatus.CANCELLED:
        logger.info("batch_generation_skipped_cancelled batch_id=%s", batch_id)
        return

    started_at = datetime.now(timezone.utc)
    started = await db.transition_batch_status(
        batch_id,
        {BatchStatus.PENDING},
        BatchStatus.GENERATING,
        generation_metadata={"started_at": started_at.isoformat()},
    )
    if not started:
        if await _is_cancelled(batch_id):
            logger.info("batch_generation_skipped_cancelled batch_id=%s", batch_id)
        else:
            logger.info("batch_generation_skipped_status batch_id=%s status=%s", batch_id, batch.status)
        return

    feedback_context = await _build_feedback_context()
    page_inputs = [item.model_dump() for item in batch.page_inputs]

    try:
        result = run_pipeline(batch_id, page_inputs, feedback_context=feedback_context)
    except BatchCancelled:
        logger.info("batch_generation_aborted_cancelled batch_id=%s", batch_id)
        return
    except Exception as exc:
        if await _is_cancelled(batch_id):
            return
        await db.transition_batch_status(
            batch_id,
            {BatchStatus.GENERATING},
            BatchStatus.FAILED,
            generation_metadata={
                "error": str(exc),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.exception("batch_generation_failed batch_id=%s", batch_id)
        raise

    if await _is_cancelled(batch_id):
        logger.info("batch_generation_aborted_cancelled batch_id=%s", batch_id)
        return

    for page in result["pages"]:
        await db.upsert_page(page)

    completed = await db.transition_batch_status(
        batch_id,
        {BatchStatus.GENERATING},
        BatchStatus.UNDER_REVIEW,
        page_count=len(result["pages"]),
        generation_metadata={
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "qc_results": result["qc_results"],
            "pipeline_status": result["status"],
        },
    )
    if completed:
        logger.info("batch_generation_complete batch_id=%s", batch_id)
    else:
        logger.info("batch_generation_complete_skipped_cancelled batch_id=%s", batch_id)


def run_batch_upload(batch_id: str) -> None:
    asyncio.run(upload_batch_pages(batch_id))
