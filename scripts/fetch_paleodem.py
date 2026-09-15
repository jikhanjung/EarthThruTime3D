#!/usr/bin/env python3
"""Fetch or verify pinned CC BY archives: the PaleoDEMs by default, or another manifest.

Manifests: sources/paleodem.json (Scotese & Wright 2018 elevation grids) and
sources/paleotemp.json (Scotese 2021 temperature maps); pass --manifest to choose.

An asset with `unzip` is extracted beside the archive; `members`, a list of glob
patterns, limits the extraction to the files that match; `discard` deletes the archive
once it is extracted, for one too large to keep (sources/paleomist.json), after which
the extracted folder stands for it and --verify-only accepts the folder.
"""

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (ROOT / "data/sources").resolve()


def verify(path, asset):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 24), b""):
            digest.update(chunk)
    if path.stat().st_size != asset["bytes"] or digest.hexdigest() != asset["sha256"]:
        raise ValueError(f"Source differs from pinned manifest: {asset['path']}")


def wanted(name, patterns):
    if name.endswith(".gplates.cache") or name.startswith("__MACOSX") or name.endswith("/"):
        return False
    return not patterns or any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Check local files without network access")
    parser.add_argument("--manifest", default=ROOT / "sources/paleodem.json", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    for asset in manifest["assets"]:
        target = (ROOT / asset["path"]).resolve()
        if not target.is_relative_to(SOURCES):
            raise ValueError("Asset must stay inside data/sources")
        out = target.parent / asset["unzip"] if "unzip" in asset else None
        if asset.get("discard") and not target.exists() and out is not None and out.exists():
            print(f"OK {asset['path']} (archive discarded after extraction; {out.relative_to(ROOT)} stands for it)")
            continue
        if target.exists() or args.verify_only:
            verify(target, asset)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".download") as temp:
                subprocess.run([
                    "curl", "--fail", "--silent", "--show-error", "--location",
                    "--connect-timeout", "10", "--max-time", str(max(300, asset["bytes"] // 200_000)), "--retry", "2",
                    "--output", temp.name, asset["url"],
                ], check=True)
                verify(Path(temp.name), asset)
                os.link(temp.name, target)  # publish verified bytes only
        print(f"OK {asset['path']}")
        if out is not None and not args.verify_only:
            if not out.exists():
                with zipfile.ZipFile(target) as z:
                    z.extractall(out, [n for n in z.namelist() if wanted(n, asset.get("members"))])
                print(f"   unzipped -> {out.relative_to(ROOT)}")
            if asset.get("discard"):
                target.unlink()
                print(f"   discarded {asset['path']}")
    print(f"Verified {len(manifest['assets'])} assets.")


if __name__ == "__main__":
    main()
