"""Checks for scripts/present_water.py: the rules that turn Natural Earth's river lines into
the present grid's routing guide. Needs pyshp and numpy (requirements-processing.txt);
run with `.venv/bin/python tests/present_water_check.py`."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import numpy as np  # noqa: E402
import shapefile  # noqa: E402

from present_water import EXTEND_CELLS, rivers  # noqa: E402

HEIGHT, WIDTH = 64, 128


def lonlat(col, row):
    return (col + 0.5) / WIDTH * 360.0 - 180.0, 90.0 - (row + 0.5) / HEIGHT * 180.0


class RiverLineTests(unittest.TestCase):
    def setUp(self):
        # Land west of column 100, sea east of it; ground rising to the north-west.
        rows, cols = np.mgrid[0:HEIGHT, 0:WIDTH]
        self.z = np.where(cols < 100, 100.0 + (100 - cols) * 5.0 + (32 - rows) * 2.0, -50.0)
        self.folder = tempfile.TemporaryDirectory()
        writer = shapefile.Writer(str(Path(self.folder.name) / "rivers"), shapeType=shapefile.POLYLINE)
        writer.field("scalerank", "N"); writer.field("featurecla", "C"); writer.field("name", "C")
        # A main river along row 32 from column 20 to 90, ending ten cells short of the sea.
        writer.line([[lonlat(c, 32) for c in range(20, 91)]]); writer.record(1, "River", "Main")
        # A tributary ending on the main river: its lower end joins at column 60.
        writer.line([[lonlat(c, 32 - (60 - c)) for c in range(40, 61)]]); writer.record(6, "River", "Side")
        # Another river passing the main river's upper end within a texel and going its own way.
        writer.line([[lonlat(c, 31) for c in range(10, 25)] + [lonlat(24, r) for r in range(30, 5, -1)]]); writer.record(6, "River", "Other")
        writer.close()
        self.burn = rivers(Path(self.folder.name) / "rivers", WIDTH, HEIGHT, self.z)

    def tearDown(self):
        self.folder.cleanup()

    def test_the_main_river_is_carried_on_to_the_sea(self):
        self.assertTrue((self.burn[32, 20:91] > 0).all(), "the line itself")
        self.assertGreater((self.burn[:, 91:100] > 0).sum(), 0, "and cells beyond its end")
        rows = np.argwhere(self.burn[:, 99] > 0)[:, 0]
        self.assertTrue(len(rows) and abs(rows[0] - 32) <= EXTEND_CELLS, "reaching the coast")
        self.assertEqual(self.burn[32, 50], 1.0, "rank 1 carries size 1")

    def test_a_tributary_keeps_its_junction(self):
        self.assertGreater(self.burn[31, 59], 0.0, "the tributary's cell next to the junction survives")

    def test_a_river_passing_a_divide_is_broken(self):
        self.assertTrue((self.burn[31, 19:22] == 0).all(), "the smaller river gives way where it passes the main's upper end")
        self.assertTrue((self.burn[31, 10:18] > 0).all(), "but keeps its own course elsewhere")
        self.assertTrue((self.burn[6:28, 24] > 0).any())


if __name__ == "__main__":
    unittest.main()
