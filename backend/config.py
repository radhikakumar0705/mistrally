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
    # Short-lived access tokens (sent as Bearer headers, kept in memory by the frontend) plus
    # long-lived refresh tokens in an httpOnly cookie, rotated on every use
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "30")))
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_REFRESH_COOKIE_PATH = os.getenv("JWT_REFRESH_COOKIE_PATH", "/api/auth/")
    JWT_REFRESH_CSRF_COOKIE_PATH = "/"
    JWT_COOKIE_CSRF_PROTECT = True  # double-submit: the X-CSRF-TOKEN header must match a readable cookie
    JWT_COOKIE_SAMESITE = "Strict"
    COOKIE_SECURE = _bool("COOKIE_SECURE", False)  # True whenever the site is served over HTTPS
    JWT_COOKIE_SECURE = COOKIE_SECURE
    SESSION_COOKIE_SECURE = COOKIE_SECURE
    SESSION_COOKIE_SAMESITE = "Lax"  # the OAuth state cookie must survive the redirect back from Google
    SESSION_COOKIE_HTTPONLY = True

    # Public origin of the site, used to build the Google OAuth redirect URI
    PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:5173").rstrip("/")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
    # Number of reverse proxies in front of the app (nginx, ingress), so rate limits see the real client IP
    PROXY_FIX_HOPS = int(os.getenv("PROXY_FIX_HOPS", "0"))

    # Which model backend to use: ollama (local), groq, openai (any OpenAI-compatible API) or fake
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
    LLM_MODEL = os.getenv("LLM_MODEL")  # overrides the provider's default model
    # Comma-separated models offered in the picker for hosted providers (default: everything the API lists)
    LLM_MODELS = [m.strip() for m in os.getenv("LLM_MODELS", "").split(",") if m.strip()] or None
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    FAKE_LLM_DELAY = float(os.getenv("FAKE_LLM_DELAY", "0.02"))

    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    # Chroma: a server when CHROMA_HOST is set (Docker/Kubernetes), otherwise an on-disk store
    CHROMA_HOST = os.getenv("CHROMA_HOST")
    CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    # Retrieval: "hybrid" (embeddings + BM25 keywords) or "dense" (embeddings only), optionally re-ranked
    RAG_MODE = os.getenv("RAG_MODE", "hybrid")
    RAG_RERANK = _bool("RAG_RERANK", True)
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
    RAG_CANDIDATES = int(os.getenv("RAG_CANDIDATES", "20"))
    RAG_RERANK_CANDIDATES = int(os.getenv("RAG_RERANK_CANDIDATES", "12"))
    # Calibrated with eval/run_retrieval.py: unanswerable questions score <= 3e-5, correct passages >= 2.5e-4
    RAG_MIN_RERANK_SCORE = float(os.getenv("RAG_MIN_RERANK_SCORE", "1e-4"))
    RAG_RERANK_MODEL = os.getenv("RAG_RERANK_MODEL", "ms-marco-MiniLM-L-12-v2")
    RAG_RERANK_CACHE_DIR = os.getenv("RAG_RERANK_CACHE_DIR", os.path.expanduser("~/.cache/flashrank"))
    # Without re-ranking: squared L2 distance on normalized embeddings (1.4 = cosine >= 0.3) or a BM25 score
    RAG_MAX_DISTANCE = float(os.getenv("RAG_MAX_DISTANCE", "1.4"))
    RAG_MIN_BM25_SCORE = float(os.getenv("RAG_MIN_BM25_SCORE", "3.0"))

    # Isolated code runner service (see sandbox/); unset disables the "Run" button
    SANDBOX_URL = os.getenv("SANDBOX_URL")
    SANDBOX_TOKEN = os.getenv("SANDBOX_TOKEN", "")

    # Redis URL for the background document queue; unset = process uploads inside the request
    TASK_QUEUE_URL = os.getenv("TASK_QUEUE_URL")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024

    RATELIMIT_ENABLED = _bool("RATELIMIT_ENABLED", True)
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "text")  # "json" in containers
    # Traces go to this OTLP gRPC endpoint (e.g. http://jaeger:4317) when set
    OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "mistrally-backend")
    DEBUG = _bool("DEBUG", False)
