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
# The timer runs this hourly, but m710q pulls only the newest snapshot once a day (04:20,
# system-operation/m710q/backup-earththrutime.sh). The kept window must outlast that pull
# interval, or a missed or late pull finds nothing it has not already lost:
# KEEP x 1 h >= 24 h. 24 matches ScoreMate and fsis.
keep=${KEEP:-24}
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
# Beside the database, where settings.INTEGRITY_SENTINEL points: while it exists /healthz
# answers degraded.
sentinel = live.parent / "INTEGRITY_FAIL"

source = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
copy = sqlite3.connect(target)
with copy:
    source.backup(copy)
copy.close()
source.close()

# A snapshot that fails its integrity check is worse than none, because it would be
# trusted. Take it out of the db-*.sqlite3 set that the offsite pull and the prune below
# read, raise the sentinel, and stop before pruning: the older snapshots are now the
# restore candidates. The first failed copy stays as evidence under a name nothing globs;
# later ones are dropped so an hourly failure does not fill the disk.
check = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
try:
    problems = [row[0] for row in check.execute("PRAGMA integrity_check")]
except sqlite3.DatabaseError as error:
    problems = [f"integrity_check could not run: {error}"]
finally:
    check.close()
if problems != ["ok"]:
    evidence = store / target.name.replace(".sqlite3", "-INTEGRITY_FAIL.corrupt")
    if any(store.glob("*-INTEGRITY_FAIL.corrupt")):
        target.unlink(missing_ok=True)
    else:
        target.replace(evidence)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    sentinel.write_text("\n".join([
        f"{stamp} backup.sh: PRAGMA integrity_check failed: {problems[0]}",
        "/healthz stays degraded while this file exists; pruning is suspended.",
        "The older backups/db-*.sqlite3 are the restore candidates. The next passing",
        "check removes this file.",
        "",
        *problems[:20],
    ]) + "\n")
    raise SystemExit(f"Integrity check failed: {problems[0]}")
sentinel.unlink(missing_ok=True)
print(f"Backed up to {target.name} ({target.stat().st_size} bytes)")

# Prune only after a verified new snapshot exists, and never below one kept copy.
keep = max(1, int(os.environ.get("KEEP", "24")))
snapshots = sorted(store.glob("db-*.sqlite3"), key=lambda path: path.name, reverse=True)
for stale in snapshots[keep:]:
    stale.unlink()
if len(snapshots) > keep:
    print(f"Kept the newest {keep} snapshots.")
PY
