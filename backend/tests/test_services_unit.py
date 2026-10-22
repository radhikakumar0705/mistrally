"""
Service-layer unit tests. Repositories, the model and the retriever are replaced with in-memory fakes
passed through the constructors, so these exercise business rules with no database, vector store or LLM.
"""
import itertools

import pytest

from models.chat_session import ChatSession
from models.user import User
from services import llm
from services.auth_service import AuthService, GoogleSignInError
from services.chat_service import ChatService
from services.errors import Conflict, InvalidInput, NotFound, Unauthorized

_ids = itertools.count(1)


class FakeRepository:
    """Dictionary-backed stand-in for SqlAlchemyRepository."""

    def __init__(self):
        self.rows = {}
        self.commits = 0

    def get(self, entity_id):
        return self.rows.get(entity_id)

    def add(self, entity):
        if getattr(entity, "id", None) is None:
            entity.id = next(_ids)
        self.rows[entity.id] = entity
        return entity

    def delete(self, entity):
        self.rows.pop(entity.id, None)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


class FakeSessions(FakeRepository):
    def for_user(self, user_id):
        return [s for s in self.rows.values() if s.user_id == user_id]

    def owned(self, session_id, user_id):
        session = self.rows.get(session_id)
        return session if session and session.user_id == user_id else None


class FakeMessages(FakeRepository):
    def latest(self, session_id, limit):
        rows = sorted((m for m in self.rows.values() if m.session_id == session_id), key=lambda m: m.id)
        return rows[-limit:]

    def for_session(self, session):
        return self.latest(session.id, 10_000)


class FakeModels:
    """The model strategy: streams a fixed reply and records prompts."""

    def __init__(self, reply=("Hi", " there")):
        self.reply, self.prompts = reply, []

    def default_model(self):
        return "fake-model"

    def list_models(self):
        return ["fake-model"]

    def stream_chat(self, messages, model):
        self.prompts.append(messages)
        return iter(self.reply)


class NoDocuments:
    def retrieve(self, query, user_id):
        return []


@pytest.fixture
def chat(app):
    with app.test_request_context():
        yield ChatService(FakeSessions(), FakeMessages(), FakeModels(), NoDocuments())


def test_sessions_are_scoped_to_their_owner(chat):
    session = chat.create_session(user_id=1, title="  Recursion  ")
    assert session.title == "Recursion"
    assert chat.list_sessions(1) == [session]
    assert chat.list_sessions(2) == []
    with pytest.raises(NotFound):
        chat.update_session(2, session.id, {"title": "mine now"})


def test_update_rejects_blank_titles_and_trims_models(chat):
    session = chat.create_session(user_id=1)
    with pytest.raises(InvalidInput, match="Title cannot be empty"):
        chat.update_session(1, session.id, {"title": "   "})
    assert chat.update_session(1, session.id, {"model": "  llama3  "}).model == "llama3"
    assert chat.update_session(1, session.id, {"model": ""}).model is None


def test_reply_streams_saves_and_titles_the_session(chat):
    session = chat.create_session(user_id=1)
    events = list(chat.start_reply(1, session.id, "What is recursion?").events())

    assert [e["type"] for e in events] == ["start", "token", "token", "done"]
    assert events[-1]["message"]["bot_response"] == "Hi there"
    assert chat.sessions.get(session.id).title == "What is recursion?"
    assert chat.models.prompts[-1][-1] == {"role": "user", "content": "What is recursion?"}


def test_stopping_early_still_saves_the_partial_answer(chat):
    session = chat.create_session(user_id=1)
    events = chat.start_reply(1, session.id, "hello").events()
    next(events)  # start
    next(events)  # first token
    events.close()  # the client disconnected

    saved = chat.history(1, session.id)
    assert [m.bot_response for m in saved] == ["Hi"]


def test_reply_validation(chat):
    session = chat.create_session(user_id=1)
    with pytest.raises(InvalidInput):
        chat.start_reply(1, session.id, "   ")
    with pytest.raises(InvalidInput):
        chat.start_reply(1, session.id, "x" * 8001)
    with pytest.raises(NotFound):
        chat.start_reply(1, 999, "hi")


def test_model_outage_becomes_a_dependency_error(app):
    class DownModels(FakeModels):
        def stream_chat(self, messages, model):
            raise llm.LLMError("connection refused")

    with app.test_request_context():
        service = ChatService(FakeSessions(), FakeMessages(), DownModels(), NoDocuments())
        session = service.create_session(user_id=1)
        with pytest.raises(Exception) as error:
            service.start_reply(1, session.id, "hi")
    assert error.value.status == 502


# ---- AuthService ----

class FakeUsers(FakeRepository):
    def _find(self, predicate):
        return next((u for u in self.rows.values() if predicate(u)), None)

    def by_login(self, identifier):
        return self._find(lambda u: u.username == identifier or u.email == identifier.lower())

    def by_username(self, username):
        return self._find(lambda u: u.username == username)

    def by_email(self, email):
        return self._find(lambda u: u.email == email.lower())

    def by_google_sub(self, sub):
        return self._find(lambda u: u.google_sub == sub)

    def exists(self, username, email):
        return self._find(lambda u: u.username == username or u.email == email) is not None


@pytest.fixture
def auth(app):
    with app.app_context():
        yield AuthService(FakeUsers())


def test_register_and_authenticate(auth):
    user = auth.register("ada", "Ada@Example.com", "password123")
    assert user.email == "ada@example.com"
    assert auth.authenticate("ADA@example.com", "password123") is user
    with pytest.raises(Unauthorized):
        auth.authenticate("ada", "wrong-password")
    with pytest.raises(Conflict):
        auth.register("ada", "other@example.com", "password123")


def test_google_identity_never_takes_over_a_password_account(auth):
    auth.register("ada", "ada@example.com", "password123")
    info = {"sub": "g-1", "email": "ada@example.com", "email_verified": True}
    with pytest.raises(GoogleSignInError) as error:
        auth.google_sign_in(info)
    assert error.value.code == "account_exists"


def test_google_sign_in_creates_then_reuses_the_account(auth):
    info = {"sub": "g-2", "email": "grace@example.com", "email_verified": True, "name": "Grace"}
    first = auth.google_sign_in(info)
    assert isinstance(first, User) and first.password is None and first.username == "grace"
    assert auth.google_sign_in(info) is first


def test_unknown_session_owner_is_not_found(chat):
    other = chat.sessions.add(ChatSession(user_id=7, title="theirs"))
    with pytest.raises(NotFound):
        chat.history(1, other.id)
