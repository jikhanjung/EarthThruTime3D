"""PaleoMIST 1.0 (Gowan et al. 2021, sources/paleomist.json) read onto the texture grid.

The merged global grid holds `ice_thickness` (grounded ice, m), `sea_level` (the SELEN
sea-level change relative to the land, m, 0 at the present), `base_topography` and
`paleo_topography`, one step every STEP_KA thousand years from OLDEST_KA to the present,
on a latitude/longitude grid with both poles and both ends of the antimeridian. The
readers here hand a step's field back north-up on the 2048 x 1024 texture grid, so
scripts/build_ice.py and scripts/build_rivers.py read the source the same way.
"""
import json
import sys
from pathlib import Path

import netCDF4
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_paleodem import resample  # noqa: E402

MANIFEST = ROOT / "sources/paleomist.json"
STEP_KA = 2.5       # the reconstruction's interval
OLDEST_KA = 80.0    # its oldest step


def grid_path():
    manifest = json.loads(MANIFEST.read_text())
    asset = manifest["assets"][0]
    return (ROOT / asset["path"]).parent / asset["unzip"] / manifest["grid"]


def grid():
    return netCDF4.Dataset(grid_path())


def ages(data):
    """Each step's age in thousands of years, in the file's order."""
    return -np.asarray(data.variables["time"][:]) / 1000.0


def step(data, age_ka):
    """The index of the step at `age_ka`, or a SystemExit naming the steps there are."""
    steps = ages(data)
    index = int(np.argmin(np.abs(steps - age_ka)))
    if abs(steps[index] - age_ka) > 1e-6:
        raise SystemExit(f"PaleoMIST has no step at {age_ka} ka; its steps are every {STEP_KA} kyr to {steps.max():g}")
    return index


def field(data, name, index):
    """One variable at one step, north-up, gaps as 0."""
    values = np.nan_to_num(np.asarray(data.variables[name][index], dtype=np.float64))
    return values if np.asarray(data.variables["lat"][:])[0] > 0 else values[::-1]


def on_texture(values, width):
    """A north-up source field resampled onto the texture grid."""
    return resample(values, width)
