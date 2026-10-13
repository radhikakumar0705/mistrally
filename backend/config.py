import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _bool(name, default):
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


def _database_uri():
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    user = quote_plus(os.getenv("DB_USER", "root"))
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "mistrally")
    return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{name}"


class Config:
    # Required; create_app() refuses to start without them
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_EXPIRES_HOURS", "12")))

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
    # Number of reverse proxies in front of the app (nginx, ingress), so rate limits see the real client IP
    PROXY_FIX_HOPS = int(os.getenv("PROXY_FIX_HOPS", "0"))

    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    # Chroma: a server when CHROMA_HOST is set (Docker/Kubernetes), otherwise an on-disk store
    CHROMA_HOST = os.getenv("CHROMA_HOST")
    CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
    # Squared L2 distance on normalized embeddings; 1.4 keeps chunks with cosine similarity >= 0.3
    RAG_MAX_DISTANCE = float(os.getenv("RAG_MAX_DISTANCE", "1.4"))

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./data/uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024

    RATELIMIT_ENABLED = _bool("RATELIMIT_ENABLED", True)
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DEBUG = _bool("DEBUG", False)
