from models.chat_history import ChatHistory
from models.chat_session import ChatSession
from repositories.base import SqlAlchemyRepository


class ChatSessionRepository(SqlAlchemyRepository[ChatSession]):
    model = ChatSession

    def for_user(self, user_id: int) -> list[ChatSession]:
        """A user's conversations, most recently active first."""
        return (
            ChatSession.query.filter_by(user_id=user_id)
            .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
            .all()
        )

    def owned(self, session_id: int, user_id: int) -> ChatSession | None:
        """A conversation, only if it belongs to the user (others' ids behave as missing)."""
        return ChatSession.query.filter_by(id=session_id, user_id=user_id).first()


class MessageRepository(SqlAlchemyRepository[ChatHistory]):
    model = ChatHistory

    def for_session(self, session: ChatSession) -> list[ChatHistory]:
        return list(session.messages)

    def latest(self, session_id: int, limit: int) -> list[ChatHistory]:
        """The newest `limit` turns of a conversation, oldest first."""
        newest_first = (
            ChatHistory.query.filter_by(session_id=session_id)
            .order_by(ChatHistory.id.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(newest_first))
