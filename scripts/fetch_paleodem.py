#!/usr/bin/env python3
"""Fetch or verify pinned CC BY archives: the PaleoDEMs by default, or another manifest.

Manifests: sources/paleodem.json (Scotese & Wright 2018 elevation grids) and
sources/paleotemp.json (Scotese 2021 temperature maps); pass --manifest to choose.

An asset with `unzip` is extracted beside the archive; `members`, a list of glob
patterns, limits the extraction to the files that match; `discard` deletes the archive
once it is extracted, for one too large to keep (sources/paleomist.json), after which
a receipt binds the extracted file hashes to the verified archive. --verify-only
checks those files; a directory alone is never accepted as verification.
"""

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
from pathlib import Path, PurePosixPath
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


RECEIPT = ".verified-extraction.json"


def extraction_path(out, name):
    relative = PurePosixPath(name)
    path = (out / name).resolve()
    if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(out.resolve()):
        raise ValueError("Unsafe extracted source path")
    return path


def verify_extracted(out, asset):
    receipt = json.loads((out / RECEIPT).read_text())
    if (receipt.get("archive_sha256") != asset["sha256"]
            or receipt.get("members") != asset.get("members") or not receipt.get("files")):
        raise ValueError("Extracted source receipt does not match the pinned archive")
    for entry in receipt["files"]:
        verify(extraction_path(out, entry["path"]), entry)


def extract_discardable(target, out, asset):
    # Publish a complete verified directory only. A failed extraction leaves the archive.
    with tempfile.TemporaryDirectory(dir=out.parent, prefix=".extract-") as temporary:
        staging = Path(temporary)
        records = []
        with zipfile.ZipFile(target) as archive:
            for info in archive.infolist():
                if not wanted(info.filename, asset.get("members")):
                    continue
                path = extraction_path(staging, info.filename)
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, path.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                with path.open("rb") as handle:
                    digest = hashlib.file_digest(handle, "sha256").hexdigest()
                records.append({"path": info.filename, "bytes": info.file_size, "sha256": digest})
        if not records:
            raise ValueError("No source files matched the extraction filter")
        receipt = {"archive_sha256": asset["sha256"], "members": asset.get("members"), "files": records}
        if out.exists():
            # An older/partial folder cannot authorize deleting the last verified archive.
            for entry in records:
                verify(extraction_path(out, entry["path"]), entry)
            (out / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n")
        else:
            (staging / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n")
            staging.rename(out)
    verify_extracted(out, asset)
    target.unlink()


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
        out = (target.parent / asset["unzip"]).resolve() if "unzip" in asset else None
        if out is not None and not out.is_relative_to(SOURCES):
            raise ValueError("Extracted sources must stay inside data/sources")
        if asset.get("discard") and not target.exists() and out is not None and out.exists():
            verify_extracted(out, asset)
            print(f"OK {asset['path']} (verified extracted files in {out.relative_to(ROOT)})")
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
            if asset.get("discard"):
                extract_discardable(target, out, asset)
                print(f"   verified extraction and discarded {asset['path']}")
                continue
            if not out.exists():
                with zipfile.ZipFile(target) as z:
                    z.extractall(out, [n for n in z.namelist() if wanted(n, asset.get("members"))])
                print(f"   unzipped -> {out.relative_to(ROOT)}")
    print(f"Verified {len(manifest['assets'])} assets.")


if __name__ == "__main__":
    main()
