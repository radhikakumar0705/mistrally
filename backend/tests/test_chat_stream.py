from conftest import read_events


def new_session(client, auth, **body):
    return client.post("/chat/sessions", headers=auth, json=body).get_json()["id"]


def send(client, auth, session_id, message):
    return client.post(f"/chat/sessions/{session_id}/messages", headers=auth, json={"message": message})


def test_reply_is_streamed_and_saved(client, auth, ollama):
    session_id = new_session(client, auth)
    response = send(client, auth, session_id, "Explain recursion")

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    events = read_events(response)
    assert events[0] == {"type": "start", "sources": [], "model": "test-model"}
    assert [e["content"] for e in events if e["type"] == "token"] == ["Hello", " there", "!"]
    done = events[-1]
    assert done["type"] == "done"
    assert done["message"]["bot_response"] == "Hello there!"
    assert done["session"]["title"] == "Explain recursion"

    history = client.get(f"/chat/sessions/{session_id}/messages", headers=auth).get_json()
    assert [(m["user_message"], m["bot_response"]) for m in history] == [("Explain recursion", "Hello there!")]


def test_previous_turns_and_session_model_are_sent(client, auth, ollama):
    session_id = new_session(client, auth, model="llama3.2:latest")
    read_events(send(client, auth, session_id, "first question"))
    read_events(send(client, auth, session_id, "second question"))

    call = ollama.calls[-1]
    assert call["model"] == "llama3.2:latest"
    roles = [(m["role"], m["content"]) for m in call["messages"][1:]]
    assert roles == [("user", "first question"), ("assistant", "Hello there!"), ("user", "second question")]


def test_message_validation(client, auth, ollama):
    session_id = new_session(client, auth)
    assert send(client, auth, session_id, "   ").status_code == 400
    assert send(client, auth, session_id, "x" * 8001).status_code == 400
    assert send(client, auth, 9999, "hello").status_code == 404


def test_model_unavailable_returns_502(client, auth, ollama):
    ollama.fail_to_start = "Could not connect to Ollama. Is it running?"
    response = send(client, auth, new_session(client, auth), "hello")
    assert response.status_code == 502
    assert "Is it running?" in response.get_json()["error"]


def test_error_mid_stream_keeps_partial_reply(client, auth, ollama):
    ollama.fail_mid_stream = "model crashed"
    session_id = new_session(client, auth)
    events = read_events(send(client, auth, session_id, "hello"))

    assert {"type": "error", "error": "model crashed"} in events
    assert events[-1]["message"]["bot_response"] == "Hello"


def test_stopping_the_stream_saves_partial_reply(client, auth, ollama):
    session_id = new_session(client, auth)
    response = client.post(f"/chat/sessions/{session_id}/messages", headers=auth,
                           json={"message": "hello"}, buffered=False)
    stream = iter(response.response)
    next(stream)  # start event
    next(stream)  # first token
    response.close()  # what the server sees when the user presses Stop

    history = client.get(f"/chat/sessions/{session_id}/messages", headers=auth).get_json()
    assert [m["bot_response"] for m in history] == ["Hello"]


def test_regenerate_replaces_last_answer(client, auth, ollama):
    session_id = new_session(client, auth)
    read_events(send(client, auth, session_id, "first"))
    read_events(send(client, auth, session_id, "second"))

    ollama.reply = ["A better", " answer"]
    events = read_events(client.post(f"/chat/sessions/{session_id}/regenerate", headers=auth))
    assert events[-1]["message"]["bot_response"] == "A better answer"
    assert ollama.calls[-1]["messages"][-1] == {"role": "user", "content": "second"}

    history = client.get(f"/chat/sessions/{session_id}/messages", headers=auth).get_json()
    assert [(m["user_message"], m["bot_response"]) for m in history] == [
        ("first", "Hello there!"),
        ("second", "A better answer"),
    ]


def test_regenerate_needs_a_message(client, auth, ollama):
    response = client.post(f"/chat/sessions/{new_session(client, auth)}/regenerate", headers=auth)
    assert response.status_code == 400
