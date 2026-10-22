# Minimal image for running untrusted Python snippets: no compilers, no extra packages, non-root.
FROM python:3.14.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Apply Debian security updates published since the base image was built (found by Trivy)
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10002 sandbox
WORKDIR /app
COPY server.py smoke_test.py ./
USER sandbox

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
CMD ["python", "server.py"]
