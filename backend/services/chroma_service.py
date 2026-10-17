"""ChromaDB access: storing document chunks and fetching candidates for retrieval."""
from functools import cache, lru_cache

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from flask import current_app

COLLECTION_NAME = "mistrally_docs"


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


def add_chunks(document, chunks, start_index=0):
    """Embed and store a batch of a document's chunks. Chunks carry the owner's user_id for filtering."""
    metadatas = []
    for i, chunk in enumerate(chunks):
        metadata = {
            "user_id": document.user_id,
            "doc_id": document.id,
            "source": document.filename,
            "chunk": start_index + i,
        }
        if chunk.get("page") is not None:
            metadata["page"] = chunk["page"]
        if chunk.get("section"):
            metadata["section"] = chunk["section"][:200]
        metadatas.append(metadata)

    _collection().add(
        ids=[f"{document.id}-{start_index + i}" for i in range(len(chunks))],
        documents=[c["text"] for c in chunks],
        metadatas=metadatas,
    )


def delete_document_chunks(doc_id):
    _collection().delete(where={"doc_id": doc_id})


def delete_chunks_by_source(user_id, source):
    """Chunks stored before documents had ids are identified by owner and file name."""
    _collection().delete(where={"$and": [{"user_id": user_id}, {"source": source}]})


def dense_search(query, user_id, n_results):
    """Nearest chunks by embedding similarity: [{"id", "text", "metadata", "distance"}]."""
    collection = _collection()
    if collection.count() == 0:
        return []
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where={"user_id": user_id},
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"id": chunk_id, "text": text, "metadata": metadata, "distance": distance}
        for chunk_id, text, metadata, distance in zip(
            results["ids"][0], results["documents"][0], results["metadatas"][0], results["distances"][0],
            strict=False,
        )
    ]


def document_text(doc_id):
    """A document's chunks in order, joined (used as study material for quizzes and flashcards)."""
    result = _collection().get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
    ordered = sorted(
        zip(result["metadatas"], result["documents"], strict=False), key=lambda pair: pair[0].get("chunk", 0)
    )
    return "\n\n".join(text for _metadata, text in ordered)


def user_chunks(user_id):
    """Every chunk the user owns, for keyword (BM25) search: (ids, texts, metadatas)."""
    result = _collection().get(where={"user_id": user_id}, include=["documents", "metadatas"])
    return result["ids"], result["documents"], result["metadatas"]


def legacy_documents(user_id):
    """Documents present in Chroma, grouped by doc_id (or file name for chunks from older versions)."""
    _ids, _texts, metadatas = user_chunks(user_id)
    documents = {}
    for metadata in metadatas:
        doc_id = metadata.get("doc_id") or f"legacy-{metadata.get('source', 'unknown')}"
        doc = documents.setdefault(doc_id, {"id": doc_id, "filename": metadata.get("source", "unknown"), "chunks": 0})
        doc["chunks"] += 1
    return list(documents.values())
