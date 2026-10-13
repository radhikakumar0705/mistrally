# Retrieval evaluation

How often does Mistrally's document search hand the model the passage that answers the question,
and how often does it correctly hand over *nothing* when the documents can't answer it?

Reproduce with `cd backend && python -m eval.run_retrieval --show-misses`. CI runs the same script with
`--check` on every push, so a change that lowers retrieval quality fails the build.

## Results

Questions: 41 answerable, 12 unanswerable (corpus: 6 documents). k = 4.

| Configuration | hit@1 | hit@k | MRR | No-answer accuracy | Latency |
|---|---|---|---|---|---|
| Baseline: fixed chunks + embeddings | 71% | 73% | 0.720 | 100% | 204 ms |
| Structured chunks + embeddings | 98% | 98% | 0.976 | 100% | 195 ms |
| Structured + hybrid (BM25 + embeddings, RRF) | 100% | 100% | 1.000 | 92% | 199 ms |
| Structured + hybrid + TinyBERT-L2 re-ranker | 98% | 100% | 0.988 | 100% | 369 ms |
| Structured + hybrid + MiniLM-L12 re-ranker (default) | 100% | 100% | 1.000 | 100% | 432 ms |

Latency is the mean retrieval time per question on a laptop CPU (Windows, no GPU), including embedding the
question, BM25 scoring and re-ranking 12 candidates.

## What changed and why it helped

1. **Structure-aware chunking (71% → 98% hit@1).** The original splitter cut the text into fixed 1,000-character
   windows, so short sections were glued to their neighbours and the embedding of a chunk mixed several topics
   ("Which block always runs?" landed in a chunk about virtual environments and f-strings). Chunks now follow
   headings and pages, keep paragraphs whole, overlap slightly, and start with their section title.
2. **Hybrid search (98% → 100%).** Embeddings miss exact identifiers and keyword-heavy questions
   ("WHERE vs HAVING", "LAB-E73", "4B-217"). BM25 keyword scores are fused with the embedding ranking using
   Reciprocal Rank Fusion. On its own this lets one unanswerable question through (92% no-answer accuracy),
   because some generic word always matches.
3. **Cross-encoder re-ranking (no-answer 92% → 100%).** A small ONNX cross-encoder (FlashRank) reads the question
   and each candidate together and scores relevance. Its scores separate unanswerable questions (≤ 3e-5) from
   correct passages (≥ 2.5e-4) by an order of magnitude, so a cutoff of 1e-4 removes irrelevant context without
   losing answers. The larger MiniLM-L12 model was chosen over TinyBERT-L2 because TinyBERT's margin between the
   two groups was only about 2x (one correct passage scored 5.8e-5).

## Metrics

- **hit@1**: the top chunk comes from the right document and contains the expected passage.
- **hit@k**: any of the k returned chunks does.
- **MRR**: mean reciprocal rank of the first correct chunk (0 if none).
- **No-answer accuracy**: for questions the documents cannot answer (pizza toppings, World Cup winners...), the
  share that correctly get no context at all, so the model answers from general knowledge instead of citing
  irrelevant notes.

## Caveats

- The set is small (53 questions over 6 documents) and the re-ranker cutoff was calibrated on the same questions,
  so the default configuration's numbers are optimistic. Treat them as a regression baseline, not a benchmark.
  A larger held-out set would be the next step.
- The corpus is short technical notes. Long PDFs with tables, code-heavy files and other languages behave differently.
