import unittest
from unittest.mock import MagicMock
from src.core.rules import (
    RulesFactory,
    TennisRules,
    GrandSlamRules,
    RegularTournamentRules,
    CustomTennisRules,
)


class TestRulesFactory(unittest.TestCase):

    def test_create_grand_slam_rules(self):
        rules = RulesFactory.create_rules(tournament_type="grand_slam")
        self.assertIsInstance(
            rules, TennisRules, "Should return an instance of TennisRules"
        )
        self.assertIsInstance(
            rules, GrandSlamRules, "Should return an instance of GrandSlamRules"
        )

    def test_create_regular_tournament_rules(self):
        rules = RulesFactory.create_rules(tournament_type="regular")
        self.assertIsInstance(
            rules, TennisRules, "Should return an instance of TennisRules"
        )
        self.assertIsInstance(
            rules,
            RegularTournamentRules,
            "Should return an instance of RegularTournamentRules",
        )

    def test_create_custom_tennis_rules(self):
        # Arrange: create mock rules for the custom rules
        constants = MagicMock()

        # Act: create custom tennis rules with the required parameters
        rules = RulesFactory.create_rules(tournament_type="custom", constants=constants)

        # Assert: check that the created rules are of the correct type
        self.assertIsInstance(
            rules, TennisRules, "Should return an instance of TennisRules"
        )
        self.assertIsInstance(
            rules, CustomTennisRules, "Should return an instance of CustomTennisRules"
        )

    def test_create_rules_with_invalid_type(self):
        with self.assertRaises(
            ValueError, msg="Invalid tournament type should raise ValueError"
        ):
            RulesFactory.create_rules(tournament_type="invalid_type")
