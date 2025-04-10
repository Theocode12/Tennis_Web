from src.interfaces.boards.views import MatchViewData, ScoreboardTeamView
import unittest


class TestViews(unittest.TestCase):
    def test_match_view_data(self):
        """Test MatchViewData stores player views correctly."""
        player1_view = ScoreboardTeamView("Player 1", 15, [1, 0])
        player2_view = ScoreboardTeamView("Player 2", 30, [0, 1])

        match_view = MatchViewData(player1_view, player2_view)

        self.assertEqual(match_view.player1_view.name, "Player 1")
        self.assertEqual(match_view.player2_view.name, "Player 2")

    def test_scoreboard_player_view(self):
        """Test ScoreboardTeamView initialization."""
        view = ScoreboardTeamView("Player 1", 15, [1, 0])
        self.assertEqual(view.name, "Player 1")
        self.assertEqual(view.game_points, 15)
        self.assertEqual(view.set_points, [1, 0])
