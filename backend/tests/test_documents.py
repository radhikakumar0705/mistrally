import io

import fakeredis
import pytest
from conftest import read_events, register_and_login
from pdf_helper import make_pdf
from rq import Queue

from services import tasks

NOTES = b"The secret project codename is BLUE HERON. It launches in March. " * 5


def upload(client, auth, content=NOTES, filename="notes.txt"):
    return client.post("/documents", headers=auth, data={"file": (io.BytesIO(content), filename)})


def ask(client, auth, question):
    session_id = client.post("/chat/sessions", headers=auth, json={}).get_json()["id"]
    return read_events(client.post(f"/chat/sessions/{session_id}/messages", headers=auth, json={"message": question}))


def test_upload_is_processed_inline_without_a_queue(client, auth):
    response = upload(client, auth)
    assert response.status_code == 201
    document = response.get_json()
    assert document["filename"] == "notes.txt"
    assert document["status"] == "ready"
    assert document["progress"] == 100
    assert document["chunks"] == 1

    assert [d["id"] for d in client.get("/documents", headers=auth).get_json()] == [document["id"]]
    assert client.get(f"/documents/{document['id']}", headers=auth).get_json()["status"] == "ready"


def test_delete_removes_record_and_chunks(client, auth, ollama):
    document = upload(client, auth).get_json()
    deleted = client.delete(f"/documents/{document['id']}", headers=auth)
    assert deleted.status_code == 204
    assert client.get("/documents", headers=auth).get_json() == []
    deleted_again = client.delete(f"/documents/{document['id']}", headers=auth)
    assert deleted_again.status_code == 404
    assert ask(client, auth, "What is the secret project codename?")[0]["sources"] == []


def test_upload_rejects_bad_files(client, auth):
    assert upload(client, auth, filename="virus.exe").status_code == 400
    assert upload(client, auth, content=b"   ").status_code == 422
    assert client.post("/documents", headers=auth).status_code == 400


def test_unreadable_pdf_is_marked_failed(client, auth):
    response = upload(client, auth, content=b"%PDF-1.4 definitely not a pdf", filename="broken.pdf")
    assert response.status_code == 422
    assert response.get_json()["status"] == "failed"
    assert response.get_json()["error"] == "Could not read that PDF"
    listed = client.get("/documents", headers=auth).get_json()
    assert listed[0]["status"] == "failed"


def test_markdown_upload_is_supported(client, auth, ollama):
    markdown = b"# Deployment guide\n\nAlways run the smoke tests with `make verify-release` before tagging.\n"
    assert upload(client, auth, content=markdown, filename="guide.md").status_code == 201
    events = ask(client, auth, "Which command runs the smoke tests before a release?")
    assert events[0]["sources"] == [{"document": "guide.md", "page": None}]


def test_pdf_answers_cite_the_page(client, auth, ollama):
    pdf = make_pdf([
        "Course logistics\nLectures are on Mondays in room 101.\nOffice hours are on Fridays.",
        "Final project\nThe final project is a terminal Snake game written in Rust.\nIt is due on December 12.",
    ])
    document = upload(client, auth, content=pdf, filename="syllabus.pdf").get_json()
    assert document["pages"] == 2

    events = ask(client, auth, "When is the final project due and what language is it in?")
    assert events[0]["sources"][0] == {"document": "syllabus.pdf", "page": 2}
    system_prompt = ollama.calls[-1]["messages"][0]["content"]
    assert "[syllabus.pdf, page 2]" in system_prompt
    assert events[-1]["message"]["sources"][0]["page"] == 2


def test_unrelated_questions_get_no_document_context(client, auth, ollama):
    upload(client, auth)
    events = ask(client, auth, "How do I reverse a linked list in C?")
    assert events[0]["sources"] == []


def test_documents_are_private(client, auth, ollama):
    document = upload(client, auth).get_json()
    bob = register_and_login(client, "bob")

    assert client.get("/documents", headers=bob).get_json() == []
    assert client.get(f"/documents/{document['id']}", headers=bob).status_code == 404
    foreign_delete = client.delete(f"/documents/{document['id']}", headers=bob)
    assert foreign_delete.status_code == 404

    events = ask(client, bob, "What is the secret project codename?")
    assert events[0]["sources"] == []
    assert "BLUE HERON" not in ollama.calls[-1]["messages"][0]["content"]


@pytest.fixture
def queue(monkeypatch):
    """An in-memory Redis queue that runs jobs immediately, exercising the enqueue path."""
    q = Queue(tasks.QUEUE_NAME, connection=fakeredis.FakeStrictRedis(), is_async=False)
    monkeypatch.setattr(tasks, "get_queue", lambda: q)
    return q


def test_upload_through_the_queue(client, auth, ollama, queue):
    response = upload(client, auth)
    assert response.status_code == 202
    job = queue.fetch_job(f"ingest-{response.get_json()['id']}")
    assert job.is_finished

    document = client.get(f"/documents/{response.get_json()['id']}", headers=auth).get_json()
    assert document["status"] == "ready"
    assert ask(client, auth, "What is the secret project codename?")[0]["sources"][0]["document"] == "notes.txt"


def test_queue_outage_marks_the_document_failed(client, auth, monkeypatch):
    def unavailable(doc_id, data):
        raise ConnectionError("redis down")

    monkeypatch.setattr(tasks, "submit_ingestion", unavailable)
    response = upload(client, auth)
    assert response.status_code == 503
    assert response.get_json()["status"] == "failed"
