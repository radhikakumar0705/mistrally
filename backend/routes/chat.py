import json

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db, limiter, user_or_ip
from models.chat_history import ChatHistory
from models.chat_session import DEFAULT_TITLE, ChatSession
from observability import LLM_STREAMS, RAG_CHUNKS_USED, RAG_RETRIEVAL_SECONDS, StreamMetrics
from services import llm, retrieval
from services.prompts import build_messages

chat_bp = Blueprint("chat", __name__)

HISTORY_TURNS = 5   # previous turns sent to the model as conversation context
TITLE_LENGTH = 60   # sessions are titled from the start of their first message
MAX_MESSAGE_LENGTH = 8000


def _current_user_id():
    return int(get_jwt_identity())


def _find_session(session_id, user_id):
    return ChatSession.query.filter_by(id=session_id, user_id=user_id).first()


def _clean_model(value):
    value = (value or "").strip()
    return value[:100] or None


@chat_bp.route("/models", methods=["GET"])
@jwt_required()
def list_models():
    try:
        models = llm.list_models()
    except llm.LLMError as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"models": models, "default": llm.default_model(),
                    "provider": current_app.config["LLM_PROVIDER"]}), 200


@chat_bp.route("/sessions", methods=["GET"])
@jwt_required()
def list_sessions():
    sessions = (
        ChatSession.query.filter_by(user_id=_current_user_id())
        .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
        .all()
    )
    return jsonify([s.to_dict() for s in sessions]), 200


@chat_bp.route("/sessions", methods=["POST"])
@jwt_required()
def create_session():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or DEFAULT_TITLE).strip()[:255]

    session = ChatSession(user_id=_current_user_id(), title=title, model=_clean_model(data.get("model")))
    db.session.add(session)
    db.session.commit()
    return jsonify(session.to_dict()), 201


@chat_bp.route("/sessions/<int:session_id>", methods=["PATCH"])
@jwt_required()
def update_session(session_id):
    session = _find_session(session_id, _current_user_id())
    if not session:
        return jsonify({"error": "Session not found"}), 404

    data = request.get_json(silent=True) or {}
    if "title" in data:
        title = (data.get("title") or "").strip()[:255]
        if not title:
            return jsonify({"error": "Title cannot be empty"}), 400
        session.title = title
    if "model" in data:
        session.model = _clean_model(data.get("model"))

    db.session.commit()
    return jsonify(session.to_dict()), 200


@chat_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
@jwt_required()
def delete_session(session_id):
    session = _find_session(session_id, _current_user_id())
    if not session:
        return jsonify({"error": "Session not found"}), 404

    db.session.delete(session)
    db.session.commit()
    return "", 204


@chat_bp.route("/sessions/<int:session_id>/messages", methods=["GET"])
@jwt_required()
def get_messages(session_id):
    session = _find_session(session_id, _current_user_id())
    if not session:
        return jsonify({"error": "Session not found"}), 404

    return jsonify([m.to_dict() for m in session.messages]), 200


@chat_bp.route("/sessions/<int:session_id>/messages", methods=["POST"])
@jwt_required()
@limiter.limit("20/minute", key_func=user_or_ip)
def send_message(session_id):
    """Send a message and stream the reply back as server-sent events."""
    user_id = _current_user_id()
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()

    if not user_msg:
        return jsonify({"error": "Message is required"}), 400
    if len(user_msg) > MAX_MESSAGE_LENGTH:
        return jsonify({"error": f"Message must be {MAX_MESSAGE_LENGTH} characters or fewer"}), 400

    session = _find_session(session_id, user_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    history = (
        ChatHistory.query.filter_by(session_id=session.id)
        .order_by(ChatHistory.id.desc())
        .limit(HISTORY_TURNS)
        .all()
    )
    return _stream_reply(session, user_id, user_msg, list(reversed(history)))


@chat_bp.route("/sessions/<int:session_id>/regenerate", methods=["POST"])
@jwt_required()
@limiter.limit("20/minute", key_func=user_or_ip)
def regenerate(session_id):
    """Answer the last message again, replacing the previous answer once the new one is saved."""
    user_id = _current_user_id()
    session = _find_session(session_id, user_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    recent = (
        ChatHistory.query.filter_by(session_id=session.id)
        .order_by(ChatHistory.id.desc())
        .limit(HISTORY_TURNS + 1)
        .all()
    )
    if not recent:
        return jsonify({"error": "Nothing to regenerate"}), 400

    last, history = recent[0], list(reversed(recent[1:]))
    return _stream_reply(session, user_id, last.user_message, history, replaces=last.id)


def _sources(chunks):
    """Distinct documents (and pages) an answer drew on, most relevant first."""
    seen, sources = set(), []
    for chunk in chunks:
        key = (chunk["source"], chunk.get("page"))
        if key not in seen:
            seen.add(key)
            sources.append({"document": chunk["source"], "page": chunk.get("page")})
    return sources


def _sse(event):
    return f"data: {json.dumps(event)}\n\n"


def _stream_reply(session, user_id, user_msg, history, replaces=None):
    # Document retrieval is best-effort: a vector store problem shouldn't block chatting.
    try:
        with RAG_RETRIEVAL_SECONDS.time():
            chunks = retrieval.retrieve(user_msg, user_id)
        RAG_CHUNKS_USED.observe(len(chunks))
    except Exception:
        current_app.logger.exception("Document retrieval failed")
        chunks = []
    sources = _sources(chunks)

    messages = build_messages(history, chunks, user_msg)
    model = session.model or llm.default_model()
    provider = current_app.config["LLM_PROVIDER"]
    # Start timing before the call: providers like Ollama only respond once the first token exists
    timing = StreamMetrics(provider, model)
    try:
        pieces = llm.stream_chat(messages, model)
    except llm.LLMError as e:
        LLM_STREAMS.labels(provider=provider, model=model, outcome="unavailable").inc()
        current_app.logger.error("Model request failed: %s", e)
        return jsonify({"error": f"The AI model is unavailable: {e}"}), 502

    session_id = session.id

    def save(reply):
        session = db.session.get(ChatSession, session_id)
        if replaces is not None:
            old = db.session.get(ChatHistory, replaces)
            if old is not None:
                db.session.delete(old)
        entry = ChatHistory(
            session_id=session_id,
            user_id=user_id,
            user_message=user_msg,
            bot_response=reply,
            sources=json.dumps(sources) if sources else None,
        )
        db.session.add(entry)
        if session.title == DEFAULT_TITLE:
            session.title = user_msg[:TITLE_LENGTH]
        session.touch()
        db.session.commit()
        return entry, session

    def generate():
        reply = []
        saved = False
        try:
            yield _sse({"type": "start", "sources": sources, "model": model})
            try:
                for piece in pieces:
                    timing.piece()
                    reply.append(piece)
                    yield _sse({"type": "token", "content": piece})
            except llm.LLMError as e:
                timing.finish("error")
                current_app.logger.error("Model stream failed: %s", e)
                yield _sse({"type": "error", "error": str(e)})

            text = "".join(reply).strip()
            if text:
                entry, session = save(text)
                saved = True
                timing.finish("completed")
                yield _sse({"type": "done", "message": entry.to_dict(), "session": session.to_dict()})
        finally:
            # The client disconnected (e.g. pressed Stop): keep whatever was generated so far
            pieces.close()
            timing.finish("stopped")  # no-op if the answer already completed or failed
            text = "".join(reply).strip()
            if not saved and text:
                try:
                    save(text)
                except Exception:
                    current_app.logger.exception("Could not save partial reply")
                    db.session.rollback()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
