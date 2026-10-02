#!/usr/bin/env bash
# The daily wind and cloud refresh (jikhanjung P11), run by the host's cron:
#
#   10 17 * * * /srv/earththrutime3d/scripts/present.sh >> /srv/earththrutime3d/logs/present.log 2>&1
#
# The container copies this script and the fetch code here at every start (install.sh), so
# what runs is the deployed release's. Python runs in a venv the host keeps apart from the
# copied files (the container writes those as UID 10001): rebuilt when the host's Python or
# requirements-present.txt changes. It fetches the 12 UTC GFS analysis and the GMGSI image of
# that hour into present-live/, which the app reads; a failed run changes nothing there but
# status.json, and the app falls back to the release's own moment after 48 hours.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${EARTHTHRUTIME_ROOT:-/srv/earththrutime3d}"
VENV="${PRESENT_VENV:-$ROOT/cron-venv}"
OUT="${PRESENT_LIVE:-$ROOT/present-live}"
PY="${PRESENT_PYTHON:-/usr/bin/python3}"
HOUR="${PRESENT_HOUR:-12}"

[[ -f "$HERE/fetch_present_weather.py" ]] || { echo "$(date -Is) no fetch script in $HERE; has the container started?" >&2; exit 1; }
mkdir -p "$VENV" "$OUT"
exec 9>"$VENV.lock"
flock -n 9 || { echo "$(date -Is) a refresh is already running; skipped"; exit 0; }

want="$({ "$PY" -c 'import sys; print(sys.version)'; cat "$HERE/requirements-present.txt"; } | sha256sum | cut -d' ' -f1)"
if [[ "$(cat "$VENV/.stamp" 2>/dev/null)" != "$want" ]]; then
    echo "$(date -Is) building the venv in $VENV"
    rm -rf "$VENV"
    "$PY" -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade pip
    "$VENV/bin/pip" install -q -r "$HERE/requirements-present.txt"
    echo "$want" > "$VENV/.stamp"          # only once everything installed
fi

echo "$(date -Is) refresh from $(cat "$HERE/INSTALLED" 2>/dev/null || echo '?')"
cd "$HERE"
timeout 1200 "$VENV/bin/python" fetch_present_weather.py --live "$OUT" --hour "$HOUR"
