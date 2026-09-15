"""Independent geometry and adversarial correspondence checks (offline)."""
import sys
import unittest
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from frame_alignment import (GEOGRAPHIC_TO_GLOBE, EARTH_RADIUS_KM, apply, fit_rotation,
                             lonlat_xyz, quaternion_matrix, separation_degrees, transform_section)
from audit_frame_alignment import trajectory_fit


class AlignmentTests(unittest.TestCase):
    def test_axes_depth_and_globe_convention(self):
        points = lonlat_xyz(np.array([0, 90, 180, 0]), np.array([0, 0, 0, 90]))
        expected = [[1,0,0], [0,0,-1], [-1,0,0], [0,1,0]]
        np.testing.assert_allclose(apply(GEOGRAPHIC_TO_GLOBE, points), expected, atol=1e-15)
        p = lonlat_xyz(85, 20, 1000)
        self.assertAlmostEqual(np.linalg.norm(apply(GEOGRAPHIC_TO_GLOBE, p)), 1-1000/EARTH_RADIUS_KM)
        self.assertAlmostEqual(np.linalg.det(GEOGRAPHIC_TO_GLOBE), 1)

    def test_fit_inverse_and_independent_quaternion(self):
        rng = np.random.default_rng(10)
        a = rng.normal(size=(100,3))
        rotation = Rotation.from_rotvec([.2, -.4, .7])
        target = rotation.apply(a)
        fit = fit_rotation(a, target)
        np.testing.assert_allclose(fit, rotation.as_matrix(), atol=1e-14)
        np.testing.assert_allclose(apply(fit.T, target), a, atol=1e-14)
        x,y,z,w = rotation.as_quat()
        np.testing.assert_allclose(quaternion_matrix([w,x,y,z]), fit, atol=1e-14)
        # A reflection must never be accepted as a coordinate rotation.
        self.assertAlmostEqual(np.linalg.det(fit_rotation(a, -a)), 1)

    def test_rotated_section_half_plane_and_distance(self):
        rotation = Rotation.from_rotvec([.5,.2,-.3]).as_matrix()
        points = lonlat_xyz(np.repeat(85., 5), np.array([-40,-20,0,20,60]))
        normal, half = transform_section(rotation)
        rotated = apply(rotation, points)
        np.testing.assert_allclose(rotated @ normal, 0, atol=1e-14)
        self.assertTrue(np.all(rotated @ half > 0))
        self.assertTrue(np.all(-rotated @ half < 0))
        np.testing.assert_allclose(separation_degrees(points[:-1],points[1:]),
                                   separation_degrees(rotated[:-1],rotated[1:]), atol=1e-13)

    def test_rematch_without_model_rotation(self):
        rng = np.random.default_rng(12)
        a = rng.normal(size=(120,3)); a /= np.linalg.norm(a,axis=1)[:,None]
        r = Rotation.from_rotvec([.03,.2,-.1]).as_matrix()
        b = apply(r,a)
        # Scramble a minority of IDs; source geometry remains unchanged.
        b[:30] = b[np.arange(29,-1,-1)]
        fitted, paired, evidence = trajectory_fit(a,b,np.arange(len(a)))
        np.testing.assert_allclose(fitted,r,atol=1e-13)
        self.assertGreater(evidence['spatial_rematch_count'],0)
        np.testing.assert_allclose(paired,apply(r,a),atol=1e-13)
        # A real displaced point must fail the all-held-out geometry gate.
        b[31] = [1.,0.,0.]
        with self.assertRaises(ValueError):
            trajectory_fit(a,b,np.arange(len(a)))

    def test_invalid_and_dateline(self):
        with self.assertRaises(ValueError): fit_rotation([[1,0,0]]*3,[[0,1,0]]*3)
        with self.assertRaises(ValueError): lonlat_xyz(0,0,7000)
        with self.assertRaises(ValueError): lonlat_xyz(0,91)
        with self.assertRaises(ValueError): lonlat_xyz(float('nan'),0)
        self.assertEqual(lonlat_xyz([0,90],0).shape,(2,3))
        self.assertAlmostEqual(float(separation_degrees(lonlat_xyz(179,0),lonlat_xyz(-179,0))),2)


if __name__ == '__main__': unittest.main()
