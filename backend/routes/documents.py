import os

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import limiter, user_or_ip
from services import chroma_service
from utils.file_helper import allowed_file, extract_text, save_uploaded_file

documents_bp = Blueprint("documents", __name__)


def _current_user_id():
    return int(get_jwt_identity())


@documents_bp.route("", methods=["GET"])
@jwt_required()
def list_documents():
    try:
        documents = chroma_service.list_documents(_current_user_id())
    except Exception:
        current_app.logger.exception("Listing documents failed")
        return jsonify({"error": "The document store is unavailable"}), 503
    return jsonify(documents), 200


@documents_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit("10/minute", key_func=user_or_ip)
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

    try:
        document = chroma_service.add_document(text, _current_user_id(), file.filename)
    except Exception:
        current_app.logger.exception("Storing document failed")
        return jsonify({"error": "The document store is unavailable"}), 503
    return jsonify(document), 201


@documents_bp.route("/<doc_id>", methods=["DELETE"])
@jwt_required()
def delete_document(doc_id):
    if not chroma_service.delete_document(_current_user_id(), doc_id):
        return jsonify({"error": "Document not found"}), 404
    return "", 204
