"""HTTP layer for conversations: parse the request, call ChatService, serialize the result."""
import json

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import limiter, user_or_ip
from services.chat_service import ChatService, ReplyStream

chat_bp = Blueprint("chat", __name__)


def _user_id() -> int:
    return int(get_jwt_identity())


def _body() -> dict:
    return request.get_json(silent=True) or {}


def _event_stream(reply: ReplyStream) -> Response:
    def generate():
        # `yield from` passes a client disconnect (generator close) through to the reply, which saves
        # the partial answer
        yield from (f"data: {json.dumps(event)}\n\n" for event in reply.events())

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@chat_bp.route("/models", methods=["GET"])
@jwt_required()
def list_models():
    return jsonify(ChatService().available_models()), 200


@chat_bp.route("/sessions", methods=["GET"])
@jwt_required()
def list_sessions():
    return jsonify([s.to_dict() for s in ChatService().list_sessions(_user_id())]), 200


@chat_bp.route("/sessions", methods=["POST"])
@jwt_required()
def create_session():
    body = _body()
    session = ChatService().create_session(_user_id(), body.get("title"), body.get("model"))
    return jsonify(session.to_dict()), 201


@chat_bp.route("/sessions/<int:session_id>", methods=["PATCH"])
@jwt_required()
def update_session(session_id):
    return jsonify(ChatService().update_session(_user_id(), session_id, _body()).to_dict()), 200


@chat_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
@jwt_required()
def delete_session(session_id):
    ChatService().delete_session(_user_id(), session_id)
    return "", 204


@chat_bp.route("/sessions/<int:session_id>/messages", methods=["GET"])
@jwt_required()
def get_messages(session_id):
    return jsonify([m.to_dict() for m in ChatService().history(_user_id(), session_id)]), 200


@chat_bp.route("/sessions/<int:session_id>/export", methods=["GET"])
@jwt_required()
def export_session(session_id):
    """Download the conversation as a Markdown file."""
    filename, markdown = ChatService().export_markdown(_user_id(), session_id)
    return Response(
        markdown,
        mimetype="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@chat_bp.route("/sessions/<int:session_id>/messages", methods=["POST"])
@jwt_required()
@limiter.limit("20/minute", key_func=user_or_ip)
def send_message(session_id):
    """Send a message and stream the reply back as server-sent events."""
    return _event_stream(ChatService().start_reply(_user_id(), session_id, _body().get("message")))


@chat_bp.route("/sessions/<int:session_id>/regenerate", methods=["POST"])
@jwt_required()
@limiter.limit("20/minute", key_func=user_or_ip)
def regenerate(session_id):
    """Answer the last message again, replacing the previous answer once the new one is saved."""
    return _event_stream(ChatService().start_regeneration(_user_id(), session_id))
