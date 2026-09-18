"""Checks for the ice mask builder's helpers.

Kept out of the Django suite on purpose: it needs the tools in
requirements-processing.txt, which the web app does not depend on.
Run it with `.venv/bin/python tests/ice_check.py`.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import numpy as np  # noqa: E402

from build_ice import (HOLE_KM2, MODEL_REACH_DEGREES, WGS84_A, WGS84_E2, distance_field,  # noqa: E402
                       fill_holes, held_levels, model_fields, model_footprint, modelled,
                       polar_laea_inverse, polar_smooth)
import build_ice  # noqa: E402


class HeldLevelTests(unittest.TestCase):
    def test_level_is_the_running_minimum_and_marks_the_ages_that_lower_it(self):
        # The stack starts above today's level, which counts as 0 m; a rise back toward the
        # present holds the lower level and does not lower it again.
        levels = {1: 7.7, 2: -3.0, 3: -1.0, 4: -8.0}
        self.assertEqual(held_levels(levels, ages=range(1, 5)),
                         [(1, 0.0, False), (2, -3.0, True), (3, -3.0, False), (4, -8.0, True)])


class FakeGrid:
    """A PaleoMIST-shaped grid, 1 degree, south-up as the file is, with two steps: a sheet
    that shrinks by ten degrees of longitude from the older step to the younger."""
    def __init__(self):
        lat = np.arange(-90.0, 91.0)
        lon = np.arange(-180.0, 181.0)
        older = np.zeros((181, 361)); older[140:170, 60:130] = 2000.0     # 50-79 N, 120-51 W
        younger = np.zeros((181, 361)); younger[140:170, 70:120] = 1500.0
        antarctic = np.zeros((181, 361)); antarctic[0:20, :] = 3000.0
        # The sea's change relative to the land: 100 m of fall everywhere at the older step
        # plus 300 m of depression under the sheet, 40 m and 100 m at the younger, over an
        # ocean that is the southern half of the grid; the ocean mean is the fall.
        bed = np.where(np.arange(181)[:, None] < 90, -4000.0, 500.0) * np.ones((181, 361))
        self.variables = {"time": np.array([-5000.0, -2500.0]), "lat": lat, "lon": lon,
                          "ice_thickness": np.stack([older + antarctic, younger + antarctic]),
                          "base_topography": np.stack([bed, bed]),
                          "sea_level": np.stack([-100.0 + 300.0 * (older > 0), -40.0 + 100.0 * (younger > 0)])}


class ModelSliceTests(unittest.TestCase):
    def test_model_ice_is_kept_only_within_reach_of_the_dated_margins(self):
        grounded = np.zeros((1024, 2048), np.uint8)
        grounded[:60, :] = 255                               # today's ice: an Antarctic band
        added = np.zeros((1024, 2048), bool)
        added[70:220, 340:730] = True                        # the dated margins' footprint, 50-77 N, 120-51 W
        footprint = model_footprint(added)
        px = int(MODEL_REACH_DEGREES / (360 / 2048))
        self.assertTrue(footprint[220 + px - 1, 500] and not footprint[220 + px + 2, 500])
        fields = model_fields(FakeGrid(), grounded, footprint, [2.5, 5.0])
        self.assertEqual(sorted(fields), [2.5, 5.0])
        # Inside the footprint the older step's wider sheet is ice and the younger's is not.
        self.assertGreaterEqual(fields[5.0][150, 360], 128)
        self.assertLess(fields[2.5][150, 360], 128)
        # The model's Antarctic ice reaches past today's band (rows 0-113 for 70-90 S) but
        # only today's is kept, so the slices stay at the present extent there.
        self.assertGreaterEqual(fields[5.0][30, 1000], 128)
        self.assertLess(fields[5.0][100, 1000], 128)

    def test_slices_between_steps_mix_the_bracketing_fields(self):
        import json
        import tempfile
        grounded = np.zeros((1024, 2048), np.uint8)
        added = np.zeros((1024, 2048), bool)
        added[70:220, 340:730] = True
        levels = {age: -10.0 * age for age in range(0, 6)}
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            slices, curve = modelled(grounded, added, levels, 26.0, out, youngest=2, oldest=5, data=FakeGrid())
            self.assertEqual(sorted(path.name for path in out.iterdir()),
                             [f"paleodem-0000-ice-low-{age}.png" for age in (3, 4, 5)])
            self.assertEqual([(s["age_ka"], s["level_m"], s["lowers"], s["source"]) for s in slices],
                             [(3, -30.0, False, "paleomist"), (4, -40.0, False, "paleomist"), (5, -50.0, False, "paleomist")])
            self.assertEqual(curve, [[5.0, -100.0], [2.5, -40.0]])
            from PIL import Image
            red = {age: np.asarray(Image.open(out / f"paleodem-0000-ice-low-{age}.png"))[:, :, 0] for age in (3, 4, 5)}
        # The older step's sheet spans 120-51 W, the younger's 110-61 W; at 4 ka, 60% of the
        # way from 2.5 to 5, the west edge stands 60% of the way from 110 to 120 W.
        row = 150
        column = lambda west: int((180 - west) / 360 * 2048)  # noqa: E731
        self.assertGreaterEqual(red[5][row, column(119)], 128)
        self.assertLess(red[3][row, column(119)], 128)
        self.assertGreaterEqual(red[4][row, column(115)], 128)
        self.assertLess(red[4][row, column(118)], 128)
        self.assertEqual(build_ice.SLICES_KA[-1] + 1, 26)
        self.assertEqual(build_ice.MODEL_TO_KA, 80)


class FillHolesTests(unittest.TestCase):
    def test_small_gap_filled_large_gap_kept(self):
        mask = np.zeros((1024, 2048), bool)
        mask[300:500, 800:1200] = True
        mask[350:360, 900:910] = False      # a few thousand km2
        mask[400:480, 1000:1150] = False    # about 1.8 million km2
        filled = fill_holes(mask)
        self.assertTrue(filled[355, 905])
        self.assertFalse(filled[440, 1075])
        self.assertEqual(filled.sum(), mask.sum() + 100)

    def test_gap_across_the_antimeridian_is_enclosed(self):
        cap = np.zeros((1024, 2048), bool)
        cap[:100] = True
        cap[40:50, 2040:] = False
        cap[40:50, :8] = False
        filled = fill_holes(cap)
        self.assertTrue(filled[45, 2045] and filled[45, 3])

    def test_gap_open_to_an_open_polar_row_is_not_enclosed(self):
        cap = np.zeros((1024, 2048), bool)
        cap[:100] = True
        cap[0:30, 1000:1010] = False
        self.assertFalse(fill_holes(cap)[10, 1005])

    def test_cap_is_the_documented_size(self):
        self.assertEqual(HOLE_KM2, 500_000.0)


class SmoothTests(unittest.TestCase):
    def test_blur_widens_toward_the_poles_and_keeps_the_range(self):
        mask = np.zeros((1800, 3600), np.float32)
        mask[:, 1700:1900] = 1.0
        out = polar_smooth(mask)
        self.assertEqual(out.shape, mask.shape)
        self.assertTrue(0.0 <= out.min() and out.max() <= 1.0)
        # the same bar spreads farther along a row near the pole than at the equator
        self.assertGreater((out[5] > 0.01).sum(), (out[900] > 0.01).sum())
        self.assertAlmostEqual(out[900].sum(), 200.0, delta=1.0)


class ProjectionTests(unittest.TestCase):
    def test_polar_laea_round_trip(self):
        """Forward polar Lambert azimuthal equal-area on the ellipsoid (Snyder 1987, 24-15 to
        24-19), then the builder's inverse, lands back on the point."""
        import math
        e2 = WGS84_E2
        e = math.sqrt(e2)

        def q_of(phi):
            s = math.sin(phi)
            return (1 - e2) * (s / (1 - e2 * s * s) - math.log((1 - e * s) / (1 + e * s)) / (2 * e))
        q_pole = q_of(math.pi / 2)
        for lon, lat in [(5.3, 60.4), (25.0, 67.0), (-10.0, 52.0), (90.0, 78.0), (-179.0, 71.0)]:
            rho = WGS84_A * math.sqrt(q_pole - q_of(math.radians(lat)))
            x, y = rho * math.sin(math.radians(lon)), -rho * math.cos(math.radians(lon))
            back = polar_laea_inverse(np.array([[x, y]]))
            self.assertAlmostEqual(back[0, 0], lon, places=6)
            self.assertAlmostEqual(back[0, 1], lat, places=6)


if __name__ == "__main__":
    unittest.main()
