#!/usr/bin/env bash
# Status ok, the expected version, and the domain invariant: every derived field the
# viewer needs is present. Run after every deploy.
set -euo pipefail
cd "$(dirname "$0")"
# Ask Compose for the effective value: handles .env, quoting and shell overrides
# with exactly the same precedence as deploy.sh, without sourcing executable text.
port=$(docker compose config --format json | python3 -c 'import json, sys; print(next(p["published"] for p in json.load(sys.stdin)["services"]["earththrutime3d"]["ports"] if p["target"] == 8000))')
expected=${1:-$(grep -oP '(?<=^IMAGE_TAG=).*' .env | tr -d 'v')}
report=$(curl -fsS "http://127.0.0.1:$port/healthz")
echo "$report"
python3 - "$report" "$expected" <<'PY'
import json, sys
report, expected = json.loads(sys.argv[1]), sys.argv[2]
if report["status"] != "ok":
    raise SystemExit(f'Status is {report["status"]}')
if expected and report["version"] != expected:
    raise SystemExit(f'Version {report["version"]} is not {expected}')
fields = report["fields"]
if not fields["required"] or fields["missing"] or fields["expected"] < 1:
    raise SystemExit(f'Land fields not fully served: {fields}')
print(f'Smoke passed: {report["version"]}, {fields["expected"]} land fields served.')
PY
