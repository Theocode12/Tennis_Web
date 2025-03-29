from src.player import Player
from src.scoreboard import Scoreboard
import unittest


class TestTennisScoreboard(unittest.TestCase):
    def setUp(self):
        self.scoreboard = Scoreboard()

    def test_both_players_start_game_with_no_points(self):
        p1 = Player()
        p2 = Player()

        p1.addNewSet()
        p2.addNewSet()

        self.scoreboard.addPlayers(p1, p2)
        score = self.scoreboard.getCurrentGameScores()

        self.assertListEqual(score, ["0", "0"])

    def test_both_players_has_zero_to_three_points(self):
        p1 = Player()
        p2 = Player()

        p1.addNewSet()
        p2.addNewSet()

        p1.addPoint(3)
        p2.addPoint(1)
        self.scoreboard.addPlayers(p1, p2)
        score = self.scoreboard.getCurrentGameScores()

        self.assertListEqual(score, ["40", "15"])

    def test_one_player_has_an_advantage(self):
        p1 = Player()
        p2 = Player()

        p1.addNewSet()
        p2.addNewSet()

        p1.addPoint(1)
        p2.addPoint(4)
        self.scoreboard.addPlayers(p1, p2)
        score = self.scoreboard.getCurrentGameScores()

        self.assertListEqual(score, ["15", "AD"])

    def test_new_players_has_empty_set(self):
        p1 = Player()
        p2 = Player()

        self.scoreboard.addPlayers(p1, p2)
        score = self.scoreboard.getSetScores()

        self.assertListEqual(score, [[], []])

    def test_scoreboard_for_new_players(self):
        p1 = Player()
        p2 = Player()

        p1.addNewSet()
        p2.addNewSet()

        self.scoreboard.addPlayers(p1, p2)
        scoreboard = self.scoreboard.getScoreBoard()

        expected_scoreboard = {
            "players": ["", ""],
            "sets": [[0], [0]],
            "game": ["0", "0"],
        }

        self.assertDictEqual(scoreboard, expected_scoreboard)
