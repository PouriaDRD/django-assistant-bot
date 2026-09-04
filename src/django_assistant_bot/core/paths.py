from __future__ import annotations

from pathlib import Path

# =========================================================
# SOURCE LAYOUT
# =========================================================


CORE_DIRECTORY = Path(__file__).resolve().parent

PACKAGE_ROOT = CORE_DIRECTORY.parent

SOURCE_ROOT = PACKAGE_ROOT.parent

PROJECT_ROOT = SOURCE_ROOT.parent


# =========================================================
# ENVIRONMENT
# =========================================================


ENV_FILE = PROJECT_ROOT / ".env"


# =========================================================
# RUNTIME DIRECTORIES
# =========================================================


DATA_DIRECTORY = PROJECT_ROOT / "data"

BACKUPS_DIRECTORY = DATA_DIRECTORY / "backups"

LOGS_DIRECTORY = PROJECT_ROOT / "logs"


# =========================================================
# DATABASE
# =========================================================


DATABASE_PATH = DATA_DIRECTORY / "bot.sqlite3"


# =========================================================
# ALEMBIC
# =========================================================


ALEMBIC_DIRECTORY = PROJECT_ROOT / "alembic"


__all__ = [
    "ALEMBIC_DIRECTORY",
    "BACKUPS_DIRECTORY",
    "CORE_DIRECTORY",
    "DATABASE_PATH",
    "DATA_DIRECTORY",
    "ENV_FILE",
    "LOGS_DIRECTORY",
    "PACKAGE_ROOT",
    "PROJECT_ROOT",
    "SOURCE_ROOT",
]
