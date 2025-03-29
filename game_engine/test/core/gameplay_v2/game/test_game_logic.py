import unittest
from unittest.mock import MagicMock, patch
from src.core.models import Set, Team, TeamIndex
from src.core.models.events.game import GameEventType
from src.core.gameplay.game.game_config import GameConfig
from src.core.gameplay.game.point_allocator import PointAllocator
from src.core.gameplay.game.game_scores_payload import ScorePayload
from src.core.gameplay.game.game_logic import GameLogic


class TestGameLogic(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.team1 = MagicMock(spec=Team)
        self.team2 = MagicMock(spec=Team)
        self.set_manager = MagicMock(spec=Set)
        self.point_allocator = MagicMock(spec=PointAllocator)
        self.rule_eval = MagicMock()
        self.game_config = GameConfig(
            game_id="test_game",
            team1=self.team1,
            team2=self.team2,
            set=self.set_manager,
            rule_eval=self.rule_eval,
        )

        # Initialize GameLogic
        self.game_logic = GameLogic(
            config=self.game_config,
            point_allocator=self.point_allocator,
        )

    def test_generate_score_payload(self):
        result = self.game_logic.generate_score_payload()
        self.assertIsInstance(result, dict)
        self.assertDictEqual(
            result,
            {
                "team1": self.team1,
                "team2": self.team2,
                "set": self.set_manager.transform_set_data(),
            },
        )

    def test_allocate_points(self):
        self.game_logic.allocate_points()
        self.point_allocator.allocate_point.assert_called_once()

    def test_handle_error(self):
        error = Exception("Test error")
        self.game_logic.handle_error(error)

        self.event_manager.handle_error.assert_called_once_with(
            error, {"_id": self.game_config.game_id, "data": {"error": error}}
        )

    def test_update_game_winner(self):
        self.game_logic.update_game_winner(TeamIndex.TEAM_1)

        self.set_manager.update_score.assert_called_once_with(TeamIndex.TEAM_1)
        self.team1.reset_game_points.assert_called_once()
        self.team2.reset_game_points.assert_called_once()

    def test_update_set_winner(self):
        self.game_logic.update_set_winner(TeamIndex.TEAM_2)

        self.set_manager.add_new_set.assert_called_once()

    def test_determine_game_winner(self):
        self.team1.get_game_points.return_value = 10
        self.team2.get_game_points.return_value = 8
        self.rule_eval.check_tiebreak.return_value = False
        self.rule_eval.check_game_winner.side_effect = lambda x, y, z: x > y

        winner = self.game_logic.determine_game_winner()
        self.assertEqual(winner, TeamIndex.TEAM_1)

    def test_end_game(self):
        self.game_logic.end_game(self.team1)

        self.event_manager.dispatch_global.assert_called_once_with(
            GameEventType.GAME_OVER, {"_id": self.game_config.game_id, "data": {}}
        )
        self.event_manager.dispatch_local.assert_called_once_with(
            GameEventType.GAME_OVER, {"_id": self.game_config.game_id, "data": {}}
        )
