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
ATLAS_SOURCE = BASE_DIR / "data/derived/paleoatlas"
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


def pack_elevation(dem, dem_source, staging, files):
    """Stage the elevation series; scripts/build_paleodem.py writes it."""
    (staging / "paleodem").mkdir()
    for item in dem["maps"]:
        source = dem_source / f"{item['id']}-field.png"
        if not source.exists():
            raise SystemExit(f"Missing derived file: {source}. Run scripts/build_paleodem.py.")
        target = staging / "paleodem" / source.name
        shutil.copy2(source, target)
        files.append({"path": f"paleodem/{source.name}", "bytes": target.stat().st_size,
                      "sha256": digest(target), "map_id": item["id"]})
    # Climate over the grids: one temperature texture per grid and the global mean curve
    # (Scotese 2021, CC BY 4.0), produced by scripts/build_paleotemp.py.
    for item in dem["maps"]:
        source = dem_source / f"{item['id']}-temp.png"
        if not source.exists():
            raise SystemExit(f"Missing derived file: {source}. Run scripts/build_paleotemp.py.")
        target = staging / "paleodem" / source.name
        shutil.copy2(source, target)
        files.append({"path": f"paleodem/{source.name}", "bytes": target.stat().st_size,
                      "sha256": digest(target), "map_id": item["id"]})
    curve = dem_source / "paleotemp-curve.json"
    if not curve.exists():
        raise SystemExit(f"Missing {curve}. Run scripts/build_paleotemp.py.")
    shutil.copy2(curve, staging / "paleodem" / curve.name)
    files.append({"path": "paleodem/paleotemp-curve.json",
                  "bytes": (staging / "paleodem" / curve.name).stat().st_size,
                  "sha256": digest(staging / "paleodem" / curve.name), "dataset": "paleotemp2021"})
    sea = dem_source / "sealevel-curve.json"
    if not sea.exists():
        raise SystemExit(f"Missing {sea}. Run scripts/build_sealevel.py.")
    shutil.copy2(sea, staging / "paleodem" / sea.name)
    files.append({"path": "paleodem/sealevel-curve.json",
                  "bytes": (staging / "paleodem" / sea.name).stat().st_size,
                  "sha256": digest(staging / "paleodem" / sea.name), "dataset": "sealevel"})


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

    # The 2016 PaleoAtlas fields, the default masks. Their rasters are never packed.
    atlas = json.loads((BASE_DIR / "sources/paleomap-atlas-2016.json").read_text())
    (staging / "paleoatlas").mkdir()
    for item in atlas["maps"]:
        for suffix in SUFFIXES:
            source = ATLAS_SOURCE / f"{item['id']}-{suffix}"
            if not source.exists():
                raise SystemExit(f"Missing derived file: {source}. Run scripts/segment_paleoatlas.py.")
            target = staging / "paleoatlas" / source.name
            shutil.copy2(source, target)
            files.append({"path": f"paleoatlas/{source.name}", "bytes": target.stat().st_size,
                          "sha256": digest(target), "map_id": item["id"]})
    motions = ATLAS_SOURCE / "motions.json"
    if not motions.exists():
        raise SystemExit(f"Missing {motions}. Run scripts/atlas_motions.py.")
    shutil.copy2(motions, staging / "paleoatlas" / motions.name)
    files.append({"path": "paleoatlas/motions.json",
                  "bytes": (staging / "paleoatlas" / motions.name).stat().st_size,
                  "sha256": digest(staging / "paleoatlas" / motions.name),
                  "dataset": "paleoatlas2016"})

    # The PaleoDEM elevation textures (Scotese & Wright 2018, CC BY 4.0): one per grid,
    # coastline distance in red and height in green and blue. Optional: a checkout that
    # has not built them ships a bundle without the series, and the page then offers no
    # link to it. Once the directory exists, every texture has to be there.
    dem = json.loads((BASE_DIR / "sources/paleodem-slices.json").read_text())
    dem_source = BASE_DIR / "data/derived/paleodem"
    if dem_source.exists():
        pack_elevation(dem, dem_source, staging, files)
    else:
        print(f"No {dem_source.relative_to(BASE_DIR)}: packing without the elevation series.")

    # The fossil-checked coastlines drawn over the 2016 masks.
    coast_dir = BASE_DIR / "data/derived/paleocoastlines"
    if not (coast_dir / "index.json").exists():
        raise SystemExit(f"Missing {coast_dir / 'index.json'}. Run scripts/pack_coastlines.py.")
    (staging / "paleocoastlines").mkdir()
    coast_index = json.loads((coast_dir / "index.json").read_text())
    for name in ["index.json"] + [entry["file"] for entry in coast_index["ages"]]:
        target = staging / "paleocoastlines" / name
        shutil.copy2(coast_dir / name, target)
        files.append({"path": f"paleocoastlines/{name}", "bytes": target.stat().st_size,
                      "sha256": digest(target), "dataset": "paleocoastlines2021"})

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
                         "scripts/segment_landmass.py from the 2002 PALEOMAP maps and by "
                         "scripts/segment_paleoatlas.py from the 2016 PaleoAtlas, whose "
                         "original images are not included, plus the "
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
