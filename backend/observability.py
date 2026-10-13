"""
Metrics, structured logs and tracing.

- Prometheus metrics at /metrics (multi-process safe under gunicorn via PROMETHEUS_MULTIPROC_DIR)
- One JSON access-log line per request, with a request ID shared with nginx (X-Request-ID)
- OpenTelemetry traces for Flask, outgoing HTTP (model calls) and SQL, when an OTLP endpoint is configured
"""
import logging
import os
import re
import time
import uuid

from flask import Response, g, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

access_log = logging.getLogger("mistrally.access")

# In multi-process mode metrics are files in this directory, created as soon as metrics are defined.
# gunicorn's on_starting hook clears it; other entry points (flask CLI, tests) just need it to exist.
if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
    os.makedirs(os.environ["PROMETHEUS_MULTIPROC_DIR"], exist_ok=True)

# ---- Metrics ----

HTTP_REQUESTS = Counter(
    "mistrally_http_requests_total", "HTTP requests handled", ["method", "endpoint", "status"]
)
HTTP_LATENCY = Histogram(
    "mistrally_http_request_duration_seconds",
    "Time until the response headers are sent (streams continue afterwards)",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
LLM_TIME_TO_FIRST_TOKEN = Histogram(
    "mistrally_llm_time_to_first_token_seconds",
    "Delay between sending a prompt and receiving the first piece of the answer",
    ["provider", "model"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 4, 8, 16, 32, 64),
)
LLM_CHUNKS = Counter("mistrally_llm_stream_chunks_total", "Answer pieces streamed to clients", ["provider", "model"])
LLM_CHUNKS_PER_SECOND = Histogram(
    "mistrally_llm_chunks_per_second",
    "Generation speed of each answer after the first piece",
    ["provider", "model"],
    buckets=(1, 5, 10, 20, 40, 80, 160, 320),
)
LLM_STREAMS = Counter(
    "mistrally_llm_streams_total", "Answers by outcome", ["provider", "model", "outcome"]
)  # outcome: completed | stopped | error | unavailable
RAG_RETRIEVAL_SECONDS = Histogram(
    "mistrally_rag_retrieval_seconds", "Document retrieval latency",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)
RAG_CHUNKS_USED = Histogram(
    "mistrally_rag_chunks_used", "Document chunks passed to the model per question", buckets=(0, 1, 2, 3, 4, 6, 8, 12)
)
DOCUMENTS_INGESTED = Counter("mistrally_documents_ingested_total", "Document uploads by result", ["status"])


class StreamMetrics:
    """Times one streamed answer: call piece() for every chunk and finish(outcome) once."""

    def __init__(self, provider, model):
        self.labels = {"provider": provider, "model": model}
        self.started = time.perf_counter()
        self.first_at = None
        self.count = 0
        self.done = False

    def piece(self):
        if self.first_at is None:
            self.first_at = time.perf_counter()
            LLM_TIME_TO_FIRST_TOKEN.labels(**self.labels).observe(self.first_at - self.started)
        self.count += 1
        LLM_CHUNKS.labels(**self.labels).inc()

    def finish(self, outcome):
        if self.done:
            return
        self.done = True
        LLM_STREAMS.labels(outcome=outcome, **self.labels).inc()
        if self.first_at is not None and self.count > 1:
            elapsed = time.perf_counter() - self.first_at
            if elapsed > 0:
                LLM_CHUNKS_PER_SECOND.labels(**self.labels).observe((self.count - 1) / elapsed)


def _registry():
    # Under gunicorn every worker writes its metrics to files; the endpoint merges them
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        from prometheus_client import multiprocess

        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return registry
    return REGISTRY


# ---- Logging ----

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestContextFilter(logging.Filter):
    """Adds request_id and trace_id to every log record."""

    def filter(self, record):
        try:
            record.request_id = g.get("request_id", "-")
        except RuntimeError:  # outside a request
            record.request_id = "-"
        record.trace_id = _current_trace_id()
        return True


def _current_trace_id():
    try:
        from opentelemetry import trace

        context = trace.get_current_span().get_span_context()
        return format(context.trace_id, "032x") if context.is_valid else "-"
    except Exception:
        return "-"


def configure_logging(level, fmt):
    handler = logging.StreamHandler()
    handler.addFilter(RequestContextFilter())
    if fmt == "json":
        from pythonjsonlogger import jsonlogger

        handler.setFormatter(jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(trace_id)s",
            rename_fields={"asctime": "time", "levelname": "level", "name": "logger"},
        ))
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)  # replaced by our access log


# ---- Tracing ----

_tracing_started = False


def configure_tracing(app, engine):
    """Export OpenTelemetry traces when OTEL_EXPORTER_OTLP_ENDPOINT is set (e.g. to Jaeger)."""
    global _tracing_started
    endpoint = app.config.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    if not _tracing_started:
        provider = TracerProvider(resource=Resource.create({"service.name": app.config["OTEL_SERVICE_NAME"]}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
        trace.set_tracer_provider(provider)
        RequestsInstrumentor().instrument()
        _tracing_started = True
    FlaskInstrumentor().instrument_app(app, excluded_urls="health/.*,metrics")
    SQLAlchemyInstrumentor().instrument(engine=engine)
    app.logger.info("OpenTelemetry tracing enabled", extra={"otlp_endpoint": endpoint})


# ---- Flask wiring ----

def init_app(app):
    @app.before_request
    def start_timer():
        incoming = request.headers.get("X-Request-ID", "")
        g.request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        g.request_started = time.perf_counter()

    @app.after_request
    def record(response):
        endpoint = request.url_rule.rule if request.url_rule else "unmatched"
        if endpoint in ("/metrics", "/health/live", "/health/ready"):
            return response
        elapsed = time.perf_counter() - g.get("request_started", time.perf_counter())
        HTTP_REQUESTS.labels(request.method, endpoint, response.status_code).inc()
        HTTP_LATENCY.labels(request.method, endpoint).observe(elapsed)
        response.headers["X-Request-ID"] = g.request_id
        access_log.info(
            "request",
            extra={
                "method": request.method,
                "path": request.path,
                "endpoint": endpoint,
                "status": response.status_code,
                "duration_ms": round(elapsed * 1000, 1),
                "client_ip": request.remote_addr,
            },
        )
        return response

    @app.route("/metrics")
    def metrics():
        return Response(generate_latest(_registry()), mimetype=CONTENT_TYPE_LATEST)
