import io

from conftest import read_events, register_and_login

NOTES = b"The secret project codename is BLUE HERON. It launches in March. " * 5


def upload(client, auth, content=NOTES, filename="notes.txt"):
    return client.post("/documents", headers=auth, data={"file": (io.BytesIO(content), filename)})


def test_upload_list_and_delete(client, auth):
    response = upload(client, auth)
    assert response.status_code == 201
    document = response.get_json()
    assert document["filename"] == "notes.txt"
    assert document["chunks"] == 1

    listed = client.get("/documents", headers=auth).get_json()
    assert [d["id"] for d in listed] == [document["id"]]

    assert client.delete(f"/documents/{document['id']}", headers=auth).status_code == 204
    assert client.get("/documents", headers=auth).get_json() == []
    assert client.delete(f"/documents/{document['id']}", headers=auth).status_code == 404


def test_upload_rejects_bad_files(client, auth):
    assert upload(client, auth, filename="virus.exe").status_code == 400
    assert upload(client, auth, content=b"   ").status_code == 422
    assert client.post("/documents", headers=auth).status_code == 400


def test_relevant_chunks_reach_the_model_with_sources(client, auth, ollama):
    upload(client, auth)
    session_id = client.post("/chat/sessions", headers=auth, json={}).get_json()["id"]

    events = read_events(client.post(f"/chat/sessions/{session_id}/messages", headers=auth,
                                     json={"message": "What is the secret project codename?"}))
    assert events[0]["sources"] == ["notes.txt"]
    assert "BLUE HERON" in ollama.calls[-1]["messages"][0]["content"]
    assert events[-1]["message"]["sources"] == ["notes.txt"]


def test_unrelated_questions_get_no_document_context(client, auth, ollama):
    upload(client, auth)
    session_id = client.post("/chat/sessions", headers=auth, json={}).get_json()["id"]

    events = read_events(client.post(f"/chat/sessions/{session_id}/messages", headers=auth,
                                     json={"message": "How do I reverse a linked list in C?"}))
    assert events[0]["sources"] == []


def test_documents_are_private(client, auth, ollama):
    document = upload(client, auth).get_json()
    bob = register_and_login(client, "bob")

    assert client.get("/documents", headers=bob).get_json() == []
    assert client.delete(f"/documents/{document['id']}", headers=bob).status_code == 404

    session_id = client.post("/chat/sessions", headers=bob, json={}).get_json()["id"]
    events = read_events(client.post(f"/chat/sessions/{session_id}/messages", headers=bob,
                                     json={"message": "What is the secret project codename?"}))
    assert events[0]["sources"] == []
    assert "BLUE HERON" not in ollama.calls[-1]["messages"][0]["content"]
