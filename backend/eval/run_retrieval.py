"""
Retrieval evaluation: how often does search hand the model the right passage?

    python -m eval.run_retrieval                  # table for every configuration
    python -m eval.run_retrieval --markdown out.md
    python -m eval.run_retrieval --check          # CI: fail if the default config regresses

Metrics (over questions.jsonl):
  hit@1     the top chunk contains the expected passage
  hit@k     any returned chunk (k = RAG_TOP_K) contains it
  MRR       mean reciprocal rank of the first correct chunk
  no-answer questions the documents can't answer that correctly get no context at all
  latency   mean retrieval time per question
"""
import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402
from services import chroma_service, retrieval  # noqa: E402
from services.chunking import chunk_fixed, chunk_structured  # noqa: E402

USER_ID = 1

CONFIGS = [
    # name, chunker, overrides
    ("Baseline: fixed chunks + embeddings", "fixed", {"RAG_MODE": "dense", "RAG_RERANK": False}),
    ("Structured chunks + embeddings", "structured", {"RAG_MODE": "dense", "RAG_RERANK": False}),
    ("Structured + hybrid (BM25 + embeddings, RRF)", "structured", {"RAG_MODE": "hybrid", "RAG_RERANK": False}),
    ("Structured + hybrid + TinyBERT-L2 re-ranker", "structured",
     {"RAG_MODE": "hybrid", "RAG_RERANK": True, "RAG_RERANK_MODEL": "ms-marco-TinyBERT-L-2-v2",
      "RAG_MIN_RERANK_SCORE": 4e-5}),
    ("Structured + hybrid + MiniLM-L12 re-ranker (default)", "structured", {"RAG_MODE": "hybrid", "RAG_RERANK": True}),
]

# Regression gate for --check, applied to the default configuration
MIN_HIT_AT_K = 0.85
MIN_NO_ANSWER = 0.9


def load_questions():
    with open(ROOT / "questions.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def make_app(chroma_path):
    class EvalConfig(Config):
        SECRET_KEY = JWT_SECRET_KEY = "eval-only-secret"
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        CHROMA_HOST = None
        CHROMA_DB_PATH = chroma_path
        LOG_LEVEL = "WARNING"

    return create_app(EvalConfig)


def index_corpus(chunker):
    chunk = chunk_fixed if chunker == "fixed" else chunk_structured
    for i, path in enumerate(sorted((ROOT / "corpus").glob("*.md"))):
        document = SimpleNamespace(id=f"doc{i}", user_id=USER_ID, filename=path.name)
        chroma_service.add_chunks(document, chunk([(None, path.read_text(encoding="utf-8"))]))


def evaluate(config, questions):
    hits1 = hitsk = 0
    reciprocal_ranks, latencies = [], []
    no_answer_correct = answerable = unanswerable = 0
    misses = []

    for q in questions:
        start = time.perf_counter()
        results = retrieval.retrieve(q["question"], USER_ID, config)
        latencies.append(time.perf_counter() - start)

        if q["document"] is None:
            unanswerable += 1
            no_answer_correct += not results
            continue

        answerable += 1
        expect = q["expect"].lower()
        rank = next(
            (i + 1 for i, r in enumerate(results) if r["source"] == q["document"] and expect in r["text"].lower()),
            None,
        )
        hits1 += rank == 1
        hitsk += rank is not None
        reciprocal_ranks.append(1 / rank if rank else 0)
        if rank is None:
            misses.append(q["question"])

    return {
        "hit@1": hits1 / answerable,
        "hit@k": hitsk / answerable,
        "mrr": statistics.mean(reciprocal_ranks),
        "no_answer": no_answer_correct / unanswerable if unanswerable else 1.0,
        "latency_ms": 1000 * statistics.mean(latencies),
        "misses": misses,
    }


def run():
    questions = load_questions()
    results = []
    for chunker in ("fixed", "structured"):
        # Chroma keeps its files open on Windows, so cleanup failures are ignored
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as chroma_path:
            app = make_app(chroma_path)
            with app.app_context():
                index_corpus(chunker)
                for name, config_chunker, overrides in CONFIGS:
                    if config_chunker != chunker:
                        continue
                    config = {**app.config, **overrides}
                    retrieval.retrieve("warm up", USER_ID, config)  # load models before timing
                    results.append({"name": name, **evaluate(config, questions)})
            chroma_service._collection_for.cache_clear()
            retrieval._bm25_cache.clear()  # both chunkers reuse chunk ids
    return questions, results


def to_markdown(questions, results):
    answerable = sum(q["document"] is not None for q in questions)
    lines = [
        f"Questions: {answerable} answerable, {len(questions) - answerable} unanswerable "
        f"(corpus: {len(list((ROOT / 'corpus').glob('*.md')))} documents). k = {Config.RAG_TOP_K}.",
        "",
        "| Configuration | hit@1 | hit@k | MRR | No-answer accuracy | Latency |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['name']} | {r['hit@1']:.0%} | {r['hit@k']:.0%} | {r['mrr']:.3f} | "
            f"{r['no_answer']:.0%} | {r['latency_ms']:.0f} ms |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--markdown", help="also write the results table to this file")
    parser.add_argument("--check", action="store_true", help="exit non-zero if the default config regresses")
    parser.add_argument("--show-misses", action="store_true")
    args = parser.parse_args()

    questions, results = run()
    table = to_markdown(questions, results)
    print(table)
    if args.show_misses:
        for r in results:
            print(f"\n{r['name']} missed:", *[f"  - {m}" for m in r["misses"]] or ["  (none)"], sep="\n")
    if args.markdown:
        Path(args.markdown).write_text(table + "\n", encoding="utf-8")

    if args.check:
        default = results[-1]
        if default["hit@k"] < MIN_HIT_AT_K or default["no_answer"] < MIN_NO_ANSWER:
            print(f"\nRegression: hit@k {default['hit@k']:.0%} (min {MIN_HIT_AT_K:.0%}), "
                  f"no-answer {default['no_answer']:.0%} (min {MIN_NO_ANSWER:.0%})", file=sys.stderr)
            sys.exit(1)
        print("\nRetrieval quality check passed.")


if __name__ == "__main__":
    main()
