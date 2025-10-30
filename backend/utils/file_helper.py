import os
import uuid
import PyPDF2
from werkzeug.utils import secure_filename

# Allowed file types for ingestion
ALLOWED_EXTENSIONS = {'txt', 'pdf'}

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploaded_files")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file):
    """
    Save the uploaded file to the UPLOAD_FOLDER and return its full path.
    Generates a unique filename to avoid collisions.
    """
    if not allowed_file(file.filename):
        raise ValueError("Unsupported file type")

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(file_path)
    return file_path


def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file using PyPDF2.
    """
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text.strip()


def extract_text_from_txt(file_path):
    """
    Extract text from a TXT file.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def extract_text(file_path):
    """
    Wrapper: detect file type and extract text accordingly.
    """
    ext = file_path.rsplit('.', 1)[1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    elif ext == "txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
