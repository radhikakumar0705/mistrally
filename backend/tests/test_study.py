import io

import pytest
import requests
from conftest import make_config

from app import create_app
from extensions import db
from services import llm, study

VALID_QUIZ = {
    "title": "Python lists",
    "questions": [
        {
            "question": "How do you get a reversed copy of a list?",
            "options": ["items[::-1]", "items.sort()", "items.pop()", "len(items)"],
            "answer_index": 0,
            "explanation": "Slicing with a step of -1 returns a reversed copy.",
        }
    ] * 3,
}


@pytest.fixture
def model_output(monkeypatch):
    """Control what the model returns for JSON completions and record the prompts."""
    state = {"outputs": [VALID_QUIZ], "calls": []}

    def fake_complete_json(messages, model, schema):
        state["calls"].append({"messages": messages, "schema": schema})
        output = state["outputs"].pop(0) if len(state["outputs"]) > 1 else state["outputs"][0]
        if isinstance(output, Exception):
            raise output
        return output

    monkeypatch.setattr(llm, "complete_json", fake_complete_json)
    return state


def test_quiz_from_topic(client, auth, model_output):
    response = client.post("/study/quiz", headers=auth, json={"topic": "Python lists", "count": 2, "difficulty": "easy"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["kind"] == "quiz"
    assert data["source"] == "Python lists"
    assert len(data["questions"]) == 2  # trimmed to the requested count
    assert data["questions"][0]["options"][data["questions"][0]["answer_index"]] == "items[::-1]"

    call = model_output["calls"][0]
    assert "easy multiple-choice quiz with exactly 2 questions" in call["messages"][1]["content"]
    assert "$defs" not in str(call["schema"])  # references are inlined for every provider


def test_quiz_from_document_uses_its_text(client, auth, model_output):
    notes = b"# Joins\n\nA left join keeps every row from the left table and fills missing matches with NULL.\n"
    document = client.post("/documents", headers=auth, data={"file": (io.BytesIO(notes), "joins.md")}).get_json()

    response = client.post("/study/quiz", headers=auth, json={"document_id": document["id"]})
    assert response.status_code == 200
    assert response.get_json()["source"] == "joins.md"
    assert "fills missing matches with NULL" in model_output["calls"][0]["messages"][1]["content"]


def test_invalid_output_is_retried_then_rejected(client, auth, model_output):
    duplicate_options = {**VALID_QUIZ["questions"][0], "options": ["a", "a", "b", "c"]}
    model_output["outputs"] = [{"title": "x", "questions": [duplicate_options]}, VALID_QUIZ]
    assert client.post("/study/quiz", headers=auth, json={"topic": "x"}).status_code == 200
    assert len(model_output["calls"]) == 2

    model_output["outputs"] = [{"title": "x", "questions": []}]
    response = client.post("/study/quiz", headers=auth, json={"topic": "x"})
    assert response.status_code == 502
    assert "invalid" in response.get_json()["error"]


def test_model_outage_is_reported(client, auth, model_output):
    model_output["outputs"] = [llm.LLMError("Could not connect to Ollama. Is it running?")]
    response = client.post("/study/flashcards", headers=auth, json={"topic": "git"})
    assert response.status_code == 502
    assert "unavailable" in response.get_json()["error"]


def test_flashcards_with_the_fake_provider(tmp_path):
    app = create_app(make_config(tmp_path, LLM_PROVIDER="fake"))
    with app.app_context():
        db.create_all()
        deck = study.generate("flashcards", count=2, topic="git")
        quiz = study.generate("quiz", count=3, topic="git")
    assert len(deck["cards"]) == 2
    assert len(set(quiz["questions"][0]["options"])) == 4


@pytest.mark.parametrize("body, message", [
    ({}, "Choose a document or enter a topic"),
    ({"topic": "x", "count": 0}, "between 1 and 10"),
    ({"topic": "x", "difficulty": "impossible"}, "difficulty"),
    ({"document_id": "nope"}, "not found"),
])
def test_study_validation(client, auth, body, message):
    response = client.post("/study/quiz", headers=auth, json=body)
    assert response.status_code in (400, 404)
    assert message in response.get_json()["error"]


def test_unknown_kind(client, auth):
    assert client.post("/study/essay", headers=auth, json={"topic": "x"}).status_code == 404


# ---- Code runner ----

class FakeSandboxResponse:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)

    def json(self):
        return self.body


@pytest.fixture
def sandbox_client(tmp_path, monkeypatch):
    app = create_app(make_config(tmp_path, SANDBOX_URL="http://sandbox:8080", SANDBOX_TOKEN="s3cret"))
    with app.app_context():
        db.create_all()
    client = app.test_client()
    client.post("/auth/register", json={"username": "u", "email": "u@x.io", "password": "password123"})
    token = client.post("/auth/login", json={"username": "u", "password": "password123"}).get_json()["access_token"]
    sent = {}

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, json=json, headers=headers)
        return FakeSandboxResponse({"stdout": "45\n", "stderr": "", "exit_code": 0, "timed_out": False})

    monkeypatch.setattr(requests, "post", fake_post)
    return client, {"Authorization": f"Bearer {token}"}, sent


def test_run_code_proxies_to_the_sandbox(sandbox_client):
    client, auth, sent = sandbox_client
    response = client.post("/study/run", headers=auth, json={"code": "print(sum(range(10)))"})
    assert response.status_code == 200
    assert response.get_json()["stdout"] == "45\n"
    assert sent["url"] == "http://sandbox:8080/run"
    assert sent["headers"]["Authorization"] == "Bearer s3cret"
    assert client.get("/auth/config").get_json()["sandbox"] is True


def test_run_code_validation(sandbox_client):
    client, auth, _ = sandbox_client
    assert client.post("/study/run", headers=auth, json={"code": "  "}).status_code == 400
    assert client.post("/study/run", headers=auth, json={"code": "x" * 20_001}).status_code == 400
    assert client.post("/study/run", headers=auth, json={"code": "ls", "language": "bash"}).status_code == 400
    assert client.post("/study/run", json={"code": "print(1)"}).status_code == 401


def test_run_code_disabled_without_sandbox(client, auth):
    assert client.post("/study/run", headers=auth, json={"code": "print(1)"}).status_code == 404
