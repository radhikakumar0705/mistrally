from models.document import Document
from repositories.base import SqlAlchemyRepository


class DocumentRepository(SqlAlchemyRepository[Document]):
    model = Document

    def for_user(self, user_id: int) -> list[Document]:
        """A user's documents, newest first."""
        return Document.query.filter_by(user_id=user_id).order_by(Document.created_at.desc()).all()

    def owned(self, doc_id: str, user_id: int) -> Document | None:
        return Document.query.filter_by(id=doc_id, user_id=user_id).first()

    def has_ready(self, user_id: int) -> bool:
        """Whether the user has any document that can be searched (an indexed primary-key lookup)."""
        return Document.query.filter_by(user_id=user_id, status="ready").first() is not None

    def ids_for_user(self, user_id: int) -> set[str]:
        return {doc_id for (doc_id,) in Document.query.with_entities(Document.id).filter_by(user_id=user_id)}
