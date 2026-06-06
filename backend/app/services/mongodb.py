from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.config import get_settings
from app.schemas import (
    BatchDocument,
    BatchStatus,
    FaqItem,
    FeedbackDocument,
    ImageAsset,
    PageDocument,
    PageInput,
    QcResult,
    SeoMetadata,
)

settings = get_settings()

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_database]


async def ensure_indexes() -> None:
    db = get_database()
    await db.batches.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    await db.pages.create_index("slug", unique=True)
    await db.pages.create_index("batch_id")
    await db.feedback.create_index([("batch_id", ASCENDING), ("timestamp", DESCENDING)])


def _oid(value: str) -> ObjectId:
    return ObjectId(value)


def _serialize_page(doc: dict[str, Any]) -> PageDocument:
    faq = [FaqItem(**item) for item in doc.get("faq", [])]
    images = [ImageAsset(**item) for item in doc.get("images", [])]
    seo = SeoMetadata(**doc["seo"]) if doc.get("seo") else None
    qc = QcResult(**doc["qc"]) if doc.get("qc") else None
    return PageDocument(
        id=str(doc["_id"]),
        batch_id=doc["batch_id"],
        puja=doc["puja"],
        city=doc["city"],
        state=doc["state"],
        country=doc["country"],
        slug=doc.get("slug", ""),
        content=doc.get("content", ""),
        faq=faq,
        seo=seo,
        images=images,
        qc=qc,
        upload_status=doc.get("upload_status"),
        generated_at=doc.get("generated_at"),
    )


def _serialize_batch(doc: dict[str, Any]) -> BatchDocument:
    page_inputs = [PageInput(**item) for item in doc.get("page_inputs", [])]
    return BatchDocument(
        id=str(doc["_id"]),
        status=BatchStatus(doc["status"]),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        page_inputs=page_inputs,
        parent_batch_id=doc.get("parent_batch_id"),
        prompt_version=doc.get("prompt_version", "v1"),
        generation_metadata=doc.get("generation_metadata", {}),
    )


async def ping_database() -> bool:
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False


async def create_batch(page_inputs: list[PageInput], parent_batch_id: str | None = None) -> BatchDocument:
    now = datetime.now(timezone.utc)
    doc = {
        "status": BatchStatus.PENDING.value,
        "created_at": now,
        "updated_at": now,
        "page_inputs": [item.model_dump() for item in page_inputs],
        "parent_batch_id": parent_batch_id,
        "prompt_version": "v1",
        "generation_metadata": {},
    }
    result = await get_database().batches.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_batch(doc)


async def update_batch_status(batch_id: str, status: BatchStatus, **extra: Any) -> None:
    update: dict[str, Any] = {"status": status.value, "updated_at": datetime.now(timezone.utc)}
    update.update(extra)
    await get_database().batches.update_one({"_id": _oid(batch_id)}, {"$set": update})


async def get_batch(batch_id: str) -> BatchDocument | None:
    doc = await get_database().batches.find_one({"_id": _oid(batch_id)})
    return _serialize_batch(doc) if doc else None


async def list_batches(limit: int = 100) -> list[BatchDocument]:
    cursor = get_database().batches.find().sort("created_at", DESCENDING).limit(limit)
    return [_serialize_batch(doc) async for doc in cursor]


async def get_pages_for_batch(batch_id: str) -> list[PageDocument]:
    cursor = get_database().pages.find({"batch_id": batch_id})
    return [_serialize_page(doc) async for doc in cursor]


async def upsert_page(page: PageDocument) -> PageDocument:
    doc = page.model_dump(exclude={"id"})
    doc["faq"] = [item.model_dump() for item in page.faq]
    doc["images"] = [item.model_dump() for item in page.images]
    doc["seo"] = page.seo.model_dump() if page.seo else None
    doc["qc"] = page.qc.model_dump() if page.qc else None

    if page.id:
        await get_database().pages.update_one({"_id": _oid(page.id)}, {"$set": doc})
        return page

    result = await get_database().pages.insert_one(doc)
    page.id = str(result.inserted_id)
    return page


async def save_feedback(batch_id: str, decision: str, comments: str) -> FeedbackDocument:
    doc = {
        "batch_id": batch_id,
        "decision": decision,
        "comments": comments,
        "timestamp": datetime.now(timezone.utc),
    }
    result = await get_database().feedback.insert_one(doc)
    return FeedbackDocument(id=str(result.inserted_id), **doc)


async def get_recent_feedback(limit: int = 20) -> list[FeedbackDocument]:
    cursor = get_database().feedback.find().sort("timestamp", DESCENDING).limit(limit)
    return [
        FeedbackDocument(
            id=str(doc["_id"]),
            batch_id=doc["batch_id"],
            decision=doc["decision"],
            comments=doc["comments"],
            timestamp=doc["timestamp"],
        )
        async for doc in cursor
    ]
