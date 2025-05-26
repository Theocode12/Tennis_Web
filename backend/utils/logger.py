"""
App-specific logging module with configurable logger setup.

This module provides an `AppLogger` class for configuring application loggers
based on a configuration file. It includes support for console output, rotating
file handlers, and a null handler for disabling logging gracefully.

Functions:
    get_logger(name): Returns a configured logger instance.
"""

from __future__ import annotations

import logging
from configparser import ConfigParser
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .load_config import load_config


class AppLogger:
    """
    A configurable application logger.

    Sets up logging based on values from a config file.
    Supports console output, rotating file handlers, and configurable log
    levels and formats.
    """

    def __init__(
        self, name: str = "app", config: ConfigParser | None = None
    ) -> None:
        """
        Initialize AppLogger with a logger name and optional config.

        Args:
            name (str): Logger name. Defaults to "app".
            config (Optional[ConfigParser]): Config object.
             Loads from file if None.
        """
        self.config = config or load_config()
        self.logger = logging.getLogger(name)
        self.logger.propagate = False

    def get_logger(self) -> logging.Logger:
        """
        Return a logger instance, disabling it if configured as such.

        Returns:
            logging.Logger: The configured logger instance.
        """
        logging_enabled = self.config.getboolean("logging", "enabled", fallback=True)

        if not logging_enabled:
            self.logger.handlers.clear()
            self.logger.addHandler(logging.NullHandler())
            return self.logger

        return self.logger

    def set_log_level(self) -> None:
        """
        Set the logger's log level based on the config.
        Defaults to DEBUG if level is invalid or missing.
        """
        level_str = self.config.get("logging", "level", fallback="DEBUG").upper()
        log_level = getattr(logging, level_str, logging.DEBUG)
        self.logger.setLevel(log_level)

    def get_formatter(self) -> logging.Formatter:
        """
        Create a log formatter using config-defined format and date format.

        Returns:
            logging.Formatter: Configured formatter.
        """
        log_format = self.config.get(
            "logging",
            "logFormat",
            fallback="%(asctime)s [%(levelname)s] %(message)s",
            raw=True,
        )
        date_format = self.config.get(
            "logging", "dateFormat", fallback="%Y-%m-%dT%H:%M:%S", raw=True
        )
        return logging.Formatter(log_format, datefmt=date_format)

    def set_console_handler(self) -> None:
        """
        Add a StreamHandler to output logs to the console if enabled.
        """
        if self.config.getboolean("logging", "consoleLogs", fallback=True):
            handler = logging.StreamHandler()
            handler.setFormatter(self.get_formatter())
            self.logger.addHandler(handler)

    def set_file_handler(self) -> None:
        """
        Add a RotatingFileHandler to log to a file if enabled.
        """
        if not self.config.getboolean("logging", "serverLogs", fallback=True):
            return

        logfile = self.config.get(
            "logging", "serverLogFile", fallback="logs/server.log"
        )
        max_file_size = self.config.getint(
            "logging", "maxFileSize", fallback=10 * 1024 * 1024
        )
        backup_count = self.config.getint("logging", "backupCount", fallback=5)

        log_path = Path(logfile)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        handler = RotatingFileHandler(
            logfile, maxBytes=max_file_size, backupCount=backup_count
        )
        handler.setFormatter(self.get_formatter())
        self.logger.addHandler(handler)


def get_logger(
    name: str = "app", config: ConfigParser | None = None
) -> logging.Logger:
    """
    Return a configured logger instance.

    If logging is disabled, the logger will use a NullHandler.

    Args:
        name (str): Logger name. Defaults to "app".
        config (Optional[ConfigParser]): Optional config object.

    Returns:
        logging.Logger: Fully configured logger.
    """
    app_logger = AppLogger(name, config)
    logger = app_logger.get_logger()

    if any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        return logger

    if not logger.handlers:
        app_logger.set_log_level()
        app_logger.set_console_handler()
        app_logger.set_file_handler()

    return logger
