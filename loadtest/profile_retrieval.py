"""
Time each retrieval stage, alone and under concurrency. Run inside the backend container:

    docker compose exec -T backend python /app/../loadtest/profile_retrieval.py   (or copy it in)
"""
import statistics
import threading
import time
from types import SimpleNamespace

from app import create_app
from services import chroma_service, retrieval

USER_ID = 987654321
TEXT = "# Grading\n\nThe final exam is worth 40 percent.\n\n# Office hours\n\nThursdays 3-5 pm in room 4B-217.\n"


def stages(app, query):
    with app.app_context():
        config = app.config
        timings = {}
        t = time.perf_counter()
        chroma_service.embed([query])
        timings["embed question"] = time.perf_counter() - t
        t = time.perf_counter()
        dense = chroma_service.dense_search(query, USER_ID, config["RAG_CANDIDATES"])
        timings["dense search (embed + Chroma query)"] = time.perf_counter() - t
        t = time.perf_counter()
        retrieval._sparse_search(query, USER_ID, config["RAG_CANDIDATES"])
        timings["BM25 (fetch user's chunks + score)"] = time.perf_counter() - t
        t = time.perf_counter()
        retrieval.rerank(query, [{**d} for d in dense][: config["RAG_RERANK_CANDIDATES"]], config)
        timings["re-rank"] = time.perf_counter() - t
        return timings


def main():
    app = create_app()
    with app.app_context():
        chroma_service.add_chunks(SimpleNamespace(id="profile-doc", user_id=USER_ID, filename="p.md"),
                                  [{"text": TEXT, "page": None, "section": None}])
        retrieval.retrieve("warm up", USER_ID)

    single = stages(app, "How much is the final exam worth?")
    results, lock = [], threading.Lock()

    def worker():
        r = stages(app, "Where are office hours?")
        with lock:
            results.append(r)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    print(f"{'stage':40} {'alone':>8} {'10 concurrent (median)':>24}")
    for stage, alone in single.items():
        concurrent = statistics.median(r[stage] for r in results)
        print(f"{stage:40} {alone * 1000:7.0f}ms {concurrent * 1000:22.0f}ms")

    with app.app_context():
        chroma_service.delete_document_chunks("profile-doc")


if __name__ == "__main__":
    main()
