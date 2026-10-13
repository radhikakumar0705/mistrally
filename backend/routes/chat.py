import os

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models.chat_history import ChatHistory
from models.chat_session import ChatSession, DEFAULT_TITLE
from services import chroma_service, ollama_service
from utils.file_helper import allowed_file, save_uploaded_file, extract_text

chat_bp = Blueprint("chat", __name__)

HISTORY_TURNS = 5   # previous turns sent to the model as conversation context
TITLE_LENGTH = 60   # sessions are titled from the start of their first message


def _current_user_id():
    return int(get_jwt_identity())


def _find_session(session_id, user_id):
    return ChatSession.query.filter_by(id=session_id, user_id=user_id).first()


@chat_bp.route("/sessions", methods=["GET"])
@jwt_required()
def list_sessions():
    sessions = (
        ChatSession.query.filter_by(user_id=_current_user_id())
        .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
        .all()
    )
    return jsonify([s.to_dict() for s in sessions]), 200


@chat_bp.route("/sessions", methods=["POST"])
@jwt_required()
def create_session():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or DEFAULT_TITLE).strip()[:255]

    session = ChatSession(user_id=_current_user_id(), title=title)
    db.session.add(session)
    db.session.commit()
    return jsonify(session.to_dict()), 201


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
def send_message(session_id):
    user_id = _current_user_id()
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()

    if not user_msg:
        return jsonify({"error": "Message is required"}), 400

    session = _find_session(session_id, user_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    history = (
        ChatHistory.query.filter_by(session_id=session.id)
        .order_by(ChatHistory.timestamp.desc(), ChatHistory.id.desc())
        .limit(HISTORY_TURNS)
        .all()
    )

    # Document retrieval is best-effort: a vector store problem shouldn't block chatting.
    try:
        context = chroma_service.retrieve_context(user_msg, user_id)
    except Exception:
        current_app.logger.exception("Document retrieval failed")
        context = ""

    messages = ollama_service.build_messages(reversed(history), context, user_msg)

    try:
        bot_response = ollama_service.chat(messages)
    except ollama_service.OllamaError as e:
        current_app.logger.error("Ollama request failed: %s", e)
        return jsonify({"error": "The AI model is unavailable. Is Ollama running?"}), 502

    entry = ChatHistory(
        session_id=session.id,
        user_id=user_id,
        user_message=user_msg,
        bot_response=bot_response,
    )
    db.session.add(entry)

    if session.title == DEFAULT_TITLE:
        session.title = user_msg[:TITLE_LENGTH]

    db.session.commit()

    return jsonify({
        "response": bot_response,
        "message": entry.to_dict(),
        "session": session.to_dict(),
    }), 200


@chat_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    """Add a PDF or TXT document to the user's knowledge base for RAG."""
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only .pdf and .txt files are supported"}), 400

    path = save_uploaded_file(file)
    try:
        text = extract_text(path)
    except Exception:
        current_app.logger.exception("Text extraction failed")
        return jsonify({"error": "Could not read that file"}), 422
    finally:
        os.remove(path)

    if not text:
        return jsonify({"error": "No text found in that file"}), 422

    chunks = chroma_service.add_document(text, _current_user_id(), file.filename)
    return jsonify({"filename": file.filename, "chunks": chunks}), 201
