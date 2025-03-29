from src.models import Team, Player
import unittest


class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.player = Player(name="John")
        self.team = Team([self.player])

    def test_initial_state(self):
        self.assertEqual(self.player.name, "John")
        self.assertEqual(self.player.team, self.team)

    def test_win_point(self):
        self.player.win_point()
        self.assertEqual(self.team.points.get_curr_pts(), 1)

    def test_no_team_exception(self):
        player_without_team = Player(name="Solo")
        with self.assertRaises(Exception):
            player_without_team.win_point()

    def test_player_to_string(self):
        self.assertEqual(str(self.player), "Player: John")
