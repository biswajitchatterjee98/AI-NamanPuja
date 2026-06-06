from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_auth
from app.queue import enqueue_generation, enqueue_upload
from app.schemas import (
    BatchCreateRequest,
    BatchDetailResponse,
    BatchRejectRequest,
    BatchStatus,
    BatchSummary,
)
from app.services import mongodb as db

batch_router = APIRouter(prefix="/batch", tags=["batches"])
batches_router = APIRouter(prefix="/batches", tags=["batches"])


@batch_router.post("/create", status_code=status.HTTP_202_ACCEPTED)
async def create_batch(
    payload: BatchCreateRequest,
    _: None = Depends(require_auth),
) -> dict:
    batch = await db.create_batch(payload.pages, parent_batch_id=payload.parent_batch_id)
    job_id = enqueue_generation(batch.id)
    return {"batch_id": batch.id, "status": batch.status, "job_id": job_id}


@batch_router.get("/{batch_id}", response_model=BatchDetailResponse)
async def get_batch(batch_id: str, _: None = Depends(require_auth)) -> BatchDetailResponse:
    batch = await db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    pages = await db.get_pages_for_batch(batch_id)
    return BatchDetailResponse(batch=batch, pages=pages)


@batches_router.get("")
async def list_batches(_: None = Depends(require_auth)) -> list[BatchSummary]:
    batches = await db.list_batches()
    summaries: list[BatchSummary] = []
    for batch in batches:
        pages = await db.get_pages_for_batch(batch.id)
        summaries.append(
            BatchSummary(
                id=batch.id,
                status=batch.status,
                created_at=batch.created_at,
                updated_at=batch.updated_at,
                page_count=len(pages) or len(batch.page_inputs),
                parent_batch_id=batch.parent_batch_id,
            )
        )
    return summaries


@batch_router.post("/{batch_id}/approve")
async def approve_batch(batch_id: str, _: None = Depends(require_auth)) -> dict:
    batch = await db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status != BatchStatus.UNDER_REVIEW:
        raise HTTPException(status_code=400, detail=f"Batch must be UNDER_REVIEW, got {batch.status}")

    await db.update_batch_status(batch_id, BatchStatus.APPROVED)
    job_id = enqueue_upload(batch_id)
    return {"batch_id": batch_id, "status": BatchStatus.APPROVED, "upload_job_id": job_id}


@batch_router.post("/{batch_id}/reject")
async def reject_batch(
    batch_id: str,
    payload: BatchRejectRequest,
    _: None = Depends(require_auth),
) -> dict:
    batch = await db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status != BatchStatus.UNDER_REVIEW:
        raise HTTPException(status_code=400, detail=f"Batch must be UNDER_REVIEW, got {batch.status}")

    await db.save_feedback(batch_id, decision="rejected", comments=payload.comments)
    await db.update_batch_status(batch_id, BatchStatus.REJECTED)
    return {"batch_id": batch_id, "status": BatchStatus.REJECTED}


@batch_router.post("/{batch_id}/upload")
async def upload_batch(batch_id: str, _: None = Depends(require_auth)) -> dict:
    batch = await db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status not in {BatchStatus.APPROVED, BatchStatus.UNDER_REVIEW}:
        raise HTTPException(status_code=400, detail=f"Cannot upload batch in status {batch.status}")

    if batch.status == BatchStatus.UNDER_REVIEW:
        await db.update_batch_status(batch_id, BatchStatus.APPROVED)

    job_id = enqueue_upload(batch_id)
    return {"batch_id": batch_id, "upload_job_id": job_id}


@batch_router.post("/{batch_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_batch(batch_id: str, _: None = Depends(require_auth)) -> dict:
    batch = await db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status != BatchStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Only rejected batches can be regenerated")

    new_batch = await db.create_batch(batch.page_inputs, parent_batch_id=batch_id)
    job_id = enqueue_generation(new_batch.id)
    return {"batch_id": new_batch.id, "parent_batch_id": batch_id, "job_id": job_id}
