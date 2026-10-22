# Mistrally

[![CI](https://github.com/radhikakumar0705/mistrally/actions/workflows/ci.yml/badge.svg)](https://github.com/radhikakumar0705/mistrally/actions/workflows/ci.yml)
[![CodeQL](https://github.com/radhikakumar0705/mistrally/actions/workflows/codeql.yml/badge.svg)](https://github.com/radhikakumar0705/mistrally/actions/workflows/codeql.yml)

A private AI teaching assistant for programmers. Mistrally streams answers from local LLMs (Mistral, Llama
and others via **Ollama**) or hosted ones (**Groq**), answers questions about your own notes with
**retrieval-augmented generation**, generates quizzes and flashcards, runs Python in a sandbox, and deploys
anywhere from a laptop to **Kubernetes**.

**Stack:** React 18 · TypeScript · Vite · Tailwind CSS · Flask · SQLAlchemy/Alembic · MySQL · ChromaDB ·
Redis/RQ · Ollama · Docker · Kubernetes (Helm, Kustomize, kind) · Argo CD · cert-manager · Terraform (GKE) ·
Prometheus/Grafana/OpenTelemetry · GitHub Actions

**Docs:** [Design document](docs/design.md) · [Retrieval evaluation](docs/rag-evaluation.md) ·
[Performance](docs/performance.md) · [Security](SECURITY.md) ·
[OpenAPI spec](backend/openapi.yaml) (interactive at `/api/docs` when running)

---

## Features

- **Streaming chat**: answers appear token by token over server-sent events, with **Stop**, **Regenerate**
  and **Export to Markdown**
- **Chat with your notes**: upload PDF, TXT or Markdown files. They're processed in the background (with a
  progress bar), searched with hybrid BM25 + embedding retrieval and a re-ranker, and cited by document
  and page under each answer
- **Study mode**: quizzes and flashcards generated from a document or topic, with schema-validated model output
- **Run code**: a Run button on Python code blocks executes them in an isolated sandbox
- **Accounts**: password or **Google sign-in**; short-lived access tokens, rotating refresh tokens, CSRF
  protection, rate limiting
- **Model choice**: any installed Ollama model per conversation, or a hosted model via Groq
- **Dark, responsive UI**: conversations grouped by date with search, rename and delete; deep links
  (`/chat/42`); mobile drawer

## Architecture

```mermaid
flowchart LR
    browser([Browser]) --> nginx["nginx<br/>app + /api proxy"]
    nginx --> api["Flask API<br/>routes → services → repositories"]
    api --> mysql[(MySQL)]
    api --> chroma[(ChromaDB)]
    api --> redis[(Redis)]
    api -->|strategy| llm[[Ollama / Groq / fake]]
    api --> sandbox[[Code sandbox]]
    redis -->|jobs| worker[RQ worker] --> chroma
```

The backend is layered (HTTP routes → services with business rules → repositories, the only code touching
the database) and uses named patterns:
- **Strategy:** model providers.
- **Repository:** data access.
- **Dependency injection:** services take their collaborators, so they can be unit-tested with fakes.
- **Producer-consumer queue:** documents are indexed by a separate worker.

The full write-up, with flows, data model, security and trade-offs, is in [docs/design.md](docs/design.md).

| Area | Highlights |
|---|---|
| Retrieval | Structure-aware chunking, BM25 + embeddings with Reciprocal Rank Fusion, cross-encoder re-ranking; **hit@1 71% → 100%** on the evaluation set, gated in CI |
| Contract | OpenAPI 3.1 spec; contract tests validate every response and streamed event; frontend types generated from the spec with drift detection |
| Performance | Load-tested with k6 at 20 concurrent users: **4.2 → 7.0 answers/s** and p95 time to first byte **3.83 s → 0.46 s** after profiling-driven fixes (75× faster embeddings, skipping retrieval when there's nothing to search, an nginx keep-alive race); 0 failures in 4,625 requests |
| Security | Refresh-token rotation with reuse detection, CSRF double-submit, no auto-linking of Google accounts, sandbox with no network route |
| Supply chain | Trivy image scans that fail CI on fixable HIGH/CRITICAL CVEs, SPDX SBOMs per image, CodeQL, Dependabot, gitleaks secret scanning, pre-commit hooks |
| Delivery | Helm chart (generated secrets kept across upgrades, migrations as an upgrade hook, config-checksum rollouts) verified end to end on a kind cluster with ingress-nginx and HTTPS from a cert-manager CA; enforced NetworkPolicies; Argo CD GitOps; Terraform for a private GKE cluster with Dataplane V2 and Workload Identity |
| Observability | Prometheus metrics (time to first token, generation speed, answer outcomes), Grafana dashboard, JSON logs with request IDs, OpenTelemetry traces |
| Testing | 117 backend tests (unit, integration, contract, migrations), 22 frontend tests, 8 Playwright end-to-end tests against the Docker stack, a k6 load test, a retrieval quality gate, sandbox limit checks, and two changes built test-first (red commit, then green) |

---

## Run it

All options need a model: [Ollama](https://ollama.com) with `ollama pull mistral`, or set
`LLM_PROVIDER=groq` with a free `GROQ_API_KEY`, or `LLM_PROVIDER=fake` to try it without any model.

### Docker Compose (recommended)

```bash
cp .env.example .env        # fill in the secrets
docker compose up --build
```

Open <http://localhost:8090>. Add `--profile monitoring` for Prometheus (:9090), Grafana (:3001) and Jaeger
(:16686), or `--profile ollama` to run Ollama in a container.

### Kubernetes with Helm (local cluster)

One script creates a [kind](https://kind.sigs.k8s.io) cluster with ingress-nginx and cert-manager, builds
and loads the images, and installs the chart with the demo model:

```bash
deploy/kind/setup.sh            # then open https://localhost:8443
deploy/kind/setup.sh --argocd   # or let Argo CD deploy it from GitHub (GitOps)
```

The chart in [helm/mistrally](helm/mistrally) generates its secrets on first install and keeps them across
upgrades, runs database migrations as a hook before every upgrade, and rolls pods when their config
changes. HTTPS comes from a private CA managed by cert-manager
([local-ca.yaml](deploy/cert-manager/local-ca.yaml)); [letsencrypt.yaml](deploy/cert-manager/letsencrypt.yaml)
has the issuers for a public domain.

NetworkPolicies are enforced on kind: the frontend can't reach the databases, and the sandbox can't reach
DNS, the internet or other pods. kind's network plugin doesn't police host-network destinations such as
the Kubernetes API server, which the sandbox can therefore connect to. It has no service-account token, so
it can't authenticate. GKE's Dataplane V2 closes that gap.

### Google Kubernetes Engine

[deploy/terraform/gke](deploy/terraform/gke) describes a production-style cluster:
- private nodes with Cloud NAT
- Dataplane V2, so NetworkPolicies are enforced
- Workload Identity
- a least-privilege node service account
- Artifact Registry
- a static ingress IP

It is validated in CI (`fmt`, `validate`) but has not been applied: running it creates billable resources.

```bash
cd deploy/terraform/gke && cp terraform.tfvars.example terraform.tfvars   # set project_id
terraform init && terraform apply
helm upgrade --install mistrally helm/mistrally -n mistrally --create-namespace -f helm/mistrally/values-gke.yaml
```

### Kubernetes with Kustomize

Plain manifests, if you'd rather not use Helm:

```bash
docker compose build
cp k8s/overlays/local/secrets.env.example k8s/overlays/local/secrets.env   # fill in
kubectl apply -k k8s/overlays/local
kubectl -n mistrally port-forward svc/frontend 8090:80
```

### Local development

```bash
cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements-dev.txt
cp .env.example .env && python app.py          # migrates, then serves :5000
cd frontend && npm install && npm run dev       # http://localhost:5173
```

Optional: set `TASK_QUEUE_URL=redis://localhost:6379/1` and run `python worker.py` to process uploads in the
background (otherwise they're processed inline).

## Tests

```bash
cd backend  && pytest && ruff check . && python -m eval.run_retrieval --check
cd frontend && npm test && npm run lint && npm run typecheck
```

End-to-end and load tests run against the Docker stack with a deterministic fake model:

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d --build
cd frontend && npx playwright install chromium && npm run e2e
docker run --rm -i --network mistrally_default -e BASE_URL=http://frontend:8080 \
  -v "$PWD/loadtest:/scripts" grafana/k6:0.54.0 run /scripts/chat.js
```

## Project structure

```
backend/
  routes/         HTTP layer (auth, chat, documents, study)
  services/       use cases: chat, auth, documents, study, retrieval, ingestion, export
    llm/          model providers (Strategy)
  repositories/   database access (Repository)
  models/  migrations/  tests/  eval/
  openapi.yaml    API contract
frontend/
  src/            pages/  components/  hooks/  api/ (typed client + generated schema)  lib/
  e2e/            Playwright end-to-end tests
sandbox/          isolated Python runner
monitoring/       Prometheus, alert rules, Grafana dashboard
loadtest/         k6 load test and retrieval profiler
helm/mistrally/   Helm chart, values for kind and GKE
k8s/              Kustomize base, overlays, optional Ollama component
deploy/           kind cluster + setup script, cert-manager issuers, Argo CD app, Terraform for GKE
docs/             design.md, rag-evaluation.md, performance.md
.github/          CI, CodeQL, load-test workflow, Dependabot
```
