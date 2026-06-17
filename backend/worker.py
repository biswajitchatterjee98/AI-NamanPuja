import os

from rq import Worker

from app.queue import create_redis_client


def main() -> None:
    redis_conn = create_redis_client()
    queue_names = [
        name.strip()
        for name in os.getenv("WORKER_QUEUES", "batch_generation,batch_upload").split(",")
        if name.strip()
    ]
    worker = Worker(queue_names, connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    main()
