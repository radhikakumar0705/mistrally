import chromadb
from sentence_transformers import SentenceTransformer

# Persistent vector DB in ./data/chroma
chroma_client = chromadb.PersistentClient(path="./data/chroma")
collection = chroma_client.get_or_create_collection("mistrally_docs")

# Embedding model (fast + lightweight)
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def add_document(doc_text: str, doc_id: str):
    """
    Add a document (or chunk) to Chroma for retrieval-augmented generation (RAG).
    """
    embedding = embedder.encode([doc_text])[0].tolist()
    collection.add(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[doc_text]
    )

def retrieve_context(query: str, top_k: int = 3) -> str:
    """
    Retrieve the most relevant text chunks based on semantic similarity.
    """
    query_embedding = embedder.encode([query])[0].tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    if not results["documents"] or not results["documents"][0]:
        return ""

    # Concatenate top retrieved contexts
    return "\n".join(results["documents"][0])
