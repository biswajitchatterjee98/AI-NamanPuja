from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import require_auth
from app.queue import cancel_generation_for_batch, enqueue_generation, enqueue_upload
from app.utils.batch_names import format_batch_name
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
    await db.update_batch_status(
        batch.id,
        BatchStatus.PENDING,
        generation_metadata={"generation_job_id": job_id},
    )
    return {"batch_id": batch.id, "status": batch.status, "job_id": job_id}


@batch_router.get("/{batch_id}", response_model=BatchDetailResponse)
async def get_batch(batch_id: str, _: None = Depends(require_auth)) -> BatchDetailResponse:
    batch = await db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    pages = await db.get_pages_for_batch(batch_id)
    return BatchDetailResponse(batch=batch, pages=pages)


@batches_router.get("")
async def list_batches(
    _: None = Depends(require_auth),
    limit: int = Query(default=100, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
) -> list[BatchSummary]:
    batches = await db.list_batches(limit=limit, skip=skip)
    return [
        BatchSummary(
            id=batch.id,
            name=format_batch_name(batch.page_inputs),
            status=batch.status,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
            page_count=batch.page_count,
            parent_batch_id=batch.parent_batch_id,
        )
        for batch in batches
    ]


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
    if batch.status not in {BatchStatus.APPROVED, BatchStatus.UPLOAD_PARTIAL}:
        raise HTTPException(
            status_code=400,
            detail=f"Upload requires APPROVED or UPLOAD_PARTIAL status, got {batch.status}",
        )

    job_id = enqueue_upload(batch_id)
    return {"batch_id": batch_id, "upload_job_id": job_id}


@batch_router.post("/{batch_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_batch(batch_id: str, _: None = Depends(require_auth)) -> dict:
    batch = await db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status not in {BatchStatus.PENDING, BatchStatus.GENERATING, BatchStatus.FAILED}:
        raise HTTPException(status_code=400, detail="Only PENDING, GENERATING, or FAILED batches can be retried")

    job_id = enqueue_generation(batch_id)
    await db.update_batch_status(
        batch_id,
        BatchStatus.PENDING,
        generation_metadata={"generation_job_id": job_id},
    )
    return {"batch_id": batch_id, "status": BatchStatus.PENDING, "job_id": job_id}


@batch_router.post("/{batch_id}/cancel")
async def cancel_batch(batch_id: str, _: None = Depends(require_auth)) -> dict:
    batch = await db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status not in {BatchStatus.PENDING, BatchStatus.GENERATING}:
        raise HTTPException(status_code=400, detail="Only PENDING or GENERATING batches can be stopped")

    job_id = batch.generation_metadata.get("generation_job_id")
    cancel_generation_for_batch(batch_id, job_id)

    cancelled = await db.transition_batch_status(
        batch_id,
        {BatchStatus.PENDING, BatchStatus.GENERATING},
        BatchStatus.CANCELLED,
        generation_metadata={"cancelled_at": datetime.now(timezone.utc).isoformat()},
    )
    if not cancelled:
        batch = await db.get_batch(batch_id)
        if batch and batch.status == BatchStatus.CANCELLED:
            return {"batch_id": batch_id, "status": BatchStatus.CANCELLED}
        raise HTTPException(status_code=409, detail="Batch could not be stopped")

    return {"batch_id": batch_id, "status": BatchStatus.CANCELLED}


@batch_router.delete("/{batch_id}")
async def delete_batch(batch_id: str, _: None = Depends(require_auth)) -> dict:
    batch = await db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status in {BatchStatus.PENDING, BatchStatus.GENERATING}:
        raise HTTPException(status_code=400, detail="Stop the batch before deleting")

    deleted = await db.delete_batch(batch_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"batch_id": batch_id, "deleted": True}


@batch_router.post("/{batch_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_batch(batch_id: str, _: None = Depends(require_auth)) -> dict:
    batch = await db.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status not in {BatchStatus.REJECTED, BatchStatus.FAILED}:
        raise HTTPException(status_code=400, detail="Only REJECTED or FAILED batches can be regenerated")

    new_batch = await db.create_batch(batch.page_inputs, parent_batch_id=batch_id)
    job_id = enqueue_generation(new_batch.id)
    await db.update_batch_status(
        new_batch.id,
        BatchStatus.PENDING,
        generation_metadata={"generation_job_id": job_id},
    )
    return {"batch_id": new_batch.id, "parent_batch_id": batch_id, "job_id": job_id}
