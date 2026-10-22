"""Documents: uploads, processing status and deletion, independent of HTTP."""
import hashlib
import uuid

from flask import current_app

from models.document import Document
from observability import DOCUMENTS_INGESTED
from repositories import DocumentRepository, UserRepository
from services import chroma_service, tasks
from services.chunking import allowed_file, file_type
from services.errors import DependencyUnavailable, InvalidInput, NotFound, Unprocessable


class DocumentService:
    """
    Producer side of the ingestion pipeline: validate an upload, record it, and hand it to the task
    queue (the consumer is the RQ worker running services.ingestion). Dependencies are injectable.
    """

    def __init__(self, documents=None, vector_store=chroma_service, queue=tasks):
        self.documents = documents or DocumentRepository()
        self.vector_store = vector_store
        self.queue = queue

    def list(self, user_id: int) -> list[Document]:
        return self.documents.for_user(user_id)

    def get(self, user_id: int, doc_id: str) -> Document:
        document = self.documents.owned(doc_id, user_id)
        if document is None:
            raise NotFound("Document not found")
        return document

    def upload(self, user_id: int, filename: str | None, data: bytes) -> tuple[Document, bool]:
        """Record and queue an upload. Returns the document and whether it was queued (vs processed inline)."""
        if not filename:
            raise InvalidInput("No file provided")
        if not allowed_file(filename):
            raise InvalidInput("Only .pdf, .txt and .md files are supported")
        if not data.strip():
            DOCUMENTS_INGESTED.labels(status="unreadable").inc()
            raise Unprocessable("That file is empty")

        document = self.documents.add(Document(
            id=uuid.uuid4().hex,
            user_id=user_id,
            filename=filename[:255],
            file_type=file_type(filename),
            size_bytes=len(data),
        ))
        self.documents.commit()

        try:
            queued = self.queue.submit_ingestion(document.id, data)
        except Exception as e:
            current_app.logger.exception("Could not queue document", extra={"document_id": document.id})
            document.status, document.error = "failed", "The processing queue is unavailable"
            self.documents.commit()
            raise DependencyUnavailable(document.error, status=503, payload=document.to_dict()) from e

        self.documents.session.refresh(document)
        if not queued and document.status == "failed":
            raise Unprocessable(document.error, payload=document.to_dict())
        return document, queued

    def delete(self, user_id: int, doc_id: str) -> None:
        document = self.get(user_id, doc_id)
        try:
            if document.id.startswith("legacy"):
                self.vector_store.delete_chunks_by_source(user_id, document.filename)
            else:
                self.vector_store.delete_document_chunks(document.id)
        except Exception as e:
            current_app.logger.exception("Could not delete chunks", extra={"document_id": doc_id})
            raise DependencyUnavailable("The document store is unavailable", status=503) from e
        self.documents.delete(document)
        self.documents.commit()

    def study_text(self, user_id: int, doc_id: str) -> tuple[Document, str]:
        """A ready document and its full text, as material for quizzes and flashcards."""
        document = self.documents.owned(doc_id, user_id)
        if document is None or document.status != "ready":
            raise NotFound("Document not found or not ready")
        return document, self.vector_store.document_text(document.id)

    def backfill(self, users=None) -> int:
        """Create records for files uploaded before documents were tracked in the database."""
        users = users or UserRepository()
        created = 0
        for user in users.all():
            known = self.documents.ids_for_user(user.id)
            for doc in self.vector_store.legacy_documents(user.id):
                doc_id = doc["id"]
                if doc_id.startswith("legacy-"):
                    doc_id = "legacy" + hashlib.sha1(doc["filename"].encode()).hexdigest()[:26]
                if doc_id in known:
                    continue
                self.documents.add(Document(
                    id=doc_id, user_id=user.id, filename=doc["filename"][:255],
                    file_type=file_type(doc["filename"]) or "txt", status="ready", progress=100,
                    chunks=doc["chunks"],
                ))
                created += 1
        self.documents.commit()
        return created
