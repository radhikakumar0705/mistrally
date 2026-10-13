import io
import json
import logging

from conftest import read_events

import observability


def metric(client, name, **labels):
    """Read one sample from the /metrics endpoint."""
    for line in client.get("/metrics").get_data(as_text=True).splitlines():
        if not line.startswith(name):
            continue
        head, _, value = line.rpartition(" ")
        if all(f'{k}="{v}"' in head for k, v in labels.items()):
            return float(value)
    return 0.0


def test_request_id_is_echoed_or_generated(client):
    response = client.get("/", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"

    generated = client.get("/").headers["X-Request-ID"]
    assert len(generated) == 32

    # Unsafe values are replaced rather than reflected into logs and headers
    unsafe = "<script>alert(1)</script>"
    assert client.get("/", headers={"X-Request-ID": unsafe}).headers["X-Request-ID"] != unsafe


def test_streamed_answer_records_llm_metrics(client, auth, ollama):
    before_ttft = metric(client, "mistrally_llm_time_to_first_token_seconds_count", model="test-model")
    before_done = metric(client, "mistrally_llm_streams_total", model="test-model", outcome="completed")
    before_chunks = metric(client, "mistrally_llm_stream_chunks_total", model="test-model")

    session_id = client.post("/chat/sessions", headers=auth, json={}).get_json()["id"]
    read_events(client.post(f"/chat/sessions/{session_id}/messages", headers=auth, json={"message": "hi"}))

    assert metric(client, "mistrally_llm_time_to_first_token_seconds_count", model="test-model") == before_ttft + 1
    assert metric(client, "mistrally_llm_streams_total", model="test-model", outcome="completed") == before_done + 1
    assert metric(client, "mistrally_llm_stream_chunks_total", model="test-model") == before_chunks + 3


def test_unavailable_model_is_counted(client, auth, ollama):
    ollama.fail_to_start = "down"
    before = metric(client, "mistrally_llm_streams_total", outcome="unavailable")
    session_id = client.post("/chat/sessions", headers=auth, json={}).get_json()["id"]
    client.post(f"/chat/sessions/{session_id}/messages", headers=auth, json={"message": "hi"})
    assert metric(client, "mistrally_llm_streams_total", outcome="unavailable") == before + 1


def test_http_metrics_use_route_templates(client, auth):
    client.get("/chat/sessions/12345/messages", headers=auth)
    text = client.get("/metrics").get_data(as_text=True)
    assert 'endpoint="/chat/sessions/<int:session_id>/messages"' in text
    assert "12345" not in text  # ids would explode label cardinality


def test_json_logs_include_request_id(app):
    stream = io.StringIO()
    observability.configure_logging("INFO", "json")
    logging.getLogger().handlers[0].stream = stream

    with app.test_request_context("/"):
        app.preprocess_request()
        logging.getLogger("mistrally.test").info("hello", extra={"user_id": 7})

    line = json.loads(stream.getvalue().strip().splitlines()[-1])
    assert line["message"] == "hello"
    assert line["level"] == "INFO"
    assert line["user_id"] == 7
    assert len(line["request_id"]) == 32
    observability.configure_logging("INFO", "text")
