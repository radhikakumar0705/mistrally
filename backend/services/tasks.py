"""Background jobs on Redis with RQ. Without TASK_QUEUE_URL, jobs run inline in the request."""
from functools import cache

from flask import current_app
from redis import Redis
from rq import Queue

from services import ingestion

QUEUE_NAME = "documents"


@cache
def _connection(url):
    return Redis.from_url(url)


def get_queue():
    url = current_app.config.get("TASK_QUEUE_URL")
    if not url:
        return None
    return Queue(QUEUE_NAME, connection=_connection(url), default_timeout=600)


def submit_ingestion(doc_id, data):
    """Queue a document for processing; returns True if it was queued, False if it ran inline."""
    queue = get_queue()
    if queue is None:
        ingestion.ingest(doc_id, data)
        return False
    queue.enqueue(
        ingestion.run_job,
        doc_id,
        data,
        job_id=f"ingest-{doc_id}",
        description=f"ingest document {doc_id}",  # keeps file contents out of the worker's logs
        result_ttl=3600,
        failure_ttl=86400,
    )
    return True
