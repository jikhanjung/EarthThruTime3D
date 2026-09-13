"""Pack the runtime bundle: the derived land fields, their piece reports, and the
PaleoDEM elevation textures.

The original PALEOMAP JPEGs are deliberately not packed. The licence permits personal,
teaching, research and scientific-publication use with credit and names websites among
the commercial uses needing the author's written consent, so the published maps stay on
the build host. What ships is this project's own measurement of them.
"""
import hashlib
import json
import shutil
import sys
import tarfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE = BASE_DIR / "data/derived/segmentation"
SUFFIXES = ("field.png", "pieces.json")


def digest(path):
    reader = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            reader.update(block)
    return reader.hexdigest()


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else (BASE_DIR / "deploy/DOCKER_VERSION").read_text().strip()
    catalogue = json.loads((BASE_DIR / "sources/scotese-earth-history.json").read_text())
    staging = BASE_DIR / ".build" / f"runtime-{version}"
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "segmentation").mkdir(parents=True)

    files = []

    def pack(source, map_id, hint):
        if not source.exists():
            raise SystemExit(f"Missing derived file: {source}. Run {hint}.")
        target = staging / "segmentation" / source.name
        shutil.copy2(source, target)
        files.append({"path": f"segmentation/{source.name}", "bytes": target.stat().st_size,
                      "sha256": digest(target), "map_id": map_id})

    for item in catalogue["maps"]:
        stem = Path(item["image"]["path"]).stem
        for suffix in SUFFIXES:
            pack(SOURCE / f"{stem}-{suffix}", item["id"], "scripts/segment_landmass.py")
    # The elevation series: one texture per PaleoDEM slice. The 650 Ma stop it starts
    # with is the Scotese field packed above.
    slices = json.loads((BASE_DIR / "sources/paleodem-slices.json").read_text())["slices"]
    for item in slices:
        pack(SOURCE / f"{item['id']}-field.png", item["id"], "scripts/build_paleodem.py")

    manifest = {"schema_version": 1, "version": version, "files": files,
                "contains_source_maps": False,
                "note": ("Derived land fields and piece reports produced by "
                         "scripts/segment_landmass.py from the PALEOMAP maps, and the "
                         "PaleoDEM textures produced by scripts/build_paleodem.py "
                         "(Scotese & Wright 2018, CC BY 4.0). The original images are "
                         "not included.")}
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    dist = BASE_DIR / "dist"
    dist.mkdir(exist_ok=True)
    archive = dist / f"earththrutime3d-data-{version}.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for entry in sorted(staging.rglob("*")):
            # Directories are listed by rglob too; adding them recursively would pack
            # every file twice.
            bundle.add(entry, arcname=str(entry.relative_to(staging)), recursive=False)
    total = sum(file["bytes"] for file in files)
    print(f"Packed {len(files)} files ({total} bytes) into {archive.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
