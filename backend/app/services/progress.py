import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.queue import redis_conn

settings = get_settings()

logger = logging.getLogger("progress")

PROGRESS_KEY_PREFIX = "batch:progress:"
PROGRESS_TTL_SECONDS = 7200


def report_progress(
    batch_id: str,
    *,
    phase: str,
    message: str,
    page_index: int = 0,
    page_total: int = 1,
    puja: str = "",
    city: str = "",
    slug: str = "",
    image_index: int | None = None,
    image_total: int = 3,
    content_preview: str = "",
) -> None:
    payload: dict[str, Any] = {
        "phase": phase,
        "message": message,
        "page_index": page_index,
        "page_total": page_total,
        "puja": puja,
        "city": city,
        "slug": slug,
        "image_index": image_index,
        "image_total": image_total,
        "content_preview": content_preview[:300],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if settings.use_mock_llm:
        return

    key = f"{PROGRESS_KEY_PREFIX}{batch_id}"
    redis_conn.setex(key, PROGRESS_TTL_SECONDS, json.dumps(payload))
    logger.info(
        "batch_progress batch_id=%s phase=%s message=%s page=%s/%s",
        batch_id,
        phase,
        message,
        page_index + 1,
        page_total,
    )


def get_progress(batch_id: str) -> dict[str, Any] | None:
    raw = redis_conn.get(f"{PROGRESS_KEY_PREFIX}{batch_id}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def clear_progress(batch_id: str) -> None:
    redis_conn.delete(f"{PROGRESS_KEY_PREFIX}{batch_id}")
