"""Document ingestion: extract text, chunk it, embed the chunks in batches, and track progress."""
from functools import cache

from flask import current_app, has_app_context

from observability import DOCUMENTS_INGESTED
from repositories import DocumentRepository
from services import chroma_service
from services.chunking import ExtractionError, chunk_structured, extract_pages, file_type

BATCH_SIZE = 32


def ingest(doc_id, data, documents=None):
    """Consumer side: process an uploaded file in the RQ worker (or inline when no queue is configured)."""
    documents = documents or DocumentRepository()
    document = documents.get(doc_id)
    if document is None:
        return
    document.status, document.progress, document.error = "processing", 0, None
    documents.commit()

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
            documents.commit()

        document.status, document.chunks = "ready", len(chunks)
        documents.commit()
        DOCUMENTS_INGESTED.labels(status="ok").inc()
    except Exception as e:
        documents.rollback()
        known = isinstance(e, ExtractionError)
        if not known:
            current_app.logger.exception("Ingestion failed", extra={"document_id": doc_id})
        try:
            chroma_service.delete_document_chunks(doc_id)  # don't leave a half-indexed document behind
        except Exception:
            current_app.logger.exception("Could not clean up chunks", extra={"document_id": doc_id})
        document = documents.get(doc_id)
        document.status = "failed"
        document.error = str(e)[:500] if known else "Could not process this file"
        documents.commit()
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
