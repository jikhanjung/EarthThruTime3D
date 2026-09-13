"""Checks for the rotation model reader and composition.

Runs on synthetic rotation files, so it needs neither the downloaded plate model nor
network access. The agreement with the reference implementation is checked separately
by scripts/check_rotation_against_gws.py, which does need both.

Run it with `.venv/bin/python tests/rotation_check.py`.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from rotation_model import (IDENTITY, RotationModel, conjugate,  # noqa: E402
                            multiply, rotate, slerp)


def write(lines):
    handle = tempfile.NamedTemporaryFile("w", suffix=".rot", delete=False)
    handle.write("\n".join(lines) + "\n")
    handle.close()
    return handle.name


class QuaternionTests(unittest.TestCase):
    def test_rotating_about_the_pole_turns_longitude(self):
        model = RotationModel(write(["  1  0.0  90.0  0.0   0.0  000",
                                     "  1 10.0  90.0  0.0  90.0  000"]))
        longitude, latitude = model.reconstruct(1, 10.0, 0.0, 0.0)
        self.assertAlmostEqual(longitude, 90.0, places=6)
        self.assertAlmostEqual(latitude, 0.0, places=6)

    def test_a_rotation_and_its_inverse_return_the_point(self):
        model = RotationModel(write(["  1  0.0   0.0  0.0   0.0  000",
                                     "  1 10.0  12.0 34.0  56.0  000"]))
        turn = model.rotation(1, 10.0)
        moved = rotate(turn, 20.0, -15.0)
        back = rotate(conjugate(turn), *moved)
        self.assertAlmostEqual(back[0], 20.0, places=6)
        self.assertAlmostEqual(back[1], -15.0, places=6)

    def test_slerp_reaches_both_ends(self):
        turn = multiply(IDENTITY, (0.7071067811865476, 0.0, 0.0, 0.7071067811865476))
        self.assertAlmostEqual(slerp(IDENTITY, turn, 0.0)[0], 1.0, places=9)
        self.assertAlmostEqual(slerp(IDENTITY, turn, 1.0)[3], turn[3], places=9)
        half = slerp(IDENTITY, turn, 0.5)
        self.assertAlmostEqual(rotate(half, 0.0, 0.0)[0], 45.0, places=6)


class CompositionTests(unittest.TestCase):
    def test_time_between_samples_is_interpolated(self):
        model = RotationModel(write(["  1  0.0  90.0  0.0   0.0  000",
                                     "  1 10.0  90.0  0.0  90.0  000"]))
        self.assertAlmostEqual(model.reconstruct(1, 5.0, 0.0, 0.0)[0], 45.0, places=6)

    def test_a_chain_composes_through_its_fixed_plate(self):
        model = RotationModel(write(["  2  0.0  90.0  0.0   0.0  000",
                                     "  2 10.0  90.0  0.0  30.0  000",
                                     "  1  0.0  90.0  0.0   0.0  002",
                                     "  1 10.0  90.0  0.0  60.0  002"]))
        self.assertAlmostEqual(model.reconstruct(1, 10.0, 0.0, 0.0)[0], 90.0, places=6)
        self.assertAlmostEqual(model.reconstruct(2, 10.0, 0.0, 0.0)[0], 30.0, places=6)

    def test_the_narrower_sequence_wins_where_two_overlap(self):
        # A window inserted over a broad sequence says the plate is measured against a
        # different neighbour for those years. 32 plates in the Merdith model do this.
        model = RotationModel(write(["  2  0.0  90.0  0.0   0.0  000",
                                     "  2 100.0 90.0  0.0  80.0  000",
                                     "  1  0.0  90.0  0.0   0.0  000",
                                     "  1 100.0 90.0  0.0  10.0  000",
                                     "  1 40.0  90.0  0.0  20.0  002",
                                     "  1 60.0  90.0  0.0  20.0  002"]))
        # Inside the window the answer comes through plate 2, not the broad sequence.
        through_two = model.reconstruct(1, 50.0, 0.0, 0.0)[0]
        self.assertAlmostEqual(through_two, 20.0 + 40.0, places=6)
        # Outside it, the broad sequence is used again.
        self.assertAlmostEqual(model.reconstruct(1, 100.0, 0.0, 0.0)[0], 10.0, places=6)

    def test_a_plate_outside_its_span_has_no_rotation(self):
        model = RotationModel(write(["  1 100.0 90.0  0.0  10.0  000",
                                     "  1 200.0 90.0  0.0  20.0  000"]))
        self.assertAlmostEqual(model.reconstruct(1, 150.0, 0.0, 0.0)[0], 15.0, places=6)
        with self.assertRaises(ValueError):
            model.reconstruct(1, 300.0, 0.0, 0.0)

    def test_the_anchor_never_moves(self):
        model = RotationModel(write(["  1 10.0  90.0  0.0  90.0  000"]))
        self.assertEqual(model.rotation(0, 10.0), IDENTITY)


if __name__ == "__main__":
    unittest.main()
