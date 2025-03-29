from src.player import Player
import unittest


class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.player = Player()

    def test_getting_empty_name(self):
        playerName = self.player.getName()
        self.assertTrue(playerName == "")

    def test_setting_name(self):
        playerName = self.player.setName("Rafeal Nadal")
        playerName = self.player.getName()
        self.assertEqual(playerName, "Rafeal Nadal")

    def test_setting_name_with_wrong_datatype(self):
        with self.assertRaises(TypeError):
            self.player.setName(["Rafeal Nadal"])

    def test_getting_zero_points(self):
        playerPoints = self.player.getPoints()
        self.assertTrue(playerPoints == 0)

    def test_incrementing_points(self):
        self.player.addPoint(1)
        playerPoints = self.player.getPoints()
        self.assertEqual(playerPoints, 1)

        self.player.addPoint(1)
        playerPoints = self.player.getPoints()
        self.assertEqual(playerPoints, 2)

    def test_adding_point_with_wrong_datatype(self):
        with self.assertRaises(TypeError):
            self.player.addPoint("1")
