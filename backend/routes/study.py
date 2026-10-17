import requests
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import limiter, user_or_ip
from models.document import Document
from services import chroma_service, study

study_bp = Blueprint("study", __name__)

MAX_CODE_CHARS = 20_000


def _current_user_id():
    return int(get_jwt_identity())


@study_bp.route("/<kind>", methods=["POST"])
@jwt_required()
@limiter.limit("10/minute", key_func=user_or_ip)
def generate(kind):
    """Generate a quiz or flashcards from one of the user's documents or from a topic."""
    if kind not in study.KINDS:
        return jsonify({"error": "Unknown study material type"}), 404

    data = request.get_json(silent=True) or {}
    try:
        count = int(data.get("count", 5))
    except (TypeError, ValueError):
        return jsonify({"error": "count must be a number"}), 400
    limit = 10 if kind == "quiz" else 20
    if not 1 <= count <= limit:
        return jsonify({"error": f"count must be between 1 and {limit}"}), 400
    difficulty = data.get("difficulty", "medium")
    if difficulty not in ("easy", "medium", "hard"):
        return jsonify({"error": "difficulty must be easy, medium or hard"}), 400

    topic = (data.get("topic") or "").strip()[:200]
    document_id = data.get("document_id")
    context = None
    if document_id:
        document = Document.query.filter_by(id=document_id, user_id=_current_user_id()).first()
        if not document or document.status != "ready":
            return jsonify({"error": "Document not found or not ready"}), 404
        context = chroma_service.document_text(document.id)
        topic = topic or document.filename
    elif not topic:
        return jsonify({"error": "Choose a document or enter a topic"}), 400

    try:
        result = study.generate(kind, count=count, difficulty=difficulty, topic=topic, context=context,
                                model=data.get("model") or None)
    except study.StudyError as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"kind": kind, "source": topic, **result}), 200


# ---- Code runner (proxies to the isolated sandbox service) ----

@study_bp.route("/run", methods=["POST"])
@jwt_required()
@limiter.limit("20/minute", key_func=user_or_ip)
def run_code():
    config = current_app.config
    if not config.get("SANDBOX_URL"):
        return jsonify({"error": "The code runner is not enabled"}), 404

    data = request.get_json(silent=True) or {}
    code = data.get("code") or ""
    if not code.strip():
        return jsonify({"error": "No code to run"}), 400
    if len(code) > MAX_CODE_CHARS:
        return jsonify({"error": "That code is too long to run"}), 400
    if (data.get("language") or "python") != "python":
        return jsonify({"error": "Only Python can be run"}), 400

    try:
        response = requests.post(
            f"{config['SANDBOX_URL'].rstrip('/')}/run",
            json={"code": code, "stdin": (data.get("stdin") or "")[:10_000]},
            headers={"Authorization": f"Bearer {config['SANDBOX_TOKEN']}"},
            timeout=20,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        current_app.logger.exception("Sandbox request failed")
        return jsonify({"error": "The code runner is unavailable"}), 502
    return jsonify(response.json()), 200
