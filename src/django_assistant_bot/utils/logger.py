from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIRECTORY = Path("logs")
LOG_FILE = LOG_DIRECTORY / "app.log"

MAX_LOG_SIZE = 10 * 1024 * 1024
BACKUP_COUNT = 5


def setup_logging() -> None:
    LOG_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    formatter = logging.Formatter(
        fmt=("%(asctime)s | " "%(levelname)-8s | " "%(name)s | " "%(message)s"),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )

    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()

    root_logger.setLevel(logging.INFO)

    root_logger.handlers.clear()

    root_logger.addHandler(
        file_handler,
    )

    root_logger.addHandler(
        console_handler,
    )
