import logging
import sys
from typing import Optional


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns a configured logger instance for RepoEvolution modules.

    Standard log format:
    [TIMESTAMP] [LEVEL] [LOGGER_NAME] - MESSAGE
    """
    logger = logging.getLogger(name or "repoevolution")

    # If handlers are already configured, return existing logger to avoid duplicate log lines
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
