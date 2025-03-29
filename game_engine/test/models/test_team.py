from src.models import Team, Player
import unittest


class TestTeam(unittest.TestCase):
    def setUp(self):
        self.player1 = Player(name="Alice")
        self.player2 = Player(name="Bob")
        self.team = Team(players=[self.player1, self.player2])

    def test_initial_state(self):
        self.assertEqual(len(self.team.players), 2)
        self.assertEqual(self.team.points.current_points, 0)
        self.assertEqual(self.team.points.total_points, 0)
        self.assertEqual(len(self.team.sets.sets), 0)

    def test_player_team_linking(self):
        self.assertEqual(self.player1.team, self.team)
        self.assertEqual(self.player2.team, self.team)

    def test_reset_game_points(self):
        self.team.points.add_point(5)
        self.team.reset_game_points()
        self.assertEqual(self.team.points.get_curr_pts(), 0)

    def test_add_additional_players(self):
        player3 = Player(name="Charlie")
        self.team.add_players([player3])
        self.assertIn(player3, self.team.players)
        self.assertEqual(player3.team, self.team)

    def test_team_to_string(self):
        self.assertEqual(
            str(self.team),
            "Team: [Alice, Bob], Game Points: 0, Total Points: 0, Sets: Sets: []",
        )

    def test_players_name_empty_team(self):
        """Test players_name with no players added."""
        team = Team()
        self.assertEqual(
            team.players_name(),
            [],
            "Expected an empty list when no players are in the team.",
        )

    def test_players_name_all_players(self):
        """Test players_name with a single player added."""
        self.assertEqual(
            self.team.players_name(),
            ["Alice", "Bob"],
            "Expected a list with a single player's name.",
        )

    def test_players_name_after_team_modification(self):
        """Test players_name after adding and removing players."""
        self.team.players.pop()  # Remove the last player
        self.assertEqual(
            self.team.players_name(),
            ["Alice"],
            "Expected the player list to update after modifying the team.",
        )
