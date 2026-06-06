import logging

from redis import Redis
from rq import Queue

from app.config import get_settings

logger = logging.getLogger("queue")
settings = get_settings()

redis_conn = Redis.from_url(settings.redis_url)
generation_queue = Queue(settings.worker_queue, connection=redis_conn)
upload_queue = Queue("batch_upload", connection=redis_conn)


def enqueue_generation(batch_id: str) -> str:
    job = generation_queue.enqueue("app.jobs.run_batch_generation", batch_id, job_timeout=1800)
    logger.info("enqueued_generation batch_id=%s job_id=%s", batch_id, job.id)
    return job.id


def enqueue_upload(batch_id: str) -> str:
    job = upload_queue.enqueue("app.jobs.run_batch_upload", batch_id, job_timeout=600)
    logger.info("enqueued_upload batch_id=%s job_id=%s", batch_id, job.id)
    return job.id


def ping_redis() -> bool:
    try:
        redis_conn.ping()
        return True
    except Exception:
        return False
