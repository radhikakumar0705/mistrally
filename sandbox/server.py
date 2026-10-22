"""
sockRat code sandbox: runs short Python snippets for the "Run" button on code blocks.

Defense in depth; no single layer is trusted on its own:
  - the container has no route to the internet or the databases (Docker internal network / Kubernetes
    NetworkPolicy), runs as a non-root user with a read-only root filesystem, no Linux capabilities and
    no-new-privileges, and has memory, CPU and process limits
  - each snippet runs in a fresh temporary directory, in Python's isolated mode with an empty environment,
    under per-process resource limits (CPU time, memory, file size, open files, processes) and a wall-clock
    timeout, and only two snippets run at once
  - only callers with the shared token (the API) are accepted, and requests and output are size-capped
This is suitable for a learning app; hosting it for untrusted strangers at scale would call for a stronger
boundary such as gVisor or Firecracker microVMs.
"""
import hmac
import json
import os
import resource
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("SANDBOX_TOKEN", "")
PORT = int(os.environ.get("PORT", "8080"))
TIMEOUT_SECONDS = float(os.environ.get("SANDBOX_TIMEOUT", "5"))
MEMORY_BYTES = int(os.environ.get("SANDBOX_MEMORY_MB", "256")) * 1024 * 1024
MAX_REQUEST_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 16 * 1024
CONCURRENCY = threading.BoundedSemaphore(int(os.environ.get("SANDBOX_CONCURRENCY", "2")))


def _limit_resources():
    """Runs in the child just before Python starts."""
    cpu = int(TIMEOUT_SECONDS) + 1
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_NPROC, (16, 16))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.setsid()  # own process group, so a timeout kills everything it started


def _truncate(data):
    text = data.decode("utf-8", errors="replace")
    if len(data) > MAX_OUTPUT_BYTES:
        text = text[:MAX_OUTPUT_BYTES] + "\n... output truncated ..."
    return text


def run_snippet(code, stdin=""):
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="run-") as workdir:
        process = subprocess.Popen(
            [sys.executable, "-I", "-c", code],
            cwd=workdir,
            env={"PATH": "/usr/bin:/bin", "HOME": workdir, "PYTHONIOENCODING": "utf-8"},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=_limit_resources,
        )
        timed_out = False
        try:
            stdout, stderr = process.communicate(stdin.encode(), timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, 9)
            stdout, stderr = process.communicate()
    return {
        "stdout": _truncate(stdout),
        "stderr": _truncate(stderr) + (f"\nTimed out after {TIMEOUT_SECONDS:g} seconds." if timed_out else ""),
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "duration_ms": round((time.perf_counter() - started) * 1000),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "sandbox"
    sys_version = ""

    def _send(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/run":
            return self._send(404, {"error": "not found"})
        supplied = self.headers.get("Authorization", "").removeprefix("Bearer ")
        if not TOKEN or not hmac.compare_digest(supplied, TOKEN):
            return self._send(401, {"error": "unauthorized"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_REQUEST_BYTES:
            return self._send(413, {"error": "request too large"})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            code, stdin = str(body["code"]), str(body.get("stdin", ""))
        except (ValueError, KeyError):
            return self._send(400, {"error": "expected JSON with a 'code' field"})
        if not CONCURRENCY.acquire(timeout=10):
            return self._send(503, {"error": "busy, try again"})
        try:
            return self._send(200, run_snippet(code, stdin))
        finally:
            CONCURRENCY.release()

    def log_message(self, fmt, *args):
        # One JSON line per request, without the submitted code
        print(json.dumps({"logger": "sandbox", "message": fmt % args}), flush=True)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("SANDBOX_TOKEN must be set")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
