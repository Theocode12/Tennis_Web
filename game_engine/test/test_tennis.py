from src.tennis import Tennis, PlayersNumbersError
from src.player import Player
import unittest


class TestTennis(unittest.TestCase):

    def setUp(self):
        self.game_instance = Tennis()
        self.player_1 = Player()
        self.player_2 = Player()

    def test_a_point(self):
        self.assertEqual(1, self.game_instance.point())

    def test_adding_a_player(self):
        self.game_instance.addPlayer(self.player_1)
        no_of_players = self.game_instance.noOfPlayers()
        self.assertEqual(no_of_players, 1)

    def test_adding_two_players(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)
        no_of_players = self.game_instance.noOfPlayers()
        self.assertEqual(no_of_players, 2)

    def test_adding_more_than_two_players(self):
        player_3 = Player()
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)
        with self.assertRaises(PlayersNumbersError):
            self.game_instance.addPlayer(player_3)

    def test_if_added_player_is_player_object(self):
        with self.assertRaises(TypeError):
            self.game_instance.addPlayer("player_1")

    def test_adding_multiple_players_at_once(self):
        self.game_instance.addPlayers(self.player_1, self.player_2)
        self.assertEqual(self.game_instance.noOfPlayers(), 2)

    def test_giving_point_to_non_existent_players(self):
        with self.assertRaises(IndexError):
            self.game_instance.givePointToPlayer(0)

    def test_giving_a_point_to_players(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)
        self.game_instance.givePointToPlayer(0)
        self.assertTrue(self.game_instance.getPlayerPoints(0) == 1)

        self.game_instance.givePointToPlayer(1)
        self.assertTrue(self.game_instance.getPlayerPoints(1) == 1)

    def test_giving_two_points_to_player(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)
        self.game_instance.givePointToPlayer(0)
        self.game_instance.givePointToPlayer(0)
        self.assertTrue(self.game_instance.getPlayerPoints(0) == 2)

        self.game_instance.givePointToPlayer(1)
        self.game_instance.givePointToPlayer(1)
        self.assertTrue(self.game_instance.getPlayerPoints(1) == 2)

    def test_starting_a_set_for_new_players(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)
        self.game_instance.createSet()

        self.assertEqual(self.player_1.getSet(), [0])
        self.assertEqual(self.player_2.getSet(), [0])

    def test_incrementing_player_current_set(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)
        self.game_instance.createSet()

        self.game_instance.incrementSetPointForPlayer(0)
        self.assertEqual(self.player_1.getSet(), [1])

    def test_checking_a_player_won_a_game(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.player_1.addPoint(5)
        self.player_2.addPoint(3)

        res = self.game_instance.hasPlayerWonGame(0)
        self.assertTrue(res)

    def test_checking_a_player_faild_to_win_a_game(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.player_1.addPoint(5)
        self.player_2.addPoint(4)

        res = self.game_instance.hasPlayerWonGame(0)
        self.assertFalse(res)

    def test_points_is_cleared_after_winning_game_point(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.player_1.addPoint(4)
        self.player_2.addPoint(3)

        self.game_instance.handleGamePoint(0)
        self.assertEqual(self.player_1.getPoints(), 0)
        self.assertEqual(self.player_2.getPoints(), 0)

    def test_set_points_is_added_after_winning_game_point(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.player_1.addPoint(4)
        self.player_2.addPoint(3)

        self.game_instance.handleGamePoint(0)
        self.assertEqual(self.player_1.getSet(), [1])
        self.assertEqual(self.player_2.getSet(), [0])

    def test_no_side_effects_after_non_winning_game_point(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.player_1.addPoint(4)
        self.player_2.addPoint(3)

        self.game_instance.handleGamePoint(1)
        self.assertEqual(self.player_1.getSet(), [0])
        self.assertEqual(self.player_2.getSet(), [0])
        self.assertEqual(self.player_1.getPoints(), 4)
        self.assertEqual(self.player_2.getPoints(), 4)

    def test_valid_tie_break(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.player_1.incrementCurrentSetPoint(6)
        self.player_2.incrementCurrentSetPoint(6)

        self.assertTrue(self.game_instance.isTieBreak())

    def test_valid_tie_break(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.player_1.incrementCurrentSetPoint(5)
        self.player_2.incrementCurrentSetPoint(5)

        self.assertFalse(self.game_instance.isTieBreak())

    def test_player_has_not_won_set_(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.player_1.incrementCurrentSetPoint(0)
        self.player_2.incrementCurrentSetPoint(0)

        self.assertFalse(self.game_instance.hasPlayerWonSet(0))

    def test_player_won_set_flawless(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.player_1.incrementCurrentSetPoint(6)
        self.player_2.incrementCurrentSetPoint(0)

        self.assertTrue(self.game_instance.hasPlayerWonSet(0))

    def test_player_won_set_difficult_way(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.player_1.incrementCurrentSetPoint(5)
        self.player_2.incrementCurrentSetPoint(7)

        self.assertTrue(self.game_instance.hasPlayerWonSet(1))

    def test_player_won_set_through_tie_break(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.player_1.incrementCurrentSetPoint(6)
        self.player_2.incrementCurrentSetPoint(6)

        self.player_1.addPoint(7)
        self.player_2.addPoint(5)

        self.assertTrue(self.game_instance.hasPlayerWonSet(0))

    def test_player_have_not_won_set_through_tie_break(self):
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.player_1.incrementCurrentSetPoint(6)
        self.player_2.incrementCurrentSetPoint(6)

        self.player_1.addPoint(6)
        self.player_2.addPoint(5)

        self.assertFalse(self.game_instance.hasPlayerWonSet(0))

    def test_tennis_sim(self):
        self.player_1.setName("Rafeal Nadal")
        self.player_2.setName("Roger Federer")
        self.game_instance.addPlayer(self.player_1)
        self.game_instance.addPlayer(self.player_2)

        self.game_instance.createSet()

        self.game_instance.gameSim()


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
