import uuid
from functools import lru_cache

import chromadb
from flask import current_app
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "mistrally_docs"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


@lru_cache(maxsize=1)
def _embedder():
    # Loaded once, on first use, instead of at import time.
    return SentenceTransformer("all-MiniLM-L6-v2")


@lru_cache(maxsize=None)
def _collection_at(path):
    client = chromadb.PersistentClient(path=path)
    return client.get_or_create_collection(COLLECTION_NAME)


def _collection():
    return _collection_at(current_app.config["CHROMA_DB_PATH"])


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks so each embedding covers a focused passage."""
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start:start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks


def add_document(text, user_id, source):
    """
    Chunk, embed and store a document for retrieval-augmented generation (RAG).
    Chunks are tagged with the owner's user_id so users only retrieve their own documents.
    Returns the number of chunks stored.
    """
    chunks = chunk_text(text)
    if not chunks:
        return 0

    embeddings = _embedder().encode(chunks).tolist()
    _collection().add(
        ids=[uuid.uuid4().hex for _ in chunks],
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{"user_id": user_id, "source": source} for _ in chunks],
    )
    return len(chunks)


def retrieve_context(query, user_id, top_k=3):
    """Return the user's most relevant document chunks for a query, or "" if they have none."""
    collection = _collection()
    if collection.count() == 0:
        return ""

    query_embedding = _embedder().encode([query])[0].tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"user_id": user_id},
    )

    documents = results.get("documents") or [[]]
    return "\n---\n".join(documents[0])
