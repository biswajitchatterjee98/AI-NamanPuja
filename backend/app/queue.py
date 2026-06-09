import logging

from redis import Redis
from rq import Queue, Retry
from rq.job import Job

from app.config import get_settings

logger = logging.getLogger("queue")
settings = get_settings()

CANCEL_KEY_PREFIX = "batch:cancel:"
CANCEL_KEY_TTL_SECONDS = 86400

redis_conn = Redis.from_url(settings.redis_url)
generation_queue = Queue(settings.worker_queue, connection=redis_conn)
upload_queue = Queue("batch_upload", connection=redis_conn)


def enqueue_generation(batch_id: str) -> str:
    clear_batch_cancelled(batch_id)
    job = generation_queue.enqueue(
        "app.jobs.run_batch_generation",
        batch_id,
        job_timeout=1800,
        retry=Retry(max=settings.job_max_retries, interval=[30, 120, 300]),
    )
    logger.info("enqueued_generation batch_id=%s job_id=%s", batch_id, job.id)
    return job.id


def enqueue_upload(batch_id: str) -> str:
    job = upload_queue.enqueue(
        "app.jobs.run_batch_upload",
        batch_id,
        job_timeout=600,
        retry=Retry(max=settings.job_max_retries, interval=[15, 60, 180]),
    )
    logger.info("enqueued_upload batch_id=%s job_id=%s", batch_id, job.id)
    return job.id


def mark_batch_cancelled(batch_id: str) -> None:
    redis_conn.set(f"{CANCEL_KEY_PREFIX}{batch_id}", "1", ex=CANCEL_KEY_TTL_SECONDS)


def clear_batch_cancelled(batch_id: str) -> None:
    redis_conn.delete(f"{CANCEL_KEY_PREFIX}{batch_id}")


def is_batch_cancelled(batch_id: str) -> bool:
    return redis_conn.get(f"{CANCEL_KEY_PREFIX}{batch_id}") is not None


def cancel_job(job_id: str | None) -> bool:
    if not job_id:
        return False
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        job.cancel()
        logger.info("cancelled_job job_id=%s", job_id)
        return True
    except Exception as exc:
        logger.warning("cancel_job_failed job_id=%s error=%s", job_id, exc)
        return False


def cancel_queued_jobs_for_batch(batch_id: str) -> int:
    cancelled = 0
    for job_id in generation_queue.job_ids:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
            if job.args and job.args[0] == batch_id:
                job.cancel()
                cancelled += 1
        except Exception:
            continue
    if cancelled:
        logger.info("cancelled_queued_jobs batch_id=%s count=%s", batch_id, cancelled)
    return cancelled


def cancel_generation_for_batch(batch_id: str, job_id: str | None = None) -> None:
    mark_batch_cancelled(batch_id)
    cancel_job(job_id)
    cancel_queued_jobs_for_batch(batch_id)


def ping_redis() -> bool:
    try:
        redis_conn.ping()
        return True
    except Exception:
        return False
