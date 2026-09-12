import json
import os
from urllib.request import urlopen

with urlopen("http://127.0.0.1:8000/healthz", timeout=4) as response:
    report = json.load(response)
expected = os.environ.get("EARTHTHRUTIME_VERSION", "").lstrip("v")
if report["status"] not in ("ok", "degraded") or (expected and report["version"] != expected):
    raise SystemExit("Unhealthy or unexpected version: " + str(report))
