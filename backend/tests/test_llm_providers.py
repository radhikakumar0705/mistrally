import json

import pytest
import requests
from conftest import make_config

from app import create_app
from services import llm
from services.llm.fake import FakeProvider
from services.llm.ollama import OllamaProvider
from services.llm.openai_compat import OpenAICompatibleProvider
from services.prompts import build_messages


class FakeResponse:
    def __init__(self, lines=(), status=200, body=None):
        self.lines = [line if isinstance(line, bytes) else line.encode() for line in lines]
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


def capture_post(monkeypatch, response):
    sent = {}

    def fake_post(url, json=None, headers=None, stream=False, timeout=None):
        sent.update(url=url, body=json, headers=headers or {})
        return response

    monkeypatch.setattr(requests, "post", fake_post)
    return sent


# ---- Ollama ----

def test_ollama_streams_content_until_done(monkeypatch):
    lines = [json.dumps(x) for x in [
        {"message": {"content": "Hel"}, "done": False},
        {"message": {"content": "lo"}, "done": False},
        {"message": {"content": ""}, "done": True},
        {"message": {"content": "ignored"}, "done": False},
    ]]
    response = FakeResponse(lines)
    sent = capture_post(monkeypatch, response)

    pieces = list(OllamaProvider("http://ollama:11434", 30).stream_chat([{"role": "user", "content": "hi"}], "mistral"))

    assert pieces == ["Hel", "lo"]
    assert response.closed
    assert sent["url"] == "http://ollama:11434/api/chat"
    assert sent["body"]["stream"] is True


def test_ollama_reports_its_own_errors(monkeypatch):
    capture_post(monkeypatch, FakeResponse(status=404, body={"error": "model 'nope' not found"}))
    with pytest.raises(llm.LLMError, match="model 'nope' not found"):
        OllamaProvider("http://ollama:11434", 30).stream_chat([], "nope")

    def refuse(*args, **kwargs):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(requests, "post", refuse)
    with pytest.raises(llm.LLMError, match="Is it running"):
        OllamaProvider("http://ollama:11434", 30).stream_chat([], "mistral")


def test_ollama_json_mode_sends_the_schema(monkeypatch):
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    sent = capture_post(monkeypatch, FakeResponse(body={"message": {"content": '{"ok": true}'}}))
    assert OllamaProvider("http://o", 30).complete_json([], "mistral", schema) == {"ok": True}
    assert sent["body"]["format"] == schema


# ---- OpenAI-compatible (Groq) ----

def test_openai_compatible_parses_sse_deltas(monkeypatch):
    lines = [
        ": keep-alive",
        'data: {"choices":[{"delta":{"role":"assistant"}}]}',
        'data: {"choices":[{"delta":{"content":"Hi"}}]}',
        "",
        'data: {"choices":[{"delta":{"content":" there"}}]}',
        "data: [DONE]",
        'data: {"choices":[{"delta":{"content":"ignored"}}]}',
    ]
    sent = capture_post(monkeypatch, FakeResponse(lines))
    provider = OpenAICompatibleProvider("Groq", "https://api.groq.com/openai/v1", "key-123", 30)

    assert list(provider.stream_chat([{"role": "user", "content": "hi"}], "llama-3.1-8b-instant")) == ["Hi", " there"]
    assert sent["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert sent["headers"]["Authorization"] == "Bearer key-123"


def test_openai_compatible_errors(monkeypatch):
    capture_post(monkeypatch, FakeResponse(status=401, body={"error": {"message": "Invalid API Key"}}))
    with pytest.raises(llm.LLMError, match="Invalid API Key"):
        OpenAICompatibleProvider("Groq", "https://x", "bad", 30).stream_chat([], "m")
    with pytest.raises(llm.LLMError, match="No API key"):
        OpenAICompatibleProvider("Groq", "https://x", None, 30).stream_chat([], "m")


def test_openai_compatible_json_mode_tolerates_code_fences(monkeypatch):
    body = {"choices": [{"message": {"content": '```json\n{"cards": []}\n```'}}]}
    sent = capture_post(monkeypatch, FakeResponse(body=body))
    result = OpenAICompatibleProvider("Groq", "https://x", "k", 30).complete_json([], "m", {"type": "object"})
    assert result == {"cards": []}
    assert sent["body"]["response_format"] == {"type": "json_object"}


def test_hosted_model_allow_list():
    provider = OpenAICompatibleProvider("Groq", "https://x", "k", 30, models=["b", "a"])
    assert provider.list_models() == ["a", "b"]


# ---- Fake + selection ----

def test_fake_provider_streams_markdown_and_builds_json():
    provider = FakeProvider(delay=0)
    text = "".join(provider.stream_chat([{"role": "user", "content": "What is a list?"}], "fake-tutor"))
    assert "```python" in text
    assert '"What is a list?"' in text

    schema = {"type": "object", "properties": {"cards": {"type": "array", "minItems": 2, "items": {
        "type": "object", "properties": {"front": {"type": "string"}, "back": {"type": "string"}}}}}}
    assert provider.complete_json([], "fake-tutor", schema) == {
        "cards": [{"front": "Example text", "back": "Example text"}] * 2
    }


@pytest.mark.parametrize("name, cls, model", [
    ("ollama", OllamaProvider, "test-model"),
    ("groq", OpenAICompatibleProvider, "llama-3.1-8b-instant"),
    ("openai", OpenAICompatibleProvider, "gpt-4o-mini"),
    ("fake", FakeProvider, "fake-tutor"),
])
def test_provider_selection(tmp_path, name, cls, model):
    app = create_app(make_config(tmp_path, LLM_PROVIDER=name))
    with app.app_context():
        assert isinstance(llm.get_provider(), cls)
        assert llm.default_model() == model


def test_build_messages_includes_document_excerpts():
    class Turn:
        user_message, bot_response = "q1", "a1"

    messages = build_messages([Turn()], [{"source": "notes.pdf", "text": "BLUE HERON"}], "q2")
    assert "[notes.pdf]\nBLUE HERON" in messages[0]["content"]
    assert messages[1:] == [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
    ]
