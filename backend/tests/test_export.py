"""
Conversation export to Markdown. Written before the implementation (TDD): these tests define the
feature, and the first commit containing them fails.
"""
import json
from datetime import datetime
from types import SimpleNamespace

from conftest import read_events, register_and_login

from services.export import export_filename, to_markdown


def turn(question, answer, sources=None, at="2026-10-22T09:30:00"):
    return SimpleNamespace(
        user_message=question,
        bot_response=answer,
        sources=json.dumps(sources) if sources else None,
        timestamp=datetime.fromisoformat(at),
    )


# ---- The formatter (pure function) ----

def test_markdown_has_title_and_alternating_turns():
    session = SimpleNamespace(title="Recursion help", model="mistral")
    markdown = to_markdown(session, [turn("What is recursion?", "A function calling itself.")])

    lines = markdown.splitlines()
    assert lines[0] == "# Recursion help"
    assert "**You:**" in markdown
    assert "What is recursion?" in markdown
    assert "**Mistrally:**" in markdown
    assert "A function calling itself." in markdown
    assert markdown.index("**You:**") < markdown.index("**Mistrally:**")


def test_sources_are_listed_with_pages():
    session = SimpleNamespace(title="Notes", model=None)
    markdown = to_markdown(session, [
        turn("When is it due?", "December 12.", sources=[{"document": "syllabus.pdf", "page": 2}, {"document": "notes.md", "page": None}]),
    ])
    assert "Sources: syllabus.pdf (p. 2), notes.md" in markdown


def test_answers_saved_by_older_versions_with_plain_source_names_still_export():
    session = SimpleNamespace(title="Old chat", model=None)
    markdown = to_markdown(session, [turn("q", "a", sources=["legacy.txt"])])
    assert "Sources: legacy.txt" in markdown


def test_empty_conversation():
    markdown = to_markdown(SimpleNamespace(title="New Chat", model=None), [])
    assert "_No messages yet._" in markdown


def test_title_cannot_inject_markdown_structure():
    session = SimpleNamespace(title="Evil\n## Injected heading", model=None)
    first_line, rest = to_markdown(session, []).split("\n", 1)
    assert first_line == "# Evil ## Injected heading"
    assert "\n## Injected heading" not in rest


def test_code_in_answers_is_kept_verbatim():
    answer = "Use this:\n\n```python\nprint('hi')\n```"
    markdown = to_markdown(SimpleNamespace(title="Code", model=None), [turn("q", answer)])
    assert "```python\nprint('hi')\n```" in markdown


def test_export_filename_is_a_safe_slug():
    assert export_filename("Recursion help!") == "recursion-help.md"
    assert export_filename("  ../../etc/passwd  ") == "etc-passwd.md"
    assert export_filename("???") == "conversation.md"
    assert len(export_filename("x" * 300)) <= 83


# ---- The endpoint ----

def test_export_endpoint_downloads_markdown(client, auth, ollama):
    session_id = client.post("/chat/sessions", headers=auth, json={"title": "Recursion help"}).get_json()["id"]
    read_events(client.post(f"/chat/sessions/{session_id}/messages", headers=auth, json={"message": "Explain recursion"}))

    response = client.get(f"/chat/sessions/{session_id}/export", headers=auth)

    assert response.status_code == 200
    assert response.mimetype == "text/markdown"
    assert response.headers["Content-Disposition"] == 'attachment; filename="recursion-help.md"'
    body = response.get_data(as_text=True)
    assert body.startswith("# Recursion help")
    assert "Explain recursion" in body
    assert "Hello there!" in body


def test_export_is_private(client, auth):
    session_id = client.post("/chat/sessions", headers=auth, json={}).get_json()["id"]
    bob = register_and_login(client, "bob")
    assert client.get(f"/chat/sessions/{session_id}/export", headers=bob).status_code == 404
    assert client.get(f"/chat/sessions/{session_id}/export").status_code == 401
