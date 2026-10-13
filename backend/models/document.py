from datetime import datetime

from extensions import db

STATUSES = ("queued", "processing", "ready", "failed")


class Document(db.Model):
    """An uploaded file and its ingestion status. Its chunks and embeddings live in Chroma."""

    __tablename__ = "documents"

    id = db.Column(db.String(32), primary_key=True)  # uuid4 hex, also stored on every Chroma chunk
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="queued")
    progress = db.Column(db.Integer, nullable=False, default=0)  # percent of chunks embedded
    pages = db.Column(db.Integer, nullable=True)
    chunks = db.Column(db.Integer, nullable=False, default=0)
    error = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "progress": self.progress,
            "pages": self.pages,
            "chunks": self.chunks,
            "error": self.error,
            "uploaded_at": self.created_at.isoformat() if self.created_at else None,
        }
