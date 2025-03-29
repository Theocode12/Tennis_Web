from src.core.models import Set, Team, TeamIndex
from src.core.gameplay.game.game_config import GameConfig
from src.core.gameplay.game.point_allocator import PointAllocator
from src.core.gameplay.game.game_scores_payload import ScorePayload
from typing import Optional


class GameLogic:
    def __init__(
        self,
        config: GameConfig,
        point_allocator: PointAllocator,
    ):
        self.config: GameConfig = config
        self.point_allocator: Optional[PointAllocator] = point_allocator
        self._set_manager: Set = config.set_manager
        self.point_allocator.set_teams([config.team1, config.team2])
        self.game_over = False

    def game_over(self) -> bool:
        return self.game_over

    def generate_score_payload(self) -> dict:
        """Generate a dictionary payload representing the current game score."""
        return ScorePayload(
            self.config.team1, self.config.team2, self._set_manager
        ).to_dict()

    def allocate_points(self):
        """Allocate points randomly between teams."""
        self.point_allocator.allocate_point()

    def handle_error(self, error: Exception):
        """Handle and log errors that occur during game execution."""
        print(f"Error occurred: {error}")
        raise error

    def update_game_winner(self, winning_team_index: TeamIndex):
        """Update the game winner and reset points for the next game."""
        if winning_team_index:
            self._set_manager.update_score(winning_team_index)
            self.config.team1.reset_game_points()
            self.config.team2.reset_game_points()
            winning_team = (
                self.config.team1
                if winning_team_index == TeamIndex.TEAM_1
                else self.config.team2
            )
            print(f"{winning_team.name} wins the game!")

    def update_set_winner(self, winning_team_index: Optional[TeamIndex]):
        """Update the set winner, record the win, and start a new set if applicable."""
        if winning_team_index is None:
            return
        self._set_manager.add_new_set()

    def determine_game_winner(self) -> int:
        """Determine if any team has won the current game."""
        team1_points = self.config.team1.get_game_points()
        team2_points = self.config.team2.get_game_points()
        is_tiebreak = self.config.rule_eval.check_tiebreak(
            *self._set_manager.get_current_set_points()
        )

        if self.config.rule_eval.check_game_winner(
            team1_points, team2_points, is_tiebreak
        ):
            return TeamIndex.TEAM_1
        elif self.config.rule_eval.check_game_winner(
            team2_points, team1_points, is_tiebreak
        ):
            return TeamIndex.TEAM_2
        return None

    def determine_set_winner(self) -> int:
        """Determine if any team has won the current set."""
        team1_set_points, team2_set_points = self._set_manager.get_current_set_points()

        if self.config.rule_eval.check_set_winner(
            team1_set_points,
            team2_set_points,
        ):
            return TeamIndex.TEAM_1
        elif self.config.rule_eval.check_set_winner(
            team2_set_points,
            team1_set_points,
        ):
            return TeamIndex.TEAM_2
        return None

    def check_and_handle_match_winner(self):
        """Check if any team has won the match and end the game if true."""
        if self.config.rule_eval.check_match_winner(
            self.sets_team_has_won(TeamIndex.TEAM_1)
        ):
            self._set_manager.pop_last_set()
            self.end_game(self.config.team1)
        elif self.config.rule_eval.check_match_winner(
            self.sets_team_has_won(TeamIndex.TEAM_2)
        ):
            self._set_manager.pop_last_set()
            self.end_game(self.config.team2)

    def sets_team_has_won(self, team_index) -> int:
        return sum(
            self.config.rule_eval.check_set_winner(
                team1_points if team_index == TeamIndex.TEAM_1 else team2_points,
                team2_points if team_index == TeamIndex.TEAM_1 else team1_points,
            )
            for team1_points, team2_points in self._set_manager.get_set_points()
        )

    def end_game(self, winning_team: Team):
        """Handle the end of the game and dispatch the result."""
        print(f"Game Over! Winner: {winning_team.name}")
        self.game_over = True

    def log_scores(self):
        """Log the current scores for debugging purposes."""
        team1_points = self.config.team1.get_game_points()
        team2_points = self.config.team2.get_game_points()
        print(
            f"Team 1 points: {team1_points}, "
            f"Team 2 points: {team2_points}, "
            f"Set: {self._set_manager.transform_set_data()}"
        )

    def execute(self):
        """Manage the progression of the game."""
        try:
            self.check_and_handle_match_winner()
            self.update_game_winner(self.determine_game_winner())
            self.log_scores()
            self.update_set_winner(self.determine_set_winner())

            # Randomly give points to a player for the next round
            self.allocate_points()
        except Exception as e:
            self.handle_error(e)
