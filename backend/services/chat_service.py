"""Conversations and streamed answers: the chat use cases, independent of HTTP."""
import json
from collections.abc import Iterator
from dataclasses import dataclass, field

from flask import current_app

from models.chat_history import ChatHistory
from models.chat_session import DEFAULT_TITLE, ChatSession
from observability import LLM_STREAMS, RAG_CHUNKS_USED, RAG_RETRIEVAL_SECONDS, StreamMetrics
from repositories import ChatSessionRepository, MessageRepository
from services import export, llm, retrieval
from services.errors import DependencyUnavailable, InvalidInput, NotFound
from services.prompts import build_messages

HISTORY_TURNS = 5  # previous turns sent to the model as conversation context
TITLE_LENGTH = 60  # sessions are titled from the start of their first message
MAX_MESSAGE_LENGTH = 8000


def _clean_model(value) -> str | None:
    return (value or "").strip()[:100] or None


def _sources(chunks) -> list[dict]:
    """Distinct documents (and pages) an answer drew on, most relevant first."""
    seen, sources = set(), []
    for chunk in chunks:
        key = (chunk["source"], chunk.get("page"))
        if key not in seen:
            seen.add(key)
            sources.append({"document": chunk["source"], "page": chunk.get("page")})
    return sources


class ChatService:
    """
    Use cases for conversations. Dependencies are passed in, so tests can substitute fakes:
    repositories for storage, `models` for the language model (the Strategy chosen by LLM_PROVIDER)
    and `retriever` for document search.
    """

    def __init__(self, sessions=None, messages=None, models=llm, retriever=retrieval):
        self.sessions = sessions or ChatSessionRepository()
        self.messages = messages or MessageRepository()
        self.models = models
        self.retriever = retriever

    # ---- Conversations ----

    def _owned(self, user_id: int, session_id: int) -> ChatSession:
        session = self.sessions.owned(session_id, user_id)
        if session is None:
            raise NotFound("Session not found")
        return session

    def list_sessions(self, user_id: int) -> list[ChatSession]:
        return self.sessions.for_user(user_id)

    def create_session(self, user_id: int, title=None, model=None) -> ChatSession:
        session = ChatSession(
            user_id=user_id,
            title=(title or DEFAULT_TITLE).strip()[:255],
            model=_clean_model(model),
        )
        self.sessions.add(session)
        self.sessions.commit()
        return session

    def update_session(self, user_id: int, session_id: int, changes: dict) -> ChatSession:
        session = self._owned(user_id, session_id)
        if "title" in changes:
            title = (changes.get("title") or "").strip()[:255]
            if not title:
                raise InvalidInput("Title cannot be empty")
            session.title = title
        if "model" in changes:
            session.model = _clean_model(changes.get("model"))
        self.sessions.commit()
        return session

    def delete_session(self, user_id: int, session_id: int) -> None:
        self.sessions.delete(self._owned(user_id, session_id))
        self.sessions.commit()

    def history(self, user_id: int, session_id: int) -> list[ChatHistory]:
        return self.messages.for_session(self._owned(user_id, session_id))

    def export_markdown(self, user_id: int, session_id: int) -> tuple[str, str]:
        """The conversation as Markdown, plus a safe file name for downloading it."""
        session = self._owned(user_id, session_id)
        return export.export_filename(session.title), export.to_markdown(session, self.messages.for_session(session))

    def available_models(self) -> dict:
        try:
            names = self.models.list_models()
        except llm.LLMError as e:
            raise DependencyUnavailable(str(e)) from e
        return {"models": names, "default": self.models.default_model(),
                "provider": current_app.config["LLM_PROVIDER"]}

    # ---- Answers ----

    def start_reply(self, user_id: int, session_id: int, message) -> "ReplyStream":
        text = (message or "").strip()
        if not text:
            raise InvalidInput("Message is required")
        if len(text) > MAX_MESSAGE_LENGTH:
            raise InvalidInput(f"Message must be {MAX_MESSAGE_LENGTH} characters or fewer")
        session = self._owned(user_id, session_id)
        history = self.messages.latest(session.id, HISTORY_TURNS)
        return self._start(session, user_id, text, history)

    def start_regeneration(self, user_id: int, session_id: int) -> "ReplyStream":
        """Answer the last message again; the old answer is replaced once the new one is saved."""
        session = self._owned(user_id, session_id)
        recent = self.messages.latest(session.id, HISTORY_TURNS + 1)
        if not recent:
            raise InvalidInput("Nothing to regenerate")
        last = recent[-1]
        return self._start(session, user_id, last.user_message, recent[:-1], replaces=last.id)

    def _start(self, session, user_id, text, history, replaces=None) -> "ReplyStream":
        # Document retrieval is best-effort: a vector store problem shouldn't block chatting.
        try:
            with RAG_RETRIEVAL_SECONDS.time():
                chunks = self.retriever.retrieve(text, user_id)
            RAG_CHUNKS_USED.observe(len(chunks))
        except Exception:
            current_app.logger.exception("Document retrieval failed")
            chunks = []

        model = session.model or self.models.default_model()
        provider = current_app.config["LLM_PROVIDER"]
        # Start timing before the call: providers like Ollama only respond once the first token exists
        timing = StreamMetrics(provider, model)
        try:
            pieces = self.models.stream_chat(build_messages(history, chunks, text), model)
        except llm.LLMError as e:
            LLM_STREAMS.labels(provider=provider, model=model, outcome="unavailable").inc()
            current_app.logger.error("Model request failed: %s", e)
            raise DependencyUnavailable(f"The AI model is unavailable: {e}") from e

        return ReplyStream(
            service=self, session_id=session.id, user_id=user_id, question=text, model=model,
            sources=_sources(chunks), pieces=pieces, timing=timing, replaces=replaces,
        )

    def save_answer(self, stream: "ReplyStream", answer: str) -> tuple[ChatHistory, ChatSession]:
        session = self.sessions.get(stream.session_id)
        if stream.replaces is not None:
            old = self.messages.get(stream.replaces)
            if old is not None:
                self.messages.delete(old)
        entry = self.messages.add(ChatHistory(
            session_id=stream.session_id,
            user_id=stream.user_id,
            user_message=stream.question,
            bot_response=answer,
            sources=json.dumps(stream.sources) if stream.sources else None,
        ))
        if session.title == DEFAULT_TITLE:
            session.title = stream.question[:TITLE_LENGTH]
        session.touch()
        self.sessions.commit()
        return entry, session


