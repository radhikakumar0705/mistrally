"""Gunicorn settings. Threaded workers keep long-lived streaming responses from blocking other requests."""
import os
import shutil

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
worker_class = "gthread"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "8"))
timeout = 120          # worker heartbeat; streaming requests can run longer than this
graceful_timeout = 30
keepalive = 5
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
accesslog = None  # the app writes its own structured access log


def on_starting(server):
    # Prometheus multi-process mode: workers write metrics to files in this directory
    directory = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if directory:
        shutil.rmtree(directory, ignore_errors=True)
        os.makedirs(directory, exist_ok=True)


def child_exit(server, worker):
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        from prometheus_client import multiprocess

        multiprocess.mark_process_dead(worker.pid)
