"""Checks for scripts/present_water.py: the rules that turn Natural Earth's river lines into
the present grid's routing guide and HydroLAKES's polygons into its lakes, and the cache
that keeps them. Needs pyshp and numpy (requirements-processing.txt); run with
`.venv/bin/python tests/present_water_check.py`."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import numpy as np  # noqa: E402
import shapefile  # noqa: E402

import present_water  # noqa: E402
from present_water import EXTEND_CELLS, cache_key, lakes, load, lowest_path, rivers  # noqa: E402

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
        self.burn = rivers(shapefile.Reader(str(Path(self.folder.name) / "rivers")), WIDTH, HEIGHT, self.z)

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


class PathTests(unittest.TestCase):
    def test_a_connection_inside_the_limit_is_found(self):
        # jikhanjung's counterexample (devlog 090): four moves east reach the target over
        # ground no higher than 5, but keyed by the cell alone the search let a longer,
        # lower route claim the cells first and ran out of moves.
        z = np.array([[6, 3, 8, 3, 6, 6, 0, 6],
                      [5, 7, 2, 9, 0, 6, 3, 6],
                      [1, 6, 3, 5, 0, 5, 4, 7],
                      [6, 7, 3, 7, 5, 8, 1, 2],
                      [9, 1, 9, 1, 0, 3, 2, 3],
                      [8, 8, 6, 4, 4, 4, 3, 0]])
        target = np.zeros(z.shape, bool)
        target[2, 6] = True
        path = lowest_path(z, target, (2, 2), 4)
        self.assertIsNotNone(path, "a connection exists within four moves")
        self.assertEqual(len(path), 3, "the four-move route, without the target cell")
        self.assertEqual(max(z[cell] for cell in path), 5, "over the lowest ground a four-move route can")

    def test_the_lowest_route_wins_and_the_limit_holds(self):
        z = np.array([[0, 9, 0, 5, 5],
                      [0, 0, 0, 5, 5]])   # wide enough that the columns' wrap-around does not join the ends
        target = np.zeros(z.shape, bool)
        target[0, 2] = True
        self.assertEqual(lowest_path(z, target, (0, 0), 2), [(1, 1)], "around the ridge, as many moves")
        self.assertIsNone(lowest_path(z, target, (0, 0), 1), "and none within one move")


class LakeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        writer = shapefile.Writer(str(Path(self.folder.name) / "lakes"), shapeType=shapefile.POLYGON)
        writer.field("Lake_area", "N", decimal=1); writer.field("Depth_avg", "N", decimal=2)
        # jikhanjung's fixture (devlog 090): a lake with an island, its inner ring counter-clockwise;
        # and an islet far smaller than a texel.
        writer.poly([[(-90, -45), (-90, 45), (90, 45), (90, -45), (-90, -45)],
                     [(-30, -15), (30, -15), (30, 15), (-30, 15), (-30, -15)],
                     [(-60, 30), (-59.9, 30), (-59.9, 30.1), (-60, 30.1), (-60, 30)]]); writer.record(1000, 10)
        # A lake in two parts, the western one with an island, on ground the grid holds below its datum.
        writer.poly([[(100, -40), (100, -20), (140, -20), (140, -40), (100, -40)],
                     [(-170, 10), (-170, 40), (-120, 40), (-120, 10), (-170, 10)],
                     [(-160, 20), (-130, 20), (-130, 30), (-160, 30), (-160, 20)]]); writer.record(2000, 20)
        # Too small to count.
        writer.poly([[(150, 50), (150, 60), (170, 60), (170, 50), (150, 50)]]); writer.record(50, 30)
        # Smaller than a texel, with an island smaller still.
        writer.poly([[(160, -50), (160, -49.9), (160.1, -49.9), (160.1, -50), (160, -50)],
                     [(160.02, -49.98), (160.08, -49.98), (160.08, -49.92), (160.02, -49.92), (160.02, -49.98)]]); writer.record(150, 4)
        writer.close()
        z = np.ones((HEIGHT, WIDTH))
        z[:, :25] = -5.0
        self.depth, self.closed = lakes(shapefile.Reader(str(Path(self.folder.name) / "lakes")), WIDTH, HEIGHT, z)

    def tearDown(self):
        self.folder.cleanup()

    def test_an_island_stays_dry(self):
        self.assertEqual(self.depth[32, 64], 0.0, "the island's centre")
        self.assertEqual(self.depth[20, 40], 10.0, "the water around it")
        self.assertEqual(self.depth[23, 12], 0.0, "the island in the two-part lake")
        self.assertEqual(self.depth[27, 60], 0.0, "the island's edge, where it covers the texel's centre")
        self.assertEqual(self.depth[26, 60], 10.0, "but not the texel it only touches")
        self.assertEqual(self.depth[21, 42], 10.0, "an islet smaller than a texel leaves its texel water")

    def test_every_outer_ring_is_water(self):
        self.assertEqual(self.depth[45, 106], 20.0, "the eastern part")
        self.assertEqual(self.depth[20, 5], 20.0, "the western part")
        self.assertEqual(self.depth[12, 120], 0.0, "a lake under LAKE_KM2 is not drawn")
        self.assertEqual(self.depth[49, 120], 4.0, "one smaller than a texel takes the texel it touches, islet or not")

    def test_closed_follows_the_water_below_the_datum(self):
        self.assertTrue(self.closed[20, 5], "the western part lies below the datum")
        self.assertFalse(self.closed[23, 12], "not its island")
        self.assertFalse(self.closed[45, 106], "the eastern part stands above it")
        self.assertFalse(self.closed[20, 40], "so does the first lake")


class CacheTests(unittest.TestCase):
    """load(): the cache is keyed by the grid, the manifest and the rules and never returned
    for another; a new one is built from sources verified against the manifest, or not at all."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.out = Path(self.folder.name)
        self.patches = [mock.patch.object(present_water, "ROOT", self.out),
                        mock.patch.object(present_water, "MANIFEST", self.out / "present-water.json")]
        for patch in self.patches:
            patch.start()
        self.manifest = {"assets": [
            {"role": "rivers", "path": "data/sources/rivers/rivers.zip", "bytes": 1, "sha256": "0" * 64, "unzip": "ne", "layer": "rivers"},
            {"role": "lakes", "path": "data/sources/lakes/lakes.zip", "bytes": 1, "sha256": "1" * 64, "unzip": "hydrolakes",
             "layer": "lakes", "members": ["lakes.*"], "discard": True}]}
        present_water.MANIFEST.write_text(json.dumps(self.manifest))
        self.cache = self.out / "paleodem-0000-present-water.npz"
        rows, cols = np.mgrid[0:HEIGHT, 0:WIDTH]
        self.z = np.where(cols < 100, 100.0 + (100 - cols) * 5.0 + (32 - rows) * 2.0, -50.0)

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.folder.cleanup()

    def write_cache(self, key, **arrays):
        data = {"burn": np.zeros((HEIGHT, WIDTH), np.float32), "lakes": np.zeros((HEIGHT, WIDTH), np.float32),
                "closed": np.ones((HEIGHT, WIDTH), bool)}
        data.update(arrays)
        np.savez_compressed(self.cache, key=key, **data)

    def test_a_matching_cache_is_returned(self):
        self.write_cache(cache_key(self.z, self.manifest))
        self.assertTrue(load(self.out, self.z)["closed"].all())

    def test_another_grids_manifests_or_rules_cache_is_not(self):
        # jikhanjung's repro (devlog 090): the elevation changed, the old `closed` was kept.
        self.write_cache(cache_key(self.z + 1000.0, self.manifest))
        self.assertIsNone(load(self.out, self.z), "another elevation's cache, and no sources to rebuild from")
        self.write_cache(cache_key(self.z, dict(self.manifest, assets=[])))
        self.assertIsNone(load(self.out, self.z), "another manifest's")
        with mock.patch.object(present_water, "RULES", present_water.RULES + 1):
            self.write_cache(cache_key(self.z, self.manifest))
        self.assertIsNone(load(self.out, self.z), "another rule version's")

    def test_a_cache_of_the_wrong_shape_or_type_or_without_a_key_is_not(self):
        key = cache_key(self.z, self.manifest)
        self.write_cache(key, closed=np.ones((HEIGHT, WIDTH), np.uint8))
        self.assertIsNone(load(self.out, self.z), "a type")
        self.write_cache(key, burn=np.zeros((HEIGHT, WIDTH // 2), np.float32))
        self.assertIsNone(load(self.out, self.z), "a shape")
        np.savez_compressed(self.cache, burn=np.zeros((HEIGHT, WIDTH), np.float32))
        self.assertIsNone(load(self.out, self.z), "no key: a cache from before the key")
        self.cache.write_bytes(b"not an archive")
        self.assertIsNone(load(self.out, self.z), "unreadable")

    def sources(self):
        """Synthetic sources as the fetcher leaves them: the rivers in a kept archive, the
        lakes extracted with a receipt, both hashed into the manifest."""
        rivers_dir = self.out / "data/sources/rivers"
        rivers_dir.mkdir(parents=True)
        writer = shapefile.Writer(str(rivers_dir / "rivers"), shapeType=shapefile.POLYLINE)
        writer.field("scalerank", "N"); writer.field("featurecla", "C"); writer.field("name", "C")
        writer.line([[lonlat(c, 32) for c in range(20, 91)]]); writer.record(1, "River", "Main")
        writer.close()
        archive = rivers_dir / "rivers.zip"
        with zipfile.ZipFile(archive, "w") as opened:
            for ext in ("shp", "shx", "dbf"):
                opened.write(rivers_dir / f"rivers.{ext}", f"rivers.{ext}")
        lakes_dir = self.out / "data/sources/lakes/hydrolakes"
        lakes_dir.mkdir(parents=True)
        writer = shapefile.Writer(str(lakes_dir / "lakes"), shapeType=shapefile.POLYGON)
        writer.field("Lake_area", "N", decimal=1); writer.field("Depth_avg", "N", decimal=2)
        writer.poly([[(116, 6), (116, 33), (143, 33), (143, 6), (116, 6)]]); writer.record(1000, 10)   # in the grid's sea
        writer.close()
        files = [{"path": f"lakes.{ext}", "bytes": (lakes_dir / f"lakes.{ext}").stat().st_size,
                  "sha256": hashlib.sha256((lakes_dir / f"lakes.{ext}").read_bytes()).hexdigest()} for ext in ("shp", "shx", "dbf")]
        (lakes_dir / ".verified-extraction.json").write_text(json.dumps(
            {"archive_sha256": self.manifest["assets"][1]["sha256"], "members": ["lakes.*"], "files": files}))
        self.manifest["assets"][0].update(bytes=archive.stat().st_size, sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        present_water.MANIFEST.write_text(json.dumps(self.manifest))
        return archive, lakes_dir

    def test_the_rasters_are_built_from_verified_sources_and_cached(self):
        archive, lakes_dir = self.sources()
        rasters = load(self.out, self.z)
        self.assertEqual(rasters["burn"][32, 50], 1.0, "the river line")
        self.assertEqual(rasters["lakes"][25, 110], 10.0, "the lake")
        self.assertTrue(rasters["closed"][25, 110], "below the datum")
        self.assertTrue(self.cache.exists())
        with mock.patch.object(present_water, "rivers", side_effect=AssertionError("rebuilt")):
            self.assertEqual(load(self.out, self.z)["burn"][32, 50], 1.0, "the second call is the cache")
        self.cache.unlink()
        with archive.open("ab") as handle:
            handle.write(b"x")
        self.assertIsNone(load(self.out, self.z), "an archive that differs from the manifest is refused")
        self.manifest["assets"][0].update(bytes=archive.stat().st_size, sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        present_water.MANIFEST.write_text(json.dumps(self.manifest))
        (lakes_dir / "lakes.dbf").write_bytes(b"tampered")
        self.assertIsNone(load(self.out, self.z), "an extracted file that differs from its receipt is refused")


if __name__ == "__main__":
    unittest.main()
