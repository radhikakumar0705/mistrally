"""
Contract tests: every response the API gives in a full user journey must match openapi.yaml,
and every route Flask serves must be documented there.
"""
import io
import json
import re
from pathlib import Path

import pytest
import requests
import yaml
from conftest import make_config, read_events
from jsonschema import Draft202012Validator
from openapi_core import OpenAPI
from openapi_core.contrib.werkzeug import WerkzeugOpenAPIRequest, WerkzeugOpenAPIResponse

from app import create_app
from extensions import db
from services import llm

SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"
SPEC = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
OPENAPI = OpenAPI.from_file_path(str(SPEC_PATH))
STREAM_EVENT = Draft202012Validator({"$ref": "#/components/schemas/StreamEvent", "components": SPEC["components"]})

UNDOCUMENTED = {"/", "/docs", "/openapi.yaml", "/static/<path:filename>"}


def check(response):
    """Validate a test-client response (and the request that produced it) against the spec."""
    request = WerkzeugOpenAPIRequest(response.request)
    if response.mimetype != "text/event-stream":
        OPENAPI.validate_response(request, WerkzeugOpenAPIResponse(response))
    else:
        # openapi-core can't parse event streams, so each event is validated against StreamEvent instead
        events = read_events(response)
        assert events, "stream had no events"
        for event in events:
            STREAM_EVENT.validate(event)
    return response


class FakeSandbox:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"stdout": "45\n", "stderr": "", "exit_code": 0, "timed_out": False, "duration_ms": 12}


@pytest.fixture
def api(tmp_path, monkeypatch, ollama):
    app = create_app(make_config(tmp_path, SANDBOX_URL="http://sandbox:8080", SANDBOX_TOKEN="t"))
    with app.app_context():
        db.create_all()
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeSandbox())
    monkeypatch.setattr(llm, "complete_json", lambda messages, model, schema: {
        "title": "Lists",
        "questions": [{"question": "Reverse a list?", "options": ["a", "b", "c", "d"], "answer_index": 0,
                       "explanation": "Because."}],
        "cards": [{"front": "Front", "back": "Back"}],
    })
    return app.test_client()


def test_full_user_journey_matches_the_spec(api):
    check(api.get("/auth/config"))
    check(api.get("/health/live"))
    check(api.get("/health/ready"))

    body = {"username": "contract", "email": "c@example.com", "password": "password123"}
    check(api.post("/auth/register", json=body))
    check(api.post("/auth/register", json=body))  # 409
    check(api.post("/auth/register", json={"username": "x"}))  # 400
    check(api.post("/auth/login", json={"username": "contract", "password": "wrong-password"}))  # 401
    login = check(api.post("/auth/login", json={"username": "contract", "password": "password123"}))
    auth = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    csrf = {"X-CSRF-TOKEN": api.get_cookie("csrf_refresh_token").value}
    check(api.post("/auth/refresh", headers=csrf))
    check(api.get("/auth/profile", headers=auth))
    check(api.get("/auth/profile"))  # 401

    check(api.get("/chat/models", headers=auth))
    session = check(api.post("/chat/sessions", headers=auth, json={"title": "Contract"})).get_json()
    sid = session["id"]
    check(api.get("/chat/sessions", headers=auth))
    check(api.patch(f"/chat/sessions/{sid}", headers=auth, json={"title": "Renamed", "model": None}))
    check(api.patch(f"/chat/sessions/{sid}", headers=auth, json={"title": " "}))  # 400

    notes = b"# Lists\n\nReverse a Python list with items[::-1] to get a reversed copy.\n"
    document = check(api.post("/documents", headers=auth, data={"file": (io.BytesIO(notes), "lists.md")})).get_json()
    check(api.post("/documents", headers=auth, data={"file": (io.BytesIO(b"x"), "bad.exe")}))  # 400
    check(api.get("/documents", headers=auth))
    check(api.get(f"/documents/{document['id']}", headers=auth))

    check(api.post(f"/chat/sessions/{sid}/messages", headers=auth, json={"message": "How do I reverse a list?"}))
    check(api.post(f"/chat/sessions/{sid}/messages", headers=auth, json={"message": ""}))  # 400
    check(api.get(f"/chat/sessions/{sid}/messages", headers=auth))
    check(api.post(f"/chat/sessions/{sid}/regenerate", headers=auth))
    check(api.get("/chat/sessions/999999/messages", headers=auth))  # 404

    check(api.post("/study/quiz", headers=auth, json={"document_id": document["id"], "count": 1}))
    check(api.post("/study/flashcards", headers=auth, json={"topic": "lists", "count": 1}))
    check(api.post("/study/quiz", headers=auth, json={}))  # 400
    check(api.post("/study/run", headers=auth, json={"code": "print(sum(range(10)))"}))
    check(api.post("/study/run", headers=auth, json={"code": ""}))  # 400

    check(api.delete(f"/documents/{document['id']}", headers=auth))
    check(api.delete(f"/chat/sessions/{sid}", headers=auth))
    check(api.post("/auth/logout", headers=csrf))


def test_metrics_endpoint_matches_the_spec(api):
    check(api.get("/metrics"))


def _documented(rule):
    return re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", rule)


def test_every_route_is_documented(app):
    served = {
        (_documented(rule.rule), method.lower())
        for rule in app.url_map.iter_rules()
        if rule.rule not in UNDOCUMENTED
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }
    documented = {
        (path, method)
        for path, item in SPEC["paths"].items()
        for method in item
        if method in {"get", "post", "put", "patch", "delete"}
    }
    assert served - documented == set(), "routes missing from openapi.yaml"
    assert documented - served == set(), "openapi.yaml documents routes that don't exist"


def test_spec_is_served(client):
    response = client.get("/openapi.yaml")
    assert response.status_code == 200
    assert yaml.safe_load(response.data)["info"]["title"] == "Mistrally API"
    assert b"swagger-ui" in client.get("/docs").data


def test_stream_event_schema_rejects_malformed_events():
    assert not STREAM_EVENT.is_valid({"type": "token"})
    assert not STREAM_EVENT.is_valid({"type": "surprise", "content": "x"})
    assert STREAM_EVENT.is_valid(json.loads('{"type": "token", "content": "hi"}'))
