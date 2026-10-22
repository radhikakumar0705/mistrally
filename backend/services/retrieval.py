"""
Retrieval for RAG: find the user's document chunks that help answer a question.

Pipeline (RAG_MODE=hybrid, the default):
  1. Dense candidates: embedding similarity from Chroma
  2. Sparse candidates: BM25 keyword scores over the user's chunks (catches exact terms, names, codes)
  3. Reciprocal Rank Fusion merges both rankings
  4. A small cross-encoder (FlashRank, ONNX) re-scores the top candidates against the question and
     drops anything below RAG_MIN_RERANK_SCORE, so unrelated questions get no context at all
RAG_MODE=dense with RAG_RERANK=false reproduces the original embedding-only behaviour (the eval baseline).
"""
import re
import threading
from functools import lru_cache

from flask import current_app
from rank_bm25 import BM25Okapi

from services import chroma_service

RRF_K = 60

_TOKEN = re.compile(r"[a-z0-9_+#]+")
_STOPWORDS = set(
    "a an and are as at be but by can do does for from how i if in into is it its me my of on or our "
    "should so than that the their them then there these this to was what when where which who why "
    "will with would you your about any all also been being could did have has just more most not "
    "only other some such very we use used using".split()
)


def tokenize(text):
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


# ---- BM25 over the user's chunks (cached until their set of chunks changes) ----

_bm25_cache = {}
_bm25_lock = threading.Lock()


def _bm25_index(user_id):
    ids, texts, metadatas = chroma_service.user_chunks(user_id)
    if not ids:
        return None
    signature = hash(tuple(ids))
    with _bm25_lock:
        cached = _bm25_cache.get(user_id)
        if cached and cached[0] == signature:
            return cached[1]
        index = (BM25Okapi([tokenize(t) for t in texts]), ids, texts, metadatas)
        _bm25_cache[user_id] = (signature, index)
        return index


def _sparse_search(query, user_id, n_results):
    index = _bm25_index(user_id)
    tokens = tokenize(query)
    if index is None or not tokens:
        return []
    bm25, ids, texts, metadatas = index
    scores = bm25.get_scores(tokens)
    ranked = sorted(range(len(ids)), key=lambda i: scores[i], reverse=True)[:n_results]
    return [
        {"id": ids[i], "text": texts[i], "metadata": metadatas[i], "bm25": float(scores[i])}
        for i in ranked
        if scores[i] > 0
    ]


# ---- Re-ranking ----

@lru_cache(maxsize=1)
def _ranker(model_name, cache_dir):
    from flashrank import Ranker

    return Ranker(model_name=model_name, cache_dir=cache_dir)


def rerank(query, candidates, config):
    from flashrank import RerankRequest

    ranker = _ranker(config["RAG_RERANK_MODEL"], config["RAG_RERANK_CACHE_DIR"])
    passages = [{"id": i, "text": c["text"]} for i, c in enumerate(candidates)]
    results = ranker.rerank(RerankRequest(query=query, passages=passages))
    for result in results:
        candidates[result["id"]]["rerank"] = float(result["score"])
    return sorted(candidates, key=lambda c: c["rerank"], reverse=True)


# ---- Pipeline ----

def retrieve(query, user_id, config=None):
    """The user's most relevant chunks: [{"text", "source", "page", "section", "score"}]."""
    config = config or current_app.config
    top_k = config["RAG_TOP_K"]
    pool = config["RAG_CANDIDATES"]

    dense = chroma_service.dense_search(query, user_id, pool)
    if not dense:
        return []
    sparse = _sparse_search(query, user_id, pool) if config["RAG_MODE"] == "hybrid" else []

    candidates = {}
    for rank, hit in enumerate(dense):
        entry = candidates.setdefault(hit["id"], {**hit, "rrf": 0.0})
        entry["rrf"] += 1 / (RRF_K + rank + 1)
        entry["distance"] = hit["distance"]
    for rank, hit in enumerate(sparse):
        entry = candidates.setdefault(hit["id"], {**hit, "rrf": 0.0, "distance": None})
        entry["rrf"] += 1 / (RRF_K + rank + 1)
        entry["bm25"] = hit["bm25"]
    fused = sorted(candidates.values(), key=lambda c: c["rrf"], reverse=True)

    if config["RAG_RERANK"]:
        reranked = rerank(query, fused[: config["RAG_RERANK_CANDIDATES"]], config)
        selected = [c for c in reranked if c["rerank"] >= config["RAG_MIN_RERANK_SCORE"]][:top_k]
        score_of = lambda c: c["rerank"]  # noqa: E731
    else:
        # Without a re-ranker, relevance comes from the embedding distance or a strong keyword match
        selected = [
            c for c in fused
            if (c.get("distance") is not None and c["distance"] <= config["RAG_MAX_DISTANCE"])
            or c.get("bm25", 0) >= config["RAG_MIN_BM25_SCORE"]
        ][:top_k]
        score_of = lambda c: c["rrf"]  # noqa: E731

    return [
        {
            "text": c["text"],
            "source": c["metadata"].get("source", "unknown"),
            "page": c["metadata"].get("page"),
            "section": c["metadata"].get("section"),
            "score": float(score_of(c)),
        }
        for c in selected
    ]
