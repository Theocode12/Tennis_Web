from src.core.models import Points
import unittest


class TestPoints(unittest.TestCase):
    def setUp(self):
        self.points = Points()

    def test_initial_state(self):
        self.assertEqual(self.points.current_points, 0)
        self.assertEqual(self.points.total_points, 0)

    def test_add_point(self):
        self.points.add_point()
        self.assertEqual(self.points.current_points, 1)
        self.assertEqual(self.points.total_points, 1)

    def test_add_custom_points(self):
        self.points.add_point(3)
        self.assertEqual(self.points.current_points, 3)
        self.assertEqual(self.points.total_points, 3)

    def test_reset_points(self):
        self.points.add_point(5)
        self.points.reset()
        self.assertEqual(self.points.current_points, 0)
        self.assertEqual(self.points.total_points, 5)
