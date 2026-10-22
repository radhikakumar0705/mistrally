"""HTTP layer for documents: file handling and status codes around DocumentService."""
import click
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import limiter, user_or_ip
from services.document_service import DocumentService

documents_bp = Blueprint("documents", __name__)


def _user_id() -> int:
    return int(get_jwt_identity())


@documents_bp.route("", methods=["GET"])
@jwt_required()
def list_documents():
    return jsonify([d.to_dict() for d in DocumentService().list(_user_id())]), 200


@documents_bp.route("/<doc_id>", methods=["GET"])
@jwt_required()
def get_document(doc_id):
    return jsonify(DocumentService().get(_user_id(), doc_id).to_dict()), 200


@documents_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit("10/minute", key_func=user_or_ip)
def upload_document():
    """
    Accept a PDF, TXT or Markdown file and queue it for processing. Returns 202 while it is being
    processed in the background (poll GET /documents/<id>), or 201 if it was processed inline.
    """
    file = request.files.get("file")
    document, queued = DocumentService().upload(
        _user_id(), file.filename if file else None, file.read() if file else b""
    )
    return jsonify(document.to_dict()), 202 if queued else 201


@documents_bp.route("/<doc_id>", methods=["DELETE"])
@jwt_required()
def delete_document(doc_id):
    DocumentService().delete(_user_id(), doc_id)
    return "", 204


@documents_bp.cli.command("backfill")
def backfill_documents():
    """Create document records for files uploaded before documents were tracked in the database."""
    click.echo(f"Created {DocumentService().backfill()} document record(s).")
