import numpy as np
from django.test import SimpleTestCase

from scripts.build_mountain_ranges import crest_marks


class CrestRuleTests(SimpleTestCase):
    """The past grids' rule on a 1-degree grid, rows north to south: a ridge standing above
    lowland is marked, a lone peak is dropped, and a plateau's interior is not a range."""

    def test_ridge_marked_lone_peak_and_plateau_interior_not(self):
        z = np.full((181, 361), 200.0)
        z[60, 180:211] = 2500.0          # a ridge along 30 N from 0 to 30 E
        z[150, 60] = 3000.0              # a lone peak at 60 S, 120 W
        z[100:121, 240:281] = 1500.0     # a plateau, 10-30 S, 60-100 E
        marks = np.array(crest_marks(z))
        ridge = marks[(marks[:, 1] == 30) & (marks[:, 0] >= 0) & (marks[:, 0] <= 30)]
        self.assertGreaterEqual(len(ridge), 5)
        self.assertTrue((ridge[:, 2] == 2500).all())
        self.assertFalse(((np.abs(marks[:, 0] + 120) < 3) & (np.abs(marks[:, 1] + 60) < 3)).any())
        self.assertFalse(((marks[:, 0] > 70) & (marks[:, 0] < 90) & (marks[:, 1] > -26) & (marks[:, 1] < -14)).any())
