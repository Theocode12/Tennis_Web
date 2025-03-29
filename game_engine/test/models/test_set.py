from src.models import Set
import unittest


class TestSet(unittest.TestCase):
    def setUp(self):
        self.sets = Set()

    def test_initial_state(self):
        self.assertEqual(len(self.sets.sets), 0)

    def test_add_new_set(self):
        self.sets.add_new_set()
        self.assertEqual(len(self.sets.sets), 1)
        self.assertEqual(self.sets.sets[0], (0, 0))

    def test_update_score_team1(self):
        self.sets.add_new_set()
        self.sets.update_score(team_index=1, points=3)
        self.assertEqual(self.sets.get_current_set_points(), (3, 0))

    def test_update_score_team2(self):
        self.sets.add_new_set()
        self.sets.update_score(team_index=2, points=2)
        self.assertEqual(self.sets.get_current_set_points(), (0, 2))

    def test_invalid_team_index(self):
        self.sets.add_new_set()
        with self.assertRaises(ValueError):
            self.sets.update_score(team_index=3)

    def test_update_without_set(self):
        with self.assertRaises(Exception):
            self.sets.update_score(team_index=1)

    def test_transform_empty_sets(self):
        """Test transform_set_data with no sets."""
        transformed = self.sets.transform_set_data()
        self.assertEqual(transformed, ([], []), "Expected empty lists for empty sets.")

    def test_transform_single_set(self):
        """Test transform_set_data with a single set."""
        self.sets.sets = [(6, 2)]
        transformed = self.sets.transform_set_data()
        self.assertEqual(transformed, ([6], [2]), "Expected ([6], [2]) for single set.")

    def test_transform_multiple_sets(self):
        """Test transform_set_data with multiple sets."""
        self.sets.sets = [(6, 2), (4, 6), (7, 6)]
        transformed = self.sets.transform_set_data()
        self.assertEqual(
            transformed,
            ([6, 4, 7], [2, 6, 6]),
            "Expected ([6, 4, 7], [2, 6, 6]) for multiple sets.",
        )
