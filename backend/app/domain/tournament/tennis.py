import asyncio
import uuid
from collections import deque
from configparser import ConfigParser
from dataclasses import dataclass
from typing import Any

from app.config.game_engine_config import CONFIG
from gameengine import GameBuilder, GameRunner
from utils.logger import get_logger


class TournamentResult:
    FINISHED = "finished"
    CONTINUE = "continue"
    NO_MATCHES = "no_matches"


@dataclass(frozen=True, slots=True)
class RoundSpec:
    code: str
    name: str
    required_players: int


class Tournament:
    """
    Single-elimination tournament aggregate.
    """

    MAX_MATCHES_PER_POLL = 4

    def __init__(self, tournament_id: str, config: dict[str, Any]) -> None:
        self.id = tournament_id
        self.config = config

        self.logger = get_logger()

        self.rounds: list[RoundSpec] = [RoundSpec(**r) for r in config["rounds"]]
        self.current_round_index = 0

        self.all_players: list[str] = list(config["players"])
        self.active_players: list[str] = list(self.all_players)

        self.player_metadata: dict[str, dict[str, Any]] = config.get("player_metadata", {})

        self.match_players: dict[str, tuple[str, str]] = {}
        self.completed_matches: deque[str] = deque()

        self.is_finished = False
        self.winner: str | None = None

    # =========================
    # Round State
    # =========================

    @property
    def current_round(self) -> RoundSpec:
        return self.rounds[self.current_round_index]

    def validate_round_state(self) -> None:
        if self.is_finished:
            self.logger.error("Tournament already finished")
            raise ValueError("Tournament already finished")

        if self.current_round_index >= len(self.rounds):
            self.logger.error("Invalid round index %d", self.current_round_index)
            raise ValueError("Invalid round index")

        if len(self.active_players) != self.current_round.required_players:
            self.logger.error(
                "Round %s requires %d players, but got %d",
                self.current_round.code,
                self.current_round.required_players,
                len(self.active_players),
            )
            raise ValueError(f"Round {self.current_round.code} requires {self.current_round.required_players} players")

    # =========================
    # Match Construction
    # =========================

    def _player_info(self, player_name: str) -> dict[str, Any]:
        """Return a PlayerInfo-compatible dict for the given player name."""
        meta = self.player_metadata.get(player_name)
        if meta and "world_ranking" in meta:
            return {"name": player_name, "world_ranking": meta["world_ranking"]}
        return {"name": player_name}

    def _build_match_payload(
        self,
        match_id: str,
        player_a: str,
        player_b: str,
    ) -> dict[str, Any]:
        defaults = self.config["game_defaults"]

        return {
            "game_id": match_id,
            **defaults,
            "players": [
                [self._player_info(player_a)],
                [self._player_info(player_b)],
            ],
            "match_context": {
                "match_type": "TOURNAMENT",
                "created_by": self.config["created_by"],
                "tournament": {
                    "tournament_id": self.id,
                    "name": self.config["name"],
                    "season": self.config["season"],
                    "surface": self.config.get("surface"),
                    "level": self.config.get("level"),
                    "round": {
                        "code": self.current_round.code,
                        "name": self.current_round.name,
                    },
                },
            },
        }

    def _create_match_runners(self) -> list[asyncio.Task]:
        self.validate_round_state()

        config = ConfigParser()
        config.read_dict(CONFIG)

        tasks = []

        for i in range(0, len(self.active_players), 2):
            a, b = self.active_players[i], self.active_players[i + 1]
            match_id = str(uuid.uuid4())

            self.match_players[match_id] = (a, b)

            payload = self._build_match_payload(match_id, a, b)

            builder = GameBuilder(payload, logger=self.logger, app_config=config)
            runner = GameRunner(builder)

            tasks.append(self._run_match(match_id, runner))

        return tasks

    async def _run_match(self, match_id: str, runner: GameRunner) -> tuple[str, str]:
        _, winner = await runner.run()
        return match_id, winner

    # =========================
    # Public API
    # =========================

    async def get_next_match_payloads(self) -> list[str]:
        """
        Returns up to 4 completed match IDs.
        Runs new matches if none are queued.
        """

        if self.completed_matches:
            return self._dequeue_completed_matches()

        tasks = self._create_match_runners()
        if not tasks:
            return []

        results = await asyncio.gather(*tasks)

        for match_id, winner in results:
            self._record_match_result(match_id, winner)

        self._advance_round_if_ready()

        return self._dequeue_completed_matches()

    def tick(self) -> tuple[str, list[str]]:
        if self.is_finished:
            return TournamentResult.FINISHED, []

        try:
            match_ids = asyncio.run(self.get_next_match_payloads())
            for match_id in match_ids:
                self.logger.info("Scheduled match %s for tournament %s", match_id, self.id)
        except ValueError:
            return TournamentResult.NO_MATCHES, []

        return TournamentResult.CONTINUE, match_ids

    # =========================
    # Match Completion
    # =========================

    def _record_match_result(self, match_id: str, winner: str) -> None:
        if match_id not in self.match_players:
            self.logger.error("Unknown match %s", match_id)
            raise ValueError(f"Unknown match {match_id}")

        a, b = self.match_players.pop(match_id)

        if winner not in (a, b):
            self.logger.error("Invalid winner %s for match %s", winner, match_id)
            raise ValueError("Invalid winner")

        loser = b if winner == a else a
        self.active_players.remove(loser)

        self.completed_matches.append(match_id)

    def _dequeue_completed_matches(self) -> list[str]:
        batch: list[str] = []

        for _ in range(min(self.MAX_MATCHES_PER_POLL, len(self.completed_matches))):
            batch.append(self.completed_matches.popleft())

        return batch

    # =========================
    # Round Advancement
    # =========================

    def _advance_round_if_ready(self) -> None:
        self.logger.info(
            "Advancing round check: %d active players, %d matches remaining",
            len(self.active_players),
            len(self.match_players),
        )
        if len(self.match_players) > 0:
            return

        if len(self.active_players) == 1:
            self.is_finished = True
            self.winner = self.active_players[0]
            return

        self.current_round_index += 1
        self.validate_round_state()
        self.logger.info(
            "Advanced to round %s (%d players)",
            self.current_round.code,
            len(self.active_players),
        )

    # =========================
    # Persistence
    # =========================

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "config": self.config,
            "current_round_index": self.current_round_index,
            "active_players": list(self.active_players),
            "completed_matches": list(self.completed_matches),
            "match_players": self.match_players,
            "is_finished": self.is_finished,
            "winner": self.winner,
        }

    @classmethod
    def from_state(cls, data: dict) -> "Tournament":
        tournament = cls(data["id"], data["config"])

        tournament.current_round_index = data["current_round_index"]
        tournament.active_players = list(data["active_players"])
        tournament.completed_matches = deque(data["completed_matches"])
        tournament.match_players = dict(data["match_players"])
        tournament.is_finished = data["is_finished"]
        tournament.winner = data["winner"]

        return tournament
