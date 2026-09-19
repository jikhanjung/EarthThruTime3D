"""Checks for the Quaternary climate texture builder.

Kept out of the Django suite on purpose: it needs the tools in
requirements-processing.txt, which the web app does not depend on.
Run it with `.venv/bin/python tests/climate_check.py`.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import numpy as np  # noqa: E402

from build_climate import CLASS_STEP, RAIN_MISSING_MM, cover_class, encode, fill_nearest  # noqa: E402

OCEAN = -2147483648     # the source's fill value


class ClimateTextureTests(unittest.TestCase):
    def test_every_biome4_code_has_one_class_and_the_sea_has_none(self):
        codes = np.array([[OCEAN, 0] + list(range(1, 29))])
        cover = cover_class(codes)[0]
        self.assertEqual(list(cover[:2]), [-1, -1])
        self.assertTrue((cover[2:] >= 0).all())
        self.assertEqual([int(cover[2 + code - 1]) for code in (21, 13, 20, 12, 1, 11, 22, 28)],
                         [0, 1, 2, 3, 4, 4, 5, 6])

    def test_the_fill_crosses_the_date_line(self):
        values = np.zeros((1, 360), np.int16); missing = np.ones((1, 360), bool)
        values[0, 359] = 7; missing[0, 359] = False      # the only kept cell is the last column
        values[0, 100] = 3; missing[0, 100] = False
        filled = fill_nearest(values, missing)
        self.assertEqual(int(filled[0, 0]), 7)           # one step west across the wrap, not 100 east
        self.assertEqual(int(filled[0, 101]), 3)

    def test_encoding_fills_the_sea_and_reads_15000_as_missing(self):
        biome = np.full((4, 8), OCEAN); rain = np.full((4, 8), np.nan)
        biome[0, 2], rain[0, 2] = 21, 50.0               # desert, south row
        biome[3, 5], rain[3, 5] = 28, RAIN_MISSING_MM    # ice, north row, precipitation masked
        rgb = encode(biome, rain)
        self.assertEqual(rgb.shape, (4, 8, 3))
        self.assertEqual(int(rgb[0, 5, 0]), 6 * CLASS_STEP)             # north first
        self.assertEqual(int(rgb[3, 2, 0]), 0)
        self.assertEqual(int(rgb[3, 2, 1]), round((50 / 8000) ** 0.5 * 255))
        self.assertEqual(int(rgb[0, 5, 1]), int(rgb[3, 2, 1]))         # filled, not 15000
        self.assertTrue((rgb[..., 1] < 255).all())


if __name__ == "__main__":
    unittest.main()
