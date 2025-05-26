from __future__ import annotations

import configparser
from logging import Logger
from pathlib import Path

from utils.logger import get_logger


class BackendFileStorage:
    """
    Provides file-based storage for game data within a specified directory.
    Ensures that game files are accessed and created consistently.
    """

    def __init__(
        self,
        config: configparser.ConfigParser,
        logger: Logger | None = None,
    ) -> None:
        """
        Initialize the BackendFileStorage instance.

        Args:
            config (ConfigParser): Application configuration containing
                                    storage settings.
            logger (Optional[Logger]): Optional logger instance. If not provided,
                a default logger is used.
        """
        self.logger = logger or get_logger(self.__class__.__name__)
        try:
            self._storage_dir = Path(
                config.get("app", "gameDataDir", fallback="/data/games")
            ).resolve()
            self._file_extension = config.get("app", "gameFileExt", fallback=".json")

            if not self._file_extension.startswith("."):
                self.logger.warning(
                    f"File extension '{self._file_extension}' does not start "
                    "with a '.', prepending."
                )
                self._file_extension = f".{self._file_extension}"

            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(
                f"Ensured storage directory exists: {self._storage_dir}"
            )

        except configparser.Error as config_error:
            self.logger.exception("Invalid configuration provided for file storage.")
            raise ValueError("Invalid storage configuration.") from config_error

        except OSError as os_error:
            self.logger.exception(
                f"Failed to create or access storage directory: {self._storage_dir}"
            )
            raise RuntimeError(
                f"Unable to initialize file storage directory: {self._storage_dir}"
            ) from os_error

    def get_game_path(self, game_id: str) -> Path:
        """
        Build the full file path for a specific game's data file.

        Args:
            game_id (str): Unique identifier for the game.

        Returns:
            Path: Path to the corresponding game data file.
        """
        game_file = self._storage_dir / f"{game_id}{self._file_extension}"
        self.logger.debug(f"Resolved game file path: {game_file}")
        return game_file
