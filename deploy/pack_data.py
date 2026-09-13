"""Pack the runtime bundle: the derived land fields, their piece reports, and the
packed EarthByte plate model.

Two datasets travel together but stay labelled. The original PALEOMAP JPEGs are
deliberately not packed: that licence permits personal, teaching, research and
scientific-publication use with credit and names websites among the commercial uses
needing the author's written consent, so the published maps stay on the build host and
only this project's own measurement of them ships. The plate model is EarthByte's, under
CC BY with a citation requirement, and ships whole.
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
PLATES = BASE_DIR / "data/derived/plates"
# Every model has rotations and continents; only some ship a separate coastline layer.
PLATE_LAYERS = ("rotations.json", "continents.json")
OPTIONAL_PLATE_LAYERS = ("coastlines.json",)


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
    for item in catalogue["maps"]:
        stem = Path(item["image"]["path"]).stem
        for suffix in SUFFIXES:
            source = SOURCE / f"{stem}-{suffix}"
            if not source.exists():
                raise SystemExit(f"Missing derived file: {source}. Run scripts/segment_landmass.py.")
            target = staging / "segmentation" / source.name
            shutil.copy2(source, target)
            files.append({"path": f"segmentation/{source.name}", "bytes": target.stat().st_size,
                          "sha256": digest(target), "map_id": item["id"]})

    (staging / "plates").mkdir()
    packed = sorted(path.stem for path in (BASE_DIR / "sources/plate-models").glob("*.json"))
    if not packed:
        raise SystemExit("No plate model manifests under sources/plate-models/.")
    for model in packed:
        (staging / "plates" / model).mkdir()
        for name in PLATE_LAYERS + OPTIONAL_PLATE_LAYERS:
            source = PLATES / model / name
            if not source.exists():
                if name in OPTIONAL_PLATE_LAYERS:
                    continue
                raise SystemExit(f"Missing plate file: {source}. Run scripts/pack_plates.py.")
            target = staging / "plates" / model / name
            shutil.copy2(source, target)
            files.append({"path": f"plates/{model}/{name}", "bytes": target.stat().st_size,
                          "sha256": digest(target), "dataset": model})

    manifest = {"schema_version": 2, "version": version, "files": files,
                "contains_source_maps": False,
                "note": ("Derived land fields and piece reports produced by "
                         "scripts/segment_landmass.py from the PALEOMAP maps, whose "
                         "original images are not included, plus the EarthByte "
                         "plate models packed by scripts/pack_plates.py, each under "
                         "its own Creative Commons Attribution licence.")}
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    dist = BASE_DIR / "dist"
    dist.mkdir(exist_ok=True)
    archive = dist / f"earththrutime3d-data-{version}.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for entry in sorted(staging.rglob("*")):
            bundle.add(entry, arcname=str(entry.relative_to(staging)))
    total = sum(file["bytes"] for file in files)
    print(f"Packed {len(files)} files ({total} bytes) into {archive.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
