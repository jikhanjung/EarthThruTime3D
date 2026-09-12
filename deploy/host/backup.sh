#!/usr/bin/env bash
# Snapshot the live SQLite database, verify the copy, then keep the newest ones.
# Run before every deploy; safe to run at any time, including with nothing running.
#
# The work happens in a throwaway container rather than in the serving one, so a backup
# does not depend on which image or mounts are currently up, and the snapshot lands
# owned by the same user that owns the database. sqlite3's own backup API is the only
# safe way to copy a database that has writers attached.
set -euo pipefail
cd "$(dirname "$0")"
keep=${KEEP:-14}
tag=${1:-$(grep -oP '(?<=^IMAGE_TAG=).*' .env 2>/dev/null || true)}
[[ -n "$tag" ]] || { echo 'No image tag: pass one or deploy first.' >&2; exit 1; }
[[ -f db/db.sqlite3 ]] || { echo 'No database yet; nothing to back up.'; exit 0; }
mkdir -p backups
# -i matters: without an attached stdin the here-document never reaches python, which
# then exits successfully having done nothing.
docker run --rm -i --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m \
    --mount "type=bind,src=$PWD/db,dst=/var/lib/earththrutime3d" \
    --mount "type=bind,src=$PWD/backups,dst=/var/lib/earththrutime3d-backups" \
    -e "KEEP=$keep" --entrypoint python "honestjung/earththrutime3d:$tag" - <<'PY'
import os
import sqlite3
import time
from pathlib import Path

live = Path("/var/lib/earththrutime3d/db.sqlite3")
store = Path("/var/lib/earththrutime3d-backups")
target = store / time.strftime("db-%Y%m%dT%H%M%SZ.sqlite3", time.gmtime())

source = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
copy = sqlite3.connect(target)
with copy:
    source.backup(copy)
copy.close()
source.close()

# A snapshot that fails its integrity check is worse than none, because it would be
# trusted. Refuse it rather than keep it.
check = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
result = check.execute("PRAGMA integrity_check").fetchone()[0]
check.close()
if result != "ok":
    target.unlink(missing_ok=True)
    raise SystemExit(f"Integrity check failed: {result}")
print(f"Backed up to {target.name} ({target.stat().st_size} bytes)")

# Prune only after a verified new snapshot exists, and never below one kept copy.
keep = max(1, int(os.environ.get("KEEP", "14")))
snapshots = sorted(store.glob("db-*.sqlite3"), key=lambda path: path.name, reverse=True)
for stale in snapshots[keep:]:
    stale.unlink()
if len(snapshots) > keep:
    print(f"Kept the newest {keep} snapshots.")
PY
