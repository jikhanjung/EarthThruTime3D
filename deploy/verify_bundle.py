"""Refuse to serve a runtime bundle that is not the one this image was built for.

Checks the manifest's version against the image, then every file's size and SHA-256.
A mismatched pair is a deployment mistake, and starting anyway would serve one
version's code against another's measurements.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

RUNTIME = Path(os.environ.get("RUNTIME_ROOT", "/runtime"))
EXPECTED = os.environ.get("EARTHTHRUTIME_VERSION", "").lstrip("v")


def digest(path):
    reader = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            reader.update(block)
    return reader.hexdigest()


def main():
    manifest_path = RUNTIME / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"No runtime bundle at {manifest_path}.")
    manifest = json.loads(manifest_path.read_text())
    found = str(manifest.get("version", "")).lstrip("v")
    if EXPECTED and found != EXPECTED:
        sys.exit(f"Bundle version {found} does not match image {EXPECTED}.")
    if manifest.get("contains_source_maps"):
        sys.exit("Bundle contains original maps; this deployment must not serve them.")
    for entry in manifest["files"]:
        path = RUNTIME / entry["path"]
        if not path.exists():
            sys.exit(f"Missing bundle file: {entry['path']}")
        if path.stat().st_size != entry["bytes"]:
            sys.exit(f"Size mismatch: {entry['path']}")
        if digest(path) != entry["sha256"]:
            sys.exit(f"Checksum mismatch: {entry['path']}")
    print(f"Runtime bundle {found}: {len(manifest['files'])} files verified.")


if __name__ == "__main__":
    main()
