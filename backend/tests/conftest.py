import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402
from extensions import db  # noqa: E402
from services import llm  # noqa: E402


def make_config(tmp_path, **overrides):
    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret-key"
        JWT_SECRET_KEY = "test-jwt-secret-key-at-least-32-bytes"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"
        SQLALCHEMY_ENGINE_OPTIONS = {}
        CHROMA_HOST = None
        CHROMA_DB_PATH = str(tmp_path / "chroma")
        RATELIMIT_ENABLED = False
        OLLAMA_MODEL = "test-model"
        LLM_PROVIDER = "ollama"
        JWT_REFRESH_COOKIE_PATH = "/auth/"
        GOOGLE_CLIENT_ID = None
        GOOGLE_CLIENT_SECRET = None

    for key, value in overrides.items():
        setattr(TestConfig, key, value)
    return TestConfig


@pytest.fixture
def app(tmp_path):
    app = create_app(make_config(tmp_path))
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


class FakeOllama:
    """Stands in for the model provider: records prompts and streams a canned reply."""

    def __init__(self):
        self.reply = ["Hello", " there", "!"]
        self.calls = []
        self.fail_to_start = None
        self.fail_mid_stream = None
        self.models = ["mistral:latest", "llama3.2:latest"]

    def stream_chat(self, messages, model):
        if self.fail_to_start:
            raise llm.LLMError(self.fail_to_start)
        self.calls.append({"messages": messages, "model": model})

        def pieces():
            for i, piece in enumerate(self.reply):
                if self.fail_mid_stream and i == 1:
                    raise llm.LLMError(self.fail_mid_stream)
                yield piece

        return pieces()

    def list_models(self):
        return self.models


@pytest.fixture
def ollama(monkeypatch):
    fake = FakeOllama()
    monkeypatch.setattr(llm, "stream_chat", fake.stream_chat)
    monkeypatch.setattr(llm, "list_models", fake.list_models)
    return fake


def register_and_login(client, username="alice", password="password123"):
    client.post("/auth/register", json={"username": username, "email": f"{username}@example.com",
                                        "password": password})
    token = client.post("/auth/login", json={"username": username, "password": password}).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth(client):
    return register_and_login(client)


def read_events(response):
    """Parse a server-sent-events response body into a list of event dicts."""
    import json

    body = response.get_data(as_text=True)
    return [json.loads(line[len("data: "):]) for line in body.splitlines() if line.startswith("data: ")]
