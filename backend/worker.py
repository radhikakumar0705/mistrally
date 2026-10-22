"""
Background worker: processes uploaded documents from the Redis queue.

    python worker.py            (needs TASK_QUEUE_URL, e.g. redis://localhost:6379/1)

SimpleWorker runs jobs in this process instead of forking per job, so the embedding and
re-ranking models stay loaded between documents.
"""
import logging

from redis import Redis
from rq import SimpleWorker

from services.ingestion import _worker_app
from services.tasks import QUEUE_NAME

if __name__ == "__main__":
    app = _worker_app()  # configures logging, metrics and tracing like the API
    url = app.config.get("TASK_QUEUE_URL")
    if not url:
        raise SystemExit("TASK_QUEUE_URL is not set")
    logging.getLogger("mistrally.worker").info("Worker listening", extra={"queue": QUEUE_NAME})
    SimpleWorker([QUEUE_NAME], connection=Redis.from_url(url)).work()
