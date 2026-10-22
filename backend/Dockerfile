# syntax=docker/dockerfile:1

# ---- Build stage: install dependencies into a virtualenv ----
FROM python:3.14.7-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -r requirements.txt

# Bake the ONNX embedding and re-ranking models into the image so containers start without downloading them
RUN /opt/venv/bin/python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as E; E()(['warm up'])" \
 && /opt/venv/bin/python -c "from flashrank import Ranker; Ranker(model_name='ms-marco-MiniLM-L-12-v2', cache_dir='/root/.cache/flashrank')"

# ---- Runtime stage: slim image, non-root user ----
FROM python:3.14.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HOME=/home/app \
    FLASK_APP=wsgi \
    LOG_FORMAT=json \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus

# Apply Debian security updates published since the base image was built (found by Trivy)
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=app:app /root/.cache/chroma /home/app/.cache/chroma
COPY --from=builder --chown=app:app /root/.cache/flashrank /home/app/.cache/flashrank

WORKDIR /app
COPY --chown=app:app . .
USER app

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health/live', timeout=2)"

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
