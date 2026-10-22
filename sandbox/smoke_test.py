"""
Checks that the sandbox's limits actually hold. Runs inside the sandbox image (CI does this too):

    docker run --rm --network none mistrally-sandbox:local python smoke_test.py
"""
import sys

from server import run_snippet

CHECKS = [
    ("prints output", "print(sum(range(10)))", lambda r: r["stdout"].strip() == "45" and r["exit_code"] == 0),
    ("reads stdin", "print(input().upper())", lambda r: r["stdout"].strip() == "HI"),
    ("reports errors", "1/0", lambda r: "ZeroDivisionError" in r["stderr"] and r["exit_code"] != 0),
    ("stops infinite loops", "while True: pass", lambda r: r["timed_out"] or r["exit_code"] != 0),
    ("caps memory", "x = bytearray(2 * 1024**3)", lambda r: "MemoryError" in r["stderr"]),
    ("limits processes",
     "import os\nfor _ in range(64):\n    os.fork()",
     lambda r: "BlockingIOError" in r["stderr"] or "Resource temporarily unavailable" in r["stderr"]),
    ("limits file size",
     "open('big', 'wb').write(b'0' * 5_000_000)",
     lambda r: r["exit_code"] != 0),
    ("has no network",
     "import socket\nsocket.create_connection(('1.1.1.1', 80), timeout=2)",
     lambda r: r["exit_code"] != 0),
    ("has an empty environment", "import os; print(sorted(os.environ))",
     lambda r: "SANDBOX_TOKEN" not in r["stdout"]),
    ("truncates huge output", "print('x' * 100_000)", lambda r: "output truncated" in r["stdout"]),
]

failed = 0
for name, code, ok in CHECKS:
    result = run_snippet(code, stdin="hi\n")
    passed = ok(result)
    failed += not passed
    print(f"{'PASS' if passed else 'FAIL'}  {name}  ({result['duration_ms']} ms)")
    if not passed:
        print("      ", result)
sys.exit(1 if failed else 0)
