import json
from datetime import datetime

from extensions import db


class ChatHistory(db.Model):
    __tablename__ = "chat_history"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    sources = db.Column(db.Text, nullable=True)  # JSON list of document names used for the answer
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ChatHistory {self.id} - User {self.user_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_message": self.user_message,
            "bot_response": self.bot_response,
            "sources": json.loads(self.sources) if self.sources else [],
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
