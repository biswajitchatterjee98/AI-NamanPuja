from redis import Redis
from rq import Connection, Worker

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    queues = [settings.worker_queue, "batch_upload"]
    with Connection(redis_conn):
        worker = Worker(queues)
        worker.work()


if __name__ == "__main__":
    main()
