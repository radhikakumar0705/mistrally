import json

import pytest
import requests

from services import ollama_service


class FakeResponse:
    def __init__(self, lines=(), status=200, body=None):
        self.lines = [json.dumps(line).encode() for line in lines]
        self.status_code = status
        self.body = body or {}
        self.closed = False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} error", response=self)

    def json(self):
        return self.body

    def iter_lines(self):
        yield from self.lines

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True


def test_stream_chat_yields_content_until_done(app, monkeypatch):
    response = FakeResponse([
        {"message": {"content": "Hel"}, "done": False},
        {"message": {"content": "lo"}, "done": False},
        {"message": {"content": ""}, "done": True},
        {"message": {"content": "ignored"}, "done": False},
    ])
    sent = {}

    def fake_post(url, json, stream, timeout):
        sent.update(url=url, body=json)
        return response

    monkeypatch.setattr(requests, "post", fake_post)
    with app.app_context():
        pieces = list(ollama_service.stream_chat([{"role": "user", "content": "hi"}], "mistral"))

    assert pieces == ["Hel", "lo"]
    assert response.closed
    assert sent["url"].endswith("/api/chat")
    assert sent["body"]["stream"] is True
    assert sent["body"]["model"] == "mistral"


def test_stream_chat_reports_ollama_errors(app, monkeypatch):
    missing = FakeResponse(status=404, body={"error": "model 'nope' not found"})
    monkeypatch.setattr(requests, "post", lambda *a, **k: missing)
    with app.app_context(), pytest.raises(ollama_service.OllamaError, match="model 'nope' not found"):
        ollama_service.stream_chat([], "nope")

    def refuse(*args, **kwargs):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(requests, "post", refuse)
    with app.app_context(), pytest.raises(ollama_service.OllamaError, match="Is it running"):
        ollama_service.stream_chat([], "mistral")


def test_build_messages_includes_document_excerpts():
    class Turn:
        user_message, bot_response = "q1", "a1"

    messages = ollama_service.build_messages(
        [Turn()], [{"source": "notes.pdf", "text": "BLUE HERON"}], "q2"
    )
    assert "[notes.pdf]\nBLUE HERON" in messages[0]["content"]
    assert messages[1:] == [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
    ]
