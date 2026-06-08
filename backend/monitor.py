import asyncio
import logging
import sys

from app.config import get_settings
from app.logging import configure_logging
from app.services import mongodb as db

logger = logging.getLogger("monitor")


async def check_stuck_batches() -> int:
    settings = get_settings()
    stuck = await db.find_stuck_batches(settings.batch_stuck_minutes)
    for batch in stuck:
        logger.error(
            "stuck_batch batch_id=%s status=%s updated_at=%s threshold_minutes=%s",
            batch.id,
            batch.status,
            batch.updated_at.isoformat(),
            settings.batch_stuck_minutes,
        )
    return len(stuck)


def main() -> None:
    configure_logging()
    count = asyncio.run(check_stuck_batches())
    if count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
