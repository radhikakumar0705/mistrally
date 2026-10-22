# Performance

How Mistrally behaves under concurrent load, what profiling found, and what changed.

## Method

- **Stack:** the Docker Compose deployment (nginx → gunicorn/Flask with 2 worker processes × 8 threads →
  MySQL, ChromaDB, Redis) with `docker-compose.test.yml`. That file swaps in the deterministic fake model
  (a word every 20 ms), so the numbers measure Mistrally rather than an LLM's speed.
- **Load:** [k6](https://k6.io), using [`loadtest/chat.js`](../loadtest/chat.js). It ramps to 20 concurrent
  users over 20 s and holds for 60 s. Each iteration creates a conversation, sends a question and reads the
  full streamed answer, then lists conversations. Half the users have an indexed document, so their
  questions go through hybrid retrieval and re-ranking; the other half don't.
- **Thresholds** (the test fails if any is missed): fewer than 1% failed requests; 99% of checks passing; p95
  time to first byte under 500 ms for users without documents and under 2 s for users with documents.
- **Hardware:** a Windows laptop running Docker Desktop (16 vCPUs, 8 GB for the VM).
- **Profiling:** [`loadtest/profile_retrieval.py`](../loadtest/profile_retrieval.py) times each retrieval
  stage alone and with 10 concurrent requests, inside the API container.

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d --build
docker run --rm -i --network mistrally_default -e BASE_URL=http://frontend:8080 \
  -v "$PWD/loadtest:/scripts" grafana/k6:0.54.0 run /scripts/chat.js
```

## Results

| 20 concurrent users | First run | Final |
|---|---|---|
| Answers per second | 4.18 | **7.01** (+68%) |
| Failed requests | 0% | **0%** (0 of 4,625 across two runs) |
| Time to first byte, users **with** documents, p50 / p95 | 1.44 s / 3.83 s | **107 ms / 462 ms** |
| Time to first byte, users **without** documents, p50 / p95 | 67 ms / 637 ms | **20 ms / 160 ms** |
| Full answer time, p95 (about 45 words at 20 ms each, plus overhead) | 4.07 s | **1.50 s** |

## What the load test found

### 1. Retrieval ran for users who had no documents

Profiling showed that retrieval still cost about 0.45 s per question for users with no documents: the
question was embedded and Chroma was queried, only to return nothing. Under 7 concurrent requests that
pushed time to first byte to 3.7–5.5 s even with the instant fake model.

**Fix:** `ChatService` checks `DocumentRepository.has_ready()` (one indexed query) before retrieving. This
was built test-first (commits `b25145f`, then `0339b41`). Time to first byte for these users under the same
7 concurrent requests fell from 3.7–5.5 s to 0.06–0.17 s.

### 2. The stock embedding function padded every input to 256 tokens

Profiling the remaining retrieval stages showed embedding one short question took **311 ms, and 5.1 s with
10 concurrent requests**. Re-ranking twelve passages took only 12 ms, so the model wasn't the problem. The
cause was Chroma's default MiniLM embedding function. It pads every input to the model's maximum of 256
tokens, so a 10-token question cost as much as a full paragraph, and it uses every CPU core for each call,
so concurrent requests oversubscribed the CPU.

**Fix:** [`services/embeddings.py`](../backend/services/embeddings.py) loads the same model files but pads
each batch only to its longest text, and caps threads per inference (`EMBEDDING_THREADS`, default 2). Padded
positions are masked in both attention and mean pooling, so the vectors are identical to the stock
function's (largest difference 4.5e-8, cosine similarity 1.0) and existing stored embeddings remain valid.
Retrieval quality is unchanged (the evaluation in [rag-evaluation.md](rag-evaluation.md) still scores 100%).

| Stage | Before: alone / 10 concurrent | After: alone / 10 concurrent |
|---|---|---|
| Embed the question | 311 ms / 5,138 ms | **5 ms / 18 ms** |
| Dense search (embed + Chroma query) | 255 ms / 2,200 ms | **53 ms / 76 ms** |
| BM25 | 4 ms / 34 ms | 5 ms / 25 ms |
| Re-rank 12 candidates | 12 ms / 176 ms | 9 ms / 16 ms |

The 20-user load test went from 4.18 to 6.85 answers per second, and p95 time to first byte for users
with documents went from 3.83 s to 0.37 s.

### 3. Occasional 502s from an nginx keep-alive race

One request in 2,331 failed with a 502. nginx's error log showed `Connection reset by peer while reading
response header from upstream` on a reused connection. gunicorn closes idle keep-alive connections after
5 s, and nginx occasionally sent a request on one just as it closed.

**Fix:** the nginx upstream's `keepalive_timeout` is now 4 s, shorter than gunicorn's 5 s, so nginx always
retires an idle connection before the API does. Two further runs had 0 failures in 4,625 requests.

### Also tried: more worker processes

Before fixing the embedding function, raising gunicorn from 2 to 4 processes improved throughput by 18%
(retrieval is CPU-bound Python, and more processes avoid contending for one interpreter lock). After the
fix, 2 processes meet every threshold on this machine, so 2 remains the default. `WEB_CONCURRENCY` is
configurable, and in Kubernetes the API scales horizontally with its autoscaler.

## Limits of these numbers

- The fake model returns words at a fixed rate. With a real model, total answer time is dominated by
  generation speed, which the Grafana dashboard measures in production.
- The run is short (about 90 s) on one machine, with the load generator on the same host as the stack.
