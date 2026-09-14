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

from build_ice import HOLE_KM2, fill_holes, polar_smooth  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
