from __future__ import annotations

import configparser
from pathlib import Path


def load_config(config_file: str = "config.ini") -> configparser.ConfigParser:
    """
    Loads a configuration file using configparser.

    Parameters:
        config_file (str): The name of the configuration file to load.
                           It is expected to be located in the current
                            working directory.

    Returns:
        configparser.ConfigParser: The loaded configuration object.

    Raises:
        ValueError: If the configuration file is missing, malformed, or empty.
    """
    config = configparser.ConfigParser()
    config_path = Path.cwd() / config_file

    if not config_path.is_file():
        raise ValueError(
            f"Configuration load failed: The file '{config_file}' "
            "does not exist or is not a regular file in the current "
            f"working directory: {Path.cwd()}"
        )

    try:
        config.read(config_path)
    except configparser.MissingSectionHeaderError as e:
        raise ValueError(
            f"Configuration load failed: The file '{config_file}' is "
            "not valid. Ensure it contains properly formatted sections."
        ) from e

    if not config.sections():
        raise ValueError(
            f"Configuration load failed: The file '{config_file}' was found "
            "but appears empty or improperly structured."
            "Check that it contains valid sections."
        )

    return config
