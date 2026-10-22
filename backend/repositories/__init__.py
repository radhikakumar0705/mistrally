"""
Repositories: the only layer that talks to the database.

Services ask repositories for domain objects ("this user's sessions", "the last five turns") instead of
building SQLAlchemy queries themselves, so the query details live in one place and services can be
unit-tested with in-memory fakes. Repositories add, find and delete; services decide when to commit.
"""
from repositories.chat import ChatSessionRepository, MessageRepository
from repositories.documents import DocumentRepository
from repositories.refresh_tokens import RefreshTokenRepository
from repositories.users import UserRepository

__all__ = [
    "ChatSessionRepository",
    "DocumentRepository",
    "MessageRepository",
    "RefreshTokenRepository",
    "UserRepository",
]
