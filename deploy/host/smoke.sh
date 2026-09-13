#!/usr/bin/env bash
# Status ok, the expected version, and the domain invariant: the elevation series is
# the one served and every field it needs is present. Run after every deploy.
set -euo pipefail
cd "$(dirname "$0")"
port=${HOST_PORT:-8014}
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
if not fields["required"] or fields.get("series") != "paleodem" or fields["missing"] or fields["expected"] != 110:
    raise SystemExit(f'Elevation series not fully served: {fields}')
print(f'Smoke passed: {report["version"]}, {fields["series"]} series, {fields["expected"]} fields served.')
PY
