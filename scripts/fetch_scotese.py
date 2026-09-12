#!/usr/bin/env python3
"""Fetch or verify the pinned Scotese source assets without Django dependencies."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sources/scotese-earth-history.json"


def verify(path, asset):
    data = path.read_bytes()
    if len(data) != asset["bytes"] or hashlib.sha256(data).hexdigest() != asset["sha256"]:
        raise ValueError(f"Source differs from pinned manifest: {asset['path']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Check local files without network access")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    assets = [manifest["source_index"], manifest["license_page"]]
    assets.extend(asset for item in manifest["maps"] for asset in (item["page"], item["image"]))
    for asset in assets:
        target = (ROOT / asset["path"]).resolve()
        if not target.is_relative_to((ROOT / "data/sources/scotese").resolve()):
            raise ValueError("Asset must stay inside the local source directory")
        if target.exists() or args.verify_only:
            verify(target, asset)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".download") as temp:
                subprocess.run([
                    "curl", "--fail", "--silent", "--show-error", "--location",
                    "--connect-timeout", "10", "--max-time", "60", "--retry", "2",
                    "--output", temp.name, asset["url"],
                ], check=True)
                verify(Path(temp.name), asset)
                # Publish verified bytes only; retain existing files on mismatch.
                os.link(temp.name, target)
        print(f"OK {asset['path']}")
    print(f"Verified {len(assets)} assets ({len(manifest['maps'])} maps).")


if __name__ == "__main__":
    main()
