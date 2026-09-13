#!/usr/bin/env python3
"""Fetch or verify pinned CC BY archives: the PaleoDEMs by default, or another manifest.

Manifests: sources/paleodem.json (Scotese & Wright 2018 elevation grids) and
sources/paleotemp.json (Scotese 2021 temperature maps); pass --manifest to choose.
"""

import argparse
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
    data = path.read_bytes()
    if len(data) != asset["bytes"] or hashlib.sha256(data).hexdigest() != asset["sha256"]:
        raise ValueError(f"Source differs from pinned manifest: {asset['path']}")


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
        if target.exists() or args.verify_only:
            verify(target, asset)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".download") as temp:
                subprocess.run([
                    "curl", "--fail", "--silent", "--show-error", "--location",
                    "--connect-timeout", "10", "--max-time", "300", "--retry", "2",
                    "--output", temp.name, asset["url"],
                ], check=True)
                verify(Path(temp.name), asset)
                os.link(temp.name, target)  # publish verified bytes only
        print(f"OK {asset['path']}")
        if "unzip" in asset and not args.verify_only:
            out = target.parent / asset["unzip"]
            if not out.exists():
                with zipfile.ZipFile(target) as z:
                    z.extractall(out, [n for n in z.namelist() if not n.endswith(".gplates.cache") and not n.startswith("__MACOSX")])
                print(f"   unzipped -> {out.relative_to(ROOT)}")
    print(f"Verified {len(manifest['assets'])} assets.")


if __name__ == "__main__":
    main()
