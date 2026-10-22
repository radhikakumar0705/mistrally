"""HTTP layer for study mode: quizzes, flashcards and the code runner."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import limiter, user_or_ip
from services.study_service import SandboxClient, StudyService

study_bp = Blueprint("study", __name__)


def _body() -> dict:
    return request.get_json(silent=True) or {}


@study_bp.route("/quiz", methods=["POST"], defaults={"kind": "quiz"})
@study_bp.route("/flashcards", methods=["POST"], defaults={"kind": "flashcards"})
@jwt_required()
@limiter.limit("10/minute", key_func=user_or_ip)
def generate(kind):
    """Generate a quiz or flashcards from one of the user's documents or from a topic."""
    return jsonify(StudyService().create(int(get_jwt_identity()), kind, _body())), 200


@study_bp.route("/run", methods=["POST"])
@jwt_required()
@limiter.limit("20/minute", key_func=user_or_ip)
def run_code():
    body = _body()
    return jsonify(SandboxClient().run(body.get("code"), body.get("stdin"), body.get("language"))), 200