@dataclass
class ReplyStream:
    """
    One answer being generated. `events()` yields start, token, error and done events; if the consumer
    stops early (the user pressed Stop and the connection closed), the partial answer is still saved.
    """

    service: ChatService
    session_id: int
    user_id: int
    question: str
    model: str
    sources: list
    pieces: Iterator[str]
    timing: StreamMetrics
    replaces: int | None = None
    _reply: list = field(default_factory=list)
    _saved: bool = False

    def events(self) -> Iterator[dict]:
        try:
            yield {"type": "start", "sources": self.sources, "model": self.model}
            try:
                for piece in self.pieces:
                    self.timing.piece()
                    self._reply.append(piece)
                    yield {"type": "token", "content": piece}
            except llm.LLMError as e:
                self.timing.finish("error")
                current_app.logger.error("Model stream failed: %s", e)
                yield {"type": "error", "error": str(e)}

            answer = "".join(self._reply).strip()
            if answer:
                entry, session = self.service.save_answer(self, answer)
                self._saved = True
                self.timing.finish("completed")
                yield {"type": "done", "message": entry.to_dict(), "session": session.to_dict()}
        finally:
            # Generators close their HTTP stream (telling the model to stop); plain iterators need nothing
            close = getattr(self.pieces, "close", None)
            if close:
                close()
            self.timing.finish("stopped")  # no-op if the answer already completed or failed
            answer = "".join(self._reply).strip()
            if not self._saved and answer:
                try:
                    self.service.save_answer(self, answer)
                except Exception:
                    current_app.logger.exception("Could not save partial reply")
                    self.service.sessions.rollback()
