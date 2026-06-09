import os

from redis import Redis
from rq import Worker

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    queue_names = [
        name.strip()
        for name in os.getenv("WORKER_QUEUES", "batch_generation,batch_upload").split(",")
        if name.strip()
    ]
    worker = Worker(queue_names, connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    main()
