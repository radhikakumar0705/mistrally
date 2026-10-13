import hashlib
import uuid

import click
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db, limiter, user_or_ip
from models.document import Document
from observability import DOCUMENTS_INGESTED
from services import chroma_service, tasks
from services.chunking import allowed_file, file_type

documents_bp = Blueprint("documents", __name__)


def _current_user_id():
    return int(get_jwt_identity())


def _find(doc_id, user_id):
    return Document.query.filter_by(id=doc_id, user_id=user_id).first()


@documents_bp.route("", methods=["GET"])
@jwt_required()
def list_documents():
    documents = (
        Document.query.filter_by(user_id=_current_user_id())
        .order_by(Document.created_at.desc())
        .all()
    )
    return jsonify([d.to_dict() for d in documents]), 200


@documents_bp.route("/<doc_id>", methods=["GET"])
@jwt_required()
def get_document(doc_id):
    document = _find(doc_id, _current_user_id())
    if not document:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(document.to_dict()), 200


@documents_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit("10/minute", key_func=user_or_ip)
def upload_document():
    """
    Accept a PDF, TXT or Markdown file and queue it for processing. Returns 202 while it is being
    processed in the background (poll GET /documents/<id>), or 201 if it was processed inline.
    """
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only .pdf, .txt and .md files are supported"}), 400

    data = file.read()
    if not data.strip():
        DOCUMENTS_INGESTED.labels(status="unreadable").inc()
        return jsonify({"error": "That file is empty"}), 422

    document = Document(
        id=uuid.uuid4().hex,
        user_id=_current_user_id(),
        filename=file.filename[:255],
        file_type=file_type(file.filename),
        size_bytes=len(data),
    )
    db.session.add(document)
    db.session.commit()

    try:
        queued = tasks.submit_ingestion(document.id, data)
    except Exception:
        current_app.logger.exception("Could not queue document", extra={"document_id": document.id})
        document.status, document.error = "failed", "The processing queue is unavailable"
        db.session.commit()
        return jsonify(document.to_dict()), 503

    db.session.refresh(document)
    if not queued and document.status == "failed":
        return jsonify({**document.to_dict(), "error": document.error}), 422
    return jsonify(document.to_dict()), 202 if queued else 201


@documents_bp.route("/<doc_id>", methods=["DELETE"])
@jwt_required()
def delete_document(doc_id):
    user_id = _current_user_id()
    document = _find(doc_id, user_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404
    try:
        if document.id.startswith("legacy"):
            chroma_service.delete_chunks_by_source(user_id, document.filename)
        else:
            chroma_service.delete_document_chunks(document.id)
    except Exception:
        current_app.logger.exception("Could not delete chunks", extra={"document_id": doc_id})
        return jsonify({"error": "The document store is unavailable"}), 503
    db.session.delete(document)
    db.session.commit()
    return "", 204


@documents_bp.cli.command("backfill")
def backfill_documents():
    """Create document records for files uploaded before documents were tracked in the database."""
    from models.user import User

    created = 0
    for user in User.query.all():
        known = {d.id for d in Document.query.filter_by(user_id=user.id)}
        for doc in chroma_service.legacy_documents(user.id):
            doc_id = doc["id"]
            if doc_id.startswith("legacy-"):
                doc_id = "legacy" + hashlib.sha1(doc["filename"].encode()).hexdigest()[:26]
            if doc_id in known:
                continue
            db.session.add(Document(
                id=doc_id, user_id=user.id, filename=doc["filename"][:255],
                file_type=file_type(doc["filename"]) or "txt", status="ready", progress=100, chunks=doc["chunks"],
            ))
            created += 1
    db.session.commit()
    click.echo(f"Created {created} document record(s).")
