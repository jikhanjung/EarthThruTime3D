"""Checks for the 2016 PaleoAtlas segmentation helpers.

Kept out of the Django suite, like tests/segmentation_check.py: it needs the tools in
requirements-processing.txt. Run it with `.venv/bin/python tests/paleoatlas_check.py`.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import numpy as np  # noqa: E402

from scripts.segment_paleoatlas import (cap_radius, cell_weights, classify,  # noqa: E402
                                        pieces_of, spherical_centroid, wrapped_labels)

OCEAN = (20, 60, 100)
SHELF = (150, 205, 235)
LAND = (110, 140, 70)
ICE = (225, 228, 232)


def image(height, width, fill):
    return np.tile(np.array(fill, dtype=np.float32), (height, width, 1))


class ClassifyTests(unittest.TestCase):
    def test_deep_ocean_and_shelf_are_sea_and_green_is_land(self):
        rgb = image(60, 120, OCEAN)
        rgb[10:50, 10:50] = SHELF
        rgb[15:45, 60:110] = LAND
        land, _ = classify(rgb, np.zeros((60, 120), dtype=bool))
        self.assertFalse(land[30, 30])
        self.assertTrue(land[30, 85])
        self.assertFalse(land[5, 5])

    def test_ice_is_land_only_on_continental_crust(self):
        rgb = image(60, 120, OCEAN)
        rgb[10:50, 10:50] = ICE
        rgb[10:50, 70:110] = ICE
        continental = np.zeros((60, 120), dtype=bool)
        continental[:, 60:] = True
        land, _ = classify(rgb, continental)
        self.assertFalse(land[30, 30], "sea ice beyond the polygons stays sea")
        self.assertTrue(land[30, 90], "an ice sheet on a continent is land")

    def test_land_across_the_antimeridian_survives_cleaning_as_one_piece(self):
        rgb = image(90, 180, OCEAN)
        rgb[30:60, :20] = LAND
        rgb[30:60, -20:] = LAND
        land, _ = classify(rgb, np.zeros((90, 180), dtype=bool))
        self.assertTrue(land[45, 0] and land[45, -1], "cleaning must not eat the seam")
        _, count = wrapped_labels(land)
        self.assertEqual(count, 1)

    def test_land_at_the_pole_survives_cleaning(self):
        rgb = image(90, 180, OCEAN)
        rgb[-10:, :] = LAND
        land, _ = classify(rgb, np.zeros((90, 180), dtype=bool))
        self.assertTrue(land[-1, 90])

    def test_thin_black_line_over_land_is_refilled(self):
        rgb = image(60, 120, LAND)
        rgb[:, 60] = (0, 0, 0)
        land, overprint = classify(rgb, np.zeros((60, 120), dtype=bool))
        self.assertTrue(overprint[30, 60])
        self.assertTrue(land[30, 60])


class GeometryTests(unittest.TestCase):
    def test_piece_touching_both_edges_is_one_piece(self):
        land = np.zeros((20, 40), dtype=bool)
        land[5:15, :4] = True
        land[5:15, -4:] = True
        land[5:15, 18:22] = True
        _, count = wrapped_labels(land)
        self.assertEqual(count, 2)

    def test_centroid_across_the_antimeridian_is_near_180(self):
        height, width = 180, 360
        rows, cols = np.mgrid[80:100, 0:360]
        chosen = (cols < 10) | (cols >= 350)
        weights = cell_weights(height, width)[rows[chosen], cols[chosen]]
        longitude, latitude = spherical_centroid(rows[chosen], cols[chosen], weights, width, height)
        self.assertGreater(abs(longitude), 179.0)
        self.assertAlmostEqual(latitude, 0.0, places=1)

    def test_cap_radius_matches_hemisphere_and_nothing(self):
        self.assertAlmostEqual(cap_radius(0.5), 90.0, places=6)
        self.assertAlmostEqual(cap_radius(0.0), 0.0, places=6)

    def test_slivers_are_dropped_and_blocks_are_kept(self):
        land = np.zeros((900, 1800), dtype=bool)
        land[400:460, 800:900] = True     # a solid block
        land[100:102, 100:900] = True     # a two-pixel coastline sliver
        labels, pieces = pieces_of(land)
        self.assertEqual(len(pieces), 1)
        self.assertTrue(labels[430, 850] > 0)
        self.assertEqual(labels[101, 500], 0)


if __name__ == "__main__":
    unittest.main()
