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

from scripts.segment_paleoatlas import (MAX_PLATE_ID, cap_radius, cell_weights,  # noqa: E402
                                        classify, group_lookup, group_name, pieces_of,
                                        plate_groups, spherical_centroid, wrapped_labels)
from scripts.atlas_motions import carry, separation  # noqa: E402

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



class PlateGroupTests(unittest.TestCase):
    def setUp(self):
        self.groups = plate_groups()
        self.lookup = group_lookup(self.groups)

    def key(self, plate):
        index = self.lookup[plate]
        return None if index < 0 else self.groups[index]["key"]

    def test_specific_ids_win_over_family_ranges(self):
        self.assertEqual(self.key(102), "greenland")
        self.assertEqual(self.key(101), "north-america")
        self.assertEqual(self.key(107), "africa")
        self.assertEqual(self.key(230), "caribbean")
        self.assertEqual(self.key(262), "south-america")
        self.assertEqual(self.key(402), "kazakhstania")
        self.assertEqual(self.key(401), "siberia")
        self.assertEqual(self.key(503), "arabia")
        self.assertEqual(self.key(702), "madagascar")
        self.assertEqual(self.key(709), "africa")
        self.assertEqual(self.key(806), "zealandia")
        self.assertEqual(self.key(802), "antarctica")
        self.assertEqual(self.key(801), "australia")

    def test_oceanic_plates_belong_to_no_group(self):
        for plate in (0, 901, 902, 985):
            self.assertIsNone(self.key(plate))
        self.assertEqual(len(self.lookup), MAX_PLATE_ID)

    def test_older_names_apply_at_and_before_their_age(self):
        group = next(group for group in self.groups if group["key"] == "north-america")
        self.assertEqual(group_name(group, 100.0)[0], "북아메리카")
        self.assertEqual(group_name(group, 320.0)[0], "로렌시아")
        self.assertEqual(group_name(group, 450.0)[1], "Laurentia")

    def test_regions_follow_the_plates_under_a_piece(self):
        land = np.zeros((900, 1800), dtype=bool)
        land[300:500, 600:1000] = True
        plates = np.zeros((900, 1800), dtype=np.int32)
        plates[300:500, 600:800] = 701
        plates[300:500, 800:1000] = 201
        _, pieces = pieces_of(land, plates, 200.0, self.groups)
        self.assertEqual(len(pieces), 1)
        regions = {region["group"]: region for region in pieces[0]["regions"]}
        self.assertEqual(set(regions), {"africa", "south-america"})
        self.assertLess(regions["africa"]["centroid"][0], regions["south-america"]["centroid"][0])
        self.assertEqual({name["name"] for name in pieces[0]["names"]}, {"아프리카", "남아메리카"})
        labels = {name["name"]: name for name in pieces[0]["names"]}
        # Each name sits inside its own half, not on the shared border.
        self.assertLess(labels["아프리카"]["lon"], -180 + 800 * 0.2)
        self.assertGreater(labels["남아메리카"]["lon"], -180 + 800 * 0.2)

    def test_close_names_yield_to_the_larger_region_and_umbrellas_are_unnamed(self):
        land = np.zeros((900, 1800), dtype=bool)
        land[300:520, 600:700] = True
        land[300:520, 1300:1500] = True
        plates = np.zeros((900, 1800), dtype=np.int32)
        # Each label sits in the middle of its own region: North China's at column 640,
        # Amuria's at 690, ten degrees apart at 0.2 degrees a column.
        plates[300:520, 600:680] = 604      # North China, large
        plates[300:520, 680:700] = 628      # Amuria, small and right beside it
        plates[300:520, 1300:1500] = 650    # an umbrella east-asia block far away
        _, pieces = pieces_of(land, plates, 10.0, self.groups)
        names = {name["name"]: name for piece in pieces for name in piece["names"]}
        self.assertTrue(names["북중국"]["display"])
        self.assertFalse(names["아무리아"]["display"])
        self.assertNotIn("동아시아 지괴", names)
        moving = {region["group"] for piece in pieces for region in piece["regions"]}
        self.assertIn("east-asia", moving, "an unnamed umbrella still has a region to move")


class MotionTests(unittest.TestCase):
    def setUp(self):
        try:
            from scripts.measure_longitude_offsets import PackedModel
            self.model = PackedModel("paleomap2016")
        except FileNotFoundError:
            self.skipTest("paleomap2016 has not been packed in this checkout")

    def test_a_point_carried_to_its_own_age_stays_put(self):
        point = carry(self.model, 701, (20.0, 5.0), 250.0, 250.0)
        self.assertLess(separation((20.0, 5.0), point), 1e-6)

    def test_carrying_there_and_back_returns_the_point(self):
        there = carry(self.model, 501, (78.0, -30.0), 100.0, 50.0)
        back = carry(self.model, 501, there, 50.0, 100.0)
        self.assertLess(separation((78.0, -30.0), back), 1e-6)
        self.assertGreater(separation((78.0, -30.0), there), 1.0, "India moves in 50 Myr")

    def test_an_unknown_plate_gives_no_target(self):
        self.assertIsNone(carry(self.model, 12345, (0.0, 0.0), 10.0, 0.0))


if __name__ == "__main__":
    unittest.main()
