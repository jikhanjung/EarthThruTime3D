"""Analytical intersections independent of the OPT1 archive."""
from pathlib import Path
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from build_india_asia import clip_segment, section_segments, unique_segments, surface


class SectionTests(unittest.TestCase):
    def test_surface_decodes_packed_height_and_samples_regional_grid(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'data/derived/paleodem'
            path.mkdir(parents=True)
            # 170*16+10 = 2730; 2730/4095*15000-9000 = 1000 m.
            Image.new('RGB', (8, 4), (0, 170, 10)).save(path/'paleodem-0000-field.png')
            with patch('build_india_asia.ROOT', Path(folder)):
                result = surface(0)
            self.assertEqual((result['nx'], result['ny']), (129, 161))
            self.assertEqual(set(result['heights_m']), {1000})

    def test_known_plane_crossing(self):
        # longitude 0 is y=0. Crossings are (.8,0,0) and (.8,0,.1).
        points = np.array([[.8, -.1, 0], [.8, .1, 0], [.8, .1, .2]])
        result = section_segments(points, np.array([0, 1, 2]), longitude=0)
        self.assertEqual(len(result), 1)
        ends = np.array(result[0]).reshape(2, 2)
        ends = ends[np.argsort(ends[:, 0])]
        np.testing.assert_allclose(ends[0], [0, .2*6371], atol=.001)
        np.testing.assert_allclose(ends[1], [np.degrees(np.arctan2(.1, .8)), (1-np.hypot(.8,.1))*6371], atol=.001)

    def test_reject_opposite_meridian_tangent_and_coplanar_face(self):
        cases = [np.array([[-.8,-.1,0],[-.8,.1,0],[-.8,.1,.2]]),
                 np.array([[.8,0,0],[.8,.1,0],[.8,.1,.2]]),
                 np.array([[.8,0,0],[.8,0,.1],[.7,0,.1]])]
        for points in cases:
            self.assertEqual(section_segments(points, np.array([0,1,2]), longitude=0), [])

    def test_clipping_preserves_crossing_with_both_ends_outside(self):
        self.assertEqual(clip_segment([-2,0], [2,0], (-1,1,-1,1)), [-1,0,1,0])
        self.assertIsNone(clip_segment([-2,2], [2,2], (-1,1,-1,1)))

    def test_shared_edges_deduplicated_in_both_directions(self):
        self.assertEqual(unique_segments([[1,2,3,4],[3,4,1,2]]), [[1,2,3,4]])


if __name__ == '__main__':
    unittest.main()
