"""Document ingestion: extract text, chunk it, embed the chunks in batches, and track progress."""
from functools import cache

from flask import current_app, has_app_context

from extensions import db
from models.document import Document
from observability import DOCUMENTS_INGESTED
from services import chroma_service
from services.chunking import ExtractionError, chunk_structured, extract_pages, file_type

BATCH_SIZE = 32


def ingest(doc_id, data):
    """Process an uploaded file. Runs in the RQ worker, or inline when no queue is configured."""
    document = db.session.get(Document, doc_id)
    if document is None:
        return
    document.status, document.progress, document.error = "processing", 0, None
    db.session.commit()

    try:
        pages = extract_pages(document.filename, data)
        if file_type(document.filename) == "pdf":
            document.pages = len(pages)
        chunks = chunk_structured(pages)
        if not chunks:
            raise ExtractionError("No text found in that file")

        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start:start + BATCH_SIZE]
            chroma_service.add_chunks(document, batch, start)
            document.progress = round(100 * (start + len(batch)) / len(chunks))
            db.session.commit()

        document.status, document.chunks = "ready", len(chunks)
        db.session.commit()
        DOCUMENTS_INGESTED.labels(status="ok").inc()
    except Exception as e:
        db.session.rollback()
        known = isinstance(e, ExtractionError)
        if not known:
            current_app.logger.exception("Ingestion failed", extra={"document_id": doc_id})
        try:
            chroma_service.delete_document_chunks(doc_id)  # don't leave a half-indexed document behind
        except Exception:
            current_app.logger.exception("Could not clean up chunks", extra={"document_id": doc_id})
        document = db.session.get(Document, doc_id)
        document.status = "failed"
        document.error = str(e)[:500] if known else "Could not process this file"
        db.session.commit()
        DOCUMENTS_INGESTED.labels(status="unreadable" if known else "failed").inc()


@cache
def _worker_app():
    from app import create_app

    return create_app()


def run_job(doc_id, data):
    """RQ entry point. Each job gets a fresh app context (and database session) in the worker."""
    if has_app_context():  # jobs run synchronously, e.g. in tests
        return ingest(doc_id, data)
    with _worker_app().app_context():
        return ingest(doc_id, data)
