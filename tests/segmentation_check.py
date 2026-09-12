"""Checks for the landmass segmentation helpers.

Kept out of the Django suite on purpose: it needs the tools in
requirements-processing.txt, which the web app does not depend on.
Run it with `.venv/bin/python tests/segmentation_check.py`.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from core.globe import BOUNDS  # noqa: E402
from scripts.segment_landmass import ellipse_mask, hsv, inverse_mollweide  # noqa: E402

BOUNDS_000 = BOUNDS["000"]


def forward(longitude, latitude, bounds):
    """The pixel mapping used by static/core/projection.js, in degrees."""
    longitude, latitude = np.radians(longitude), np.radians(latitude)
    theta = np.arcsin(np.clip(latitude / (np.pi / 2), -1, 1))
    for _ in range(60):
        theta -= ((2 * theta + np.sin(2 * theta) - np.pi * np.sin(latitude))
                  / (2 + 2 * np.cos(2 * theta)))
    left, top, right, bottom = bounds
    x = longitude / np.pi * np.cos(theta)
    return ((left + right) / 2 + x * (right - left) * 0.495,
            (top + bottom) / 2 - np.sin(theta) * (bottom - top) * 0.495)


class InverseProjectionTests(unittest.TestCase):
    def test_round_trips_through_the_forward_mapping(self):
        for longitude, latitude in [(0, 0), (90, 45), (-120, -30), (179, 10), (0, 85)]:
            col, row = forward(longitude, latitude, BOUNDS_000)
            back_lon, back_lat = inverse_mollweide(col, row, BOUNDS_000)
            self.assertAlmostEqual(back_lon, longitude, places=2)
            self.assertAlmostEqual(back_lat, latitude, places=2)

    def test_centre_and_poles_land_where_expected(self):
        left, top, right, bottom = BOUNDS_000
        centre = inverse_mollweide((left + right) / 2, (top + bottom) / 2, BOUNDS_000)
        self.assertAlmostEqual(centre[0], 0.0, places=6)
        self.assertAlmostEqual(centre[1], 0.0, places=6)
        self.assertGreater(inverse_mollweide((left + right) / 2, top, BOUNDS_000)[1], 88.0)
        self.assertLess(inverse_mollweide((left + right) / 2, bottom, BOUNDS_000)[1], -88.0)


class MaskTests(unittest.TestCase):
    def test_ellipse_mask_is_inset_and_centred(self):
        mask = ellipse_mask((467, 720), BOUNDS_000)
        left, top, right, bottom = BOUNDS_000
        self.assertTrue(mask[int((top + bottom) / 2), int((left + right) / 2)])
        self.assertFalse(mask[int((top + bottom) / 2), left])
        self.assertFalse(mask[0, 0])

    def test_hsv_matches_known_colours(self):
        rgb = np.array([[[52, 152, 227], [237, 210, 139], [255, 255, 255]]], dtype=np.float32)
        hue, saturation, value = hsv(rgb)
        self.assertAlmostEqual(float(hue[0, 0]), 206, delta=1)
        self.assertAlmostEqual(float(hue[0, 1]), 43, delta=1)
        self.assertAlmostEqual(float(saturation[0, 2]), 0.0, places=6)
        self.assertAlmostEqual(float(value[0, 2]), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
