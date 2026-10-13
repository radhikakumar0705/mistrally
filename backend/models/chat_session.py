from datetime import datetime
from extensions import db

DEFAULT_TITLE = "New Chat"


class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False, default=DEFAULT_TITLE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship(
        "ChatHistory",
        backref="session",
        cascade="all, delete-orphan",
        order_by="ChatHistory.timestamp",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
