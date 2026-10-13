import io

import pytest
from conftest import make_config

from app import create_app
from extensions import db
from services import retrieval

DOCS = {
    "errors.md": (
        "# Error codes\n\n"
        "Error E4417 means the payment gateway rejected the card because the CVV was wrong.\n\n"
        "# Retries\n\nRetry failed webhooks with exponential backoff, starting at 2 seconds.\n"
    ),
    "python.md": (
        "# Lists\n\nReverse a Python list in place with list.reverse(), or get a reversed copy with slicing.\n\n"
        "# Dictionaries\n\nA dictionary maps keys to values and looks keys up in constant time on average.\n"
    ),
}


@pytest.fixture
def indexed(tmp_path):
    """An app with two documents uploaded by user 1."""
    app = create_app(make_config(tmp_path))
    with app.app_context():
        db.create_all()
    client = app.test_client()
    client.post("/auth/register", json={"username": "u", "email": "u@x.io", "password": "password123"})
    token = client.post("/auth/login", json={"username": "u", "password": "password123"}).get_json()["access_token"]
    for name, text in DOCS.items():
        client.post("/documents", headers={"Authorization": f"Bearer {token}"},
                    data={"file": (io.BytesIO(text.encode()), name)})
    return app


def search(app, query, **overrides):
    with app.app_context():
        config = {**app.config, **overrides}
        return retrieval.retrieve(query, 1, config)


def test_hybrid_rerank_finds_the_right_section(indexed):
    results = search(indexed, "How do I reverse a list?")
    assert results[0]["source"] == "python.md"
    assert results[0]["section"] == "Lists"


def test_keyword_search_finds_exact_codes(indexed):
    # Embeddings blur rare identifiers; BM25 matches them exactly
    results = search(indexed, "E4417", RAG_RERANK=False)
    assert results and results[0]["section"] == "Error codes"


def test_reranker_drops_unrelated_questions(indexed):
    assert search(indexed, "What is the capital of Australia?") == []
    assert search(indexed, "Best pizza toppings?") == []


def test_dense_mode_without_rerank_is_the_baseline(indexed):
    results = search(indexed, "How do I reverse a list?", RAG_MODE="dense", RAG_RERANK=False)
    assert results[0]["source"] == "python.md"
    assert all(r["score"] > 0 for r in results)


def test_tokenizer_drops_stopwords():
    assert retrieval.tokenize("How do I use the C++ map in C#?") == ["c++", "map", "c#"]
