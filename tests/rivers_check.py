"""Checks for the river builder's routing.

Kept out of the Django suite on purpose: it needs the tools in
requirements-processing.txt, which the web app does not depend on.
Run it with `.venv/bin/python tests/rivers_check.py`.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import numpy as np  # noqa: E402

from build_rivers import CONE_RADIUS, CONE_SLOPE, RIVER_KM2, cell_geometry, directions, fill_sinks, river_field, route  # noqa: E402

HEIGHT, WIDTH = 64, 128


def island(centre_col=64):
    """A cone of land 1,000 m high whose slopes reach the sea, with a pit on one flank."""
    rows, cols = np.mgrid[0:HEIGHT, 0:WIDTH]
    away = (cols - centre_col + WIDTH / 2) % WIDTH - WIDTH / 2     # columns wrap
    z = 1000.0 - 40.0 * np.hypot(rows - 32, away / 2.0)
    z[24:28, (centre_col + 8) % WIDTH:(centre_col + 12) % WIDTH or WIDTH] -= 300.0   # a closed pit, 300 m deep
    return z


def reaching_the_sea(z):
    land = z > 0
    drained = route(z, land)
    surface = fill_sinks(z, land)
    down, _ = directions(surface, land)
    mouths = land & (down >= 0) & ~land.ravel()[np.maximum(down, 0)].reshape(land.shape)
    _, _, area = cell_geometry(z.shape)
    return drained, drained[mouths].sum(), area[land].sum()


class RoutingTests(unittest.TestCase):
    def test_every_drop_reaches_the_sea_and_the_pit_spills(self):
        z = island()
        drained, reached, total = reaching_the_sea(z)
        self.assertAlmostEqual(reached / total, 1.0, places=6)
        land = z > 0
        self.assertTrue((drained[land] >= 1.0).all())
        # water leaving the pit: some cell of its rim drains at least the pit's own cells
        pit = np.zeros_like(land)
        pit[24:28, 72:76] = True
        rim = np.zeros_like(land)
        rim[23:29, 71:77] = True
        rim &= ~pit
        _, _, area = cell_geometry(z.shape)
        self.assertGreater(drained[rim].max(), area[pit].sum())

    def test_an_island_across_the_antimeridian_drains_as_one(self):
        drained_centre, reached_centre, total_centre = reaching_the_sea(island(64))
        drained_seam, reached_seam, total_seam = reaching_the_sea(island(0))
        self.assertAlmostEqual(total_seam, total_centre)
        self.assertAlmostEqual(reached_seam / total_seam, 1.0, places=6)
        self.assertAlmostEqual(drained_seam.max(), drained_centre.max(), delta=drained_centre.max() * 0.02)

    def test_field_does_not_copy_between_north_and_south_edges(self):
        land = np.ones((HEIGHT, WIDTH), bool)
        for row, opposite in [(0, slice(-CONE_RADIUS, None)), (-1, slice(0, CONE_RADIUS))]:
            with self.subTest(row=row):
                drained = np.zeros((HEIGHT, WIDTH))
                drained[row, 64] = 1e7
                field = river_field(drained, land)
                self.assertEqual(int(field[row, 64]), 255)
                self.assertTrue((field[opposite] == 0).all())

    def test_field_still_wraps_across_longitude_seam(self):
        land = np.ones((HEIGHT, WIDTH), bool)
        drained = np.zeros((HEIGHT, WIDTH))
        drained[32, 0] = 1e7
        field = river_field(drained, land)
        self.assertEqual(field[32, -1], field[32, 1])
        self.assertGreater(field[32, -1], 0)

    def test_a_lowered_sea_routes_over_the_exposed_shelf(self):
        z = island()
        shelf = (z > -130) & ~(z > 0)
        self.assertGreater(shelf.sum(), 0)
        low = route(z, z > -130)
        self.assertTrue((low[shelf] > 0).all(), 'every shelf cell drains something')
        self.assertGreater(low.max(), route(z, z > 0).max(), 'the island drains more land at the lowstand')

    def test_the_field_is_a_cone_the_size_of_its_river(self):
        land = np.ones((HEIGHT, WIDTH), bool)
        drained = np.full((HEIGHT, WIDTH), RIVER_KM2 / 10.0)
        drained[32, 64] = 1e5     # size 0.5 over the 10^3..10^7 span
        field = river_field(drained, land) / 255.0
        self.assertAlmostEqual(field[32, 64], 0.5, delta=0.01)
        self.assertAlmostEqual(field[32, 65], 0.5 - CONE_SLOPE, delta=0.01)
        self.assertEqual(field[32, 64 + CONE_RADIUS + 1], 0.0)
        self.assertEqual(field[10, 10], 0.0)


if __name__ == "__main__":
    unittest.main()
