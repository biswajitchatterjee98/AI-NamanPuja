import asyncio
import logging

from app.agents.upload import upload_batch_pages
from app.graph.pipeline import run_pipeline
from app.schemas import BatchStatus
from app.services import mongodb as db

logger = logging.getLogger("jobs")


def _build_feedback_context() -> str:
    feedback_items = asyncio.run(db.get_recent_feedback(limit=10))
    if not feedback_items:
        return ""
    lines = [f"- {item.comments}" for item in feedback_items]
    return "Previous reviewer feedback to avoid:\n" + "\n".join(lines)


def run_batch_generation(batch_id: str) -> None:
    asyncio.run(_run_batch_generation(batch_id))


async def _run_batch_generation(batch_id: str) -> None:
    batch = await db.get_batch(batch_id)
    if not batch:
        logger.error("batch_not_found batch_id=%s", batch_id)
        return

    await db.update_batch_status(
        batch_id,
        BatchStatus.GENERATING,
        generation_metadata={"started_at": batch.updated_at.isoformat()},
    )

    feedback_context = _build_feedback_context()
    page_inputs = [item.model_dump() for item in batch.page_inputs]

    try:
        result = run_pipeline(batch_id, page_inputs, feedback_context=feedback_context)
        for page in result["pages"]:
            await db.upsert_page(page)

        await db.update_batch_status(
            batch_id,
            BatchStatus.UNDER_REVIEW,
            generation_metadata={
                "qc_results": result["qc_results"],
                "pipeline_status": result["status"],
            },
        )
        logger.info("batch_generation_complete batch_id=%s", batch_id)
    except Exception as exc:
        await db.update_batch_status(
            batch_id,
            BatchStatus.REJECTED,
            generation_metadata={"error": str(exc)},
        )
        logger.exception("batch_generation_failed batch_id=%s", batch_id)
        raise


def run_batch_upload(batch_id: str) -> None:
    asyncio.run(upload_batch_pages(batch_id))
