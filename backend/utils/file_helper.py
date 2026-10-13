import os
import uuid

from flask import current_app
from pypdf import PdfReader
from werkzeug.utils import secure_filename

# Allowed file types for ingestion
ALLOWED_EXTENSIONS = {"txt", "pdf"}


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file):
    """
    Save the uploaded file to the UPLOAD_FOLDER and return its full path.
    Generates a unique filename to avoid collisions.
    """
    if not allowed_file(file.filename):
        raise ValueError("Unsupported file type")

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(file.filename) or "upload"
    file_path = os.path.join(upload_folder, f"{uuid.uuid4().hex}_{filename}")
    file.save(file_path)
    return file_path


def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_text_from_txt(file_path):
    """Extract text from a TXT file."""
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def extract_text(file_path):
    """Detect file type and extract text accordingly."""
    ext = file_path.rsplit(".", 1)[1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    if ext == "txt":
        return extract_text_from_txt(file_path)
    raise ValueError(f"Unsupported file type: {ext}")
