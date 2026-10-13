import uuid
from datetime import UTC, datetime
from functools import cache, lru_cache

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from flask import current_app

COLLECTION_NAME = "mistrally_docs"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


@lru_cache(maxsize=1)
def _embedding_function():
    # all-MiniLM-L6-v2 run with ONNX Runtime: same model as sentence-transformers, no PyTorch needed
    return DefaultEmbeddingFunction()


@cache
def _collection_for(host, port, path):
    if host:
        client = chromadb.HttpClient(host=host, port=port)
    else:
        client = chromadb.PersistentClient(path=path)
    return client.get_or_create_collection(COLLECTION_NAME, embedding_function=_embedding_function())


def _collection():
    config = current_app.config
    return _collection_for(config["CHROMA_HOST"], config["CHROMA_PORT"], config["CHROMA_DB_PATH"])


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


def add_document(text, user_id, filename):
    """
    Chunk, embed and store a document for retrieval-augmented generation (RAG).
    Chunks are tagged with the owner's user_id so users only retrieve their own documents.
    Returns the new document's summary, or None if it had no text.
    """
    chunks = chunk_text(text)
    if not chunks:
        return None

    doc_id = uuid.uuid4().hex
    uploaded_at = datetime.now(UTC).isoformat()
    _collection().add(
        ids=[f"{doc_id}-{i}" for i in range(len(chunks))],
        documents=chunks,
        metadatas=[
            {"user_id": user_id, "doc_id": doc_id, "source": filename, "chunk": i, "uploaded_at": uploaded_at}
            for i in range(len(chunks))
        ],
    )
    return {"id": doc_id, "filename": filename, "chunks": len(chunks), "uploaded_at": uploaded_at}


def _doc_id(metadata):
    # Chunks stored before documents had ids are grouped by file name
    return metadata.get("doc_id") or f"legacy-{metadata.get('source', 'unknown')}"


def list_documents(user_id):
    result = _collection().get(where={"user_id": user_id}, include=["metadatas"])
    documents = {}
    for metadata in result["metadatas"]:
        doc_id = _doc_id(metadata)
        doc = documents.setdefault(doc_id, {
            "id": doc_id,
            "filename": metadata.get("source", "unknown"),
            "chunks": 0,
            "uploaded_at": metadata.get("uploaded_at"),
        })
        doc["chunks"] += 1
    return sorted(documents.values(), key=lambda d: d["uploaded_at"] or "", reverse=True)


def delete_document(user_id, doc_id):
    """Delete one of the user's documents. Returns False if they have no such document."""
    collection = _collection()
    result = collection.get(where={"user_id": user_id}, include=["metadatas"])
    ids = [chunk_id for chunk_id, metadata in zip(result["ids"], result["metadatas"], strict=False)
           if _doc_id(metadata) == doc_id]
    if not ids:
        return False
    collection.delete(ids=ids)
    return True


def retrieve(query, user_id):
    """The user's document chunks most relevant to the query, as [{"text", "source"}]."""
    config = current_app.config
    collection = _collection()
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=config["RAG_TOP_K"],
        where={"user_id": user_id},
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"text": text, "source": metadata.get("source", "unknown")}
        for text, metadata, distance in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0], strict=False
        )
        if distance <= config["RAG_MAX_DISTANCE"]
    ]
