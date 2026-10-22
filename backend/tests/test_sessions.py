from conftest import read_events, register_and_login


def test_session_lifecycle(client, auth):
    created = client.post("/chat/sessions", headers=auth, json={})
    assert created.status_code == 201
    session = created.get_json()
    assert session["title"] == "New Chat"
    assert session["model"] is None

    renamed = client.patch(f"/chat/sessions/{session['id']}", headers=auth,
                           json={"title": "Recursion help", "model": "llama3.2:latest"})
    assert renamed.status_code == 200
    assert renamed.get_json()["title"] == "Recursion help"
    assert renamed.get_json()["model"] == "llama3.2:latest"

    assert client.patch(f"/chat/sessions/{session['id']}", headers=auth, json={"title": "  "}).status_code == 400

    assert [s["id"] for s in client.get("/chat/sessions", headers=auth).get_json()] == [session["id"]]
    deleted = client.delete(f"/chat/sessions/{session['id']}", headers=auth)
    assert deleted.status_code == 204
    assert client.get("/chat/sessions", headers=auth).get_json() == []


def test_sessions_are_private(client, auth):
    session = client.post("/chat/sessions", headers=auth, json={}).get_json()
    bob = register_and_login(client, "bob")

    assert client.get("/chat/sessions", headers=bob).get_json() == []
    for method, path in [
        ("get", f"/chat/sessions/{session['id']}/messages"),
        ("post", f"/chat/sessions/{session['id']}/messages"),
        ("patch", f"/chat/sessions/{session['id']}"),
        ("delete", f"/chat/sessions/{session['id']}"),
    ]:
        response = getattr(client, method)(path, headers=bob, json={"message": "hi", "title": "x"})
        assert response.status_code == 404, (method, path)


def test_sessions_ordered_by_latest_activity(client, auth, ollama):
    first = client.post("/chat/sessions", headers=auth, json={}).get_json()
    second = client.post("/chat/sessions", headers=auth, json={}).get_json()
    assert [s["id"] for s in client.get("/chat/sessions", headers=auth).get_json()] == [second["id"], first["id"]]

    read_events(client.post(f"/chat/sessions/{first['id']}/messages", headers=auth, json={"message": "hi"}))
    assert [s["id"] for s in client.get("/chat/sessions", headers=auth).get_json()] == [first["id"], second["id"]]


def test_list_models(client, auth, ollama):
    data = client.get("/chat/models", headers=auth).get_json()
    assert data == {"models": ["mistral:latest", "llama3.2:latest"], "default": "test-model", "provider": "ollama"}
