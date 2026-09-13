#!/usr/bin/env python3
"""Fetch or verify the pinned EarthByte plate model archive and its members.

Separate from the Scotese maps on purpose. That dataset is a set of published
pictures this project measures; this one is a rotation model that reconstructs
geometry. They have different authors, different licences and different limits, and
mixing them without saying which is which would misrepresent both.
"""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sources/earthbyte-merdith2021.json"
HOME = ROOT / "data/sources/earthbyte"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(path, expected_bytes, expected_hash, label):
    data = path.read_bytes()
    if len(data) != expected_bytes or digest(data) != expected_hash:
        raise ValueError(f"Differs from pinned manifest: {label}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true",
                        help="Check local files without network access")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    archive = manifest["archive"]
    target = (ROOT / archive["path"]).resolve()
    if not target.is_relative_to(HOME.resolve()):
        raise ValueError("The archive must stay inside the local source directory")

    if target.exists() or args.verify_only:
        verify(target, archive["bytes"], archive["sha256"], archive["path"])
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".download") as temp:
            subprocess.run([
                "curl", "--fail", "--silent", "--show-error", "--location",
                "--connect-timeout", "10", "--max-time", "300", "--retry", "2",
                "--output", temp.name, archive["url"],
            ], check=True)
            verify(Path(temp.name), archive["bytes"], archive["sha256"], archive["path"])
            # Publish verified bytes only; keep any existing file on mismatch.
            os.link(temp.name, target)
    print(f"OK {archive['path']}")

    extracted = HOME / archive["version"]
    extracted.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target) as bundle:
        for member in manifest["members"]:
            destination = extracted / member["name"]
            if not destination.exists() and not args.verify_only:
                # Read from the archive rather than trusting its paths on disk.
                data = bundle.read(archive["member_prefix"] + member["name"])
                if len(data) != member["bytes"] or digest(data) != member["sha256"]:
                    raise ValueError(f"Archive member differs from manifest: {member['name']}")
                destination.write_bytes(data)
            verify(destination, member["bytes"], member["sha256"], member["name"])
            print(f"OK {destination.relative_to(ROOT)}  {member['role']}")
    print(f"Verified the archive and {len(manifest['members'])} members.")
    print(f"Licence: {manifest['license']['name']}. Cite: {manifest['citation'][:60]}...")


if __name__ == "__main__":
    main()
