import logging
from typing import Any

from bson import ObjectId
from pymongo import MongoClient

from app.config import get_settings
from app.schemas import PageDocument

logger = logging.getLogger("sync_persist")
settings = get_settings()

_client: MongoClient | None = None


def _database():
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri)
    return _client[settings.mongodb_database]


def upsert_page(page: PageDocument) -> None:
    if settings.use_mock_llm:
        return

    doc: dict[str, Any] = page.model_dump(exclude={"id"})
    doc["faq"] = [item.model_dump() for item in page.faq]
    doc["images"] = [item.model_dump() for item in page.images]
    doc["seo"] = page.seo.model_dump() if page.seo else None
    doc["qc"] = page.qc.model_dump() if page.qc else None

    result = _database().pages.update_one(
        {"batch_id": page.batch_id, "slug": page.slug},
        {"$set": doc},
        upsert=True,
    )
    logger.debug(
        "page_upserted_sync batch_id=%s slug=%s matched=%s",
        page.batch_id,
        page.slug,
        result.matched_count,
    )


def touch_batch_page_count(batch_id: str, page_count: int) -> None:
    if settings.use_mock_llm:
        return

    try:
        _database().batches.update_one(
            {"_id": ObjectId(batch_id)},
            {"$set": {"page_count": page_count}},
        )
    except Exception as exc:
        logger.warning("touch_batch_page_count_failed batch_id=%s error=%s", batch_id, exc)
