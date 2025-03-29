from src.boards import ScoreBoard
from src.boards.views import MatchViewData, ScoreboardTeamView
from src.displays import BashDisplay
from src.models import Team, Set
from unittest.mock import MagicMock
import unittest


class TestTennisScoreboard(unittest.TestCase):
    def setUp(self):
        self.scoreboard = ScoreBoard()  # Initialize scoreboard without any displays
        self.team1 = MagicMock(
            spec=Team, players_name=MagicMock(return_value=["Alice", "Bob"])
        )
        self.team2 = MagicMock(
            spec=Team, players_name=MagicMock(return_value=["Charlie", "David"])
        )
        self.team1.get_game_points = MagicMock(return_value=5)
        self.team2.get_game_points = MagicMock(return_value=3)

        self.mock_set = MagicMock(spec=Set)
        self.mock_set.transform_set_data = MagicMock(
            return_value=([6, 4, 7], [2, 6, 6])
        )

    def test_scoreboard_without_display(self):
        """Test initializing scoreboard without displays."""
        self.assertEqual(
            len(self.scoreboard.displays),
            0,
            "Scoreboard should have no displays initially.",
        )

    def test_scorboard_register_display(self):
        """Test registering a display to the scoreboard."""
        display = BashDisplay()
        self.scoreboard.register_display(display)
        self.assertIn(
            display,
            self.scoreboard.displays,
            "Display should be registered in the scoreboard.",
        )
        self.assertEqual(
            len(self.scoreboard.displays),
            1,
            "Scoreboard should have exactly one display registered.",
        )

    def test_instantiating_scoreboard_with_multiple_displays(self):
        """Test initializing scoreboard with multiple displays."""
        display1 = BashDisplay()
        display2 = BashDisplay()
        scoreboard = ScoreBoard(display1, display2)
        self.assertEqual(
            len(scoreboard.displays),
            2,
            "Scoreboard should have two displays initially.",
        )
        self.assertIn(
            display1, scoreboard.displays, "Display1 should be in the scoreboard."
        )
        self.assertIn(
            display2, scoreboard.displays, "Display2 should be in the scoreboard."
        )

    def test_scoreboard_register_display_after_instantiation_with_display(self):
        """Test registering multiple displays after instantiation."""
        display1 = BashDisplay()
        display2 = BashDisplay()
        scoreboard = ScoreBoard(display1)
        scoreboard.register_display(display2)
        self.assertEqual(
            len(scoreboard.displays), 2, "Scoreboard should register both displays."
        )
        self.assertIn(display1, scoreboard.displays, "Display1 should be registered.")
        self.assertIn(display2, scoreboard.displays, "Display2 should be registered.")

    def test_scoreboard_removal_of_display(self):
        display1 = BashDisplay()
        display2 = BashDisplay()
        self.scoreboard.register_display(display1)
        self.scoreboard.register_display(display2)
        self.assertIn(
            display1, self.scoreboard.displays, "Display1 should be registered."
        )
        self.scoreboard.remove_display(display1)
        self.assertNotIn(
            display1, self.scoreboard.displays, "Display1 should not be available."
        )

    def test_get_view(self):
        """Test the get_view method returns a valid MatchViewData."""
        view_data = self.scoreboard.get_view(self.team1, self.team2, self.mock_set)

        # Assert that the returned data is an instance of MatchViewData
        self.assertIsInstance(
            view_data, MatchViewData, "get_view should return MatchViewData"
        )

        # Validate the team 1 view
        self.assertIsInstance(
            view_data.player1_view,
            ScoreboardTeamView,
            "Team 1 view should be a ScoreboardTeamView",
        )
        self.assertEqual(
            view_data.player1_view.name,
            ["Alice", "Bob"],
            "Team 1 view's name should match the players in team 1",
        )
        self.assertEqual(
            view_data.player1_view.game_points,
            5,
            "Team 1 view's game points should match team 1's game points",
        )
        self.assertEqual(
            view_data.player1_view.set_points,
            [6, 4, 7],
            "Team 1 view's set points should match the transformed data",
        )

        # Validate the team 2 view
        self.assertIsInstance(
            view_data.player2_view,
            ScoreboardTeamView,
            "Team 2 view should be a ScoreboardTeamView",
        )
        self.assertEqual(
            view_data.player2_view.name,
            ["Charlie", "David"],
            "Team 2 view's name should match the players in team 2",
        )
        self.assertEqual(
            view_data.player2_view.game_points,
            3,
            "Team 2 view's game points should match team 2's game points",
        )
        self.assertEqual(
            view_data.player2_view.set_points,
            [2, 6, 6],
            "Team 2 view's set points should match the transformed data",
        )

    def test_notify_display(self):
        """Test that notify_display calls render on all registered displays."""
        display1 = BashDisplay()
        display1.render = MagicMock()
        display2 = BashDisplay()
        display2.render = MagicMock()

        self.scoreboard.register_display(display1)
        self.scoreboard.register_display(display2)

        self.scoreboard.notify_display(self.team1, self.team2, self.mock_set)

        view_data = self.scoreboard.get_view(self.team1, self.team2, self.mock_set)
        display1.render.assert_called_once_with(view_data)
        display2.render.assert_called_once_with(view_data)
