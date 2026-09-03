from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------
# Source layout
# ---------------------------------------------------------

CORE_DIRECTORY = Path(__file__).resolve().parent

PACKAGE_ROOT = CORE_DIRECTORY.parent

SOURCE_ROOT = PACKAGE_ROOT.parent

PROJECT_ROOT = SOURCE_ROOT.parent


# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

ENV_FILE = PROJECT_ROOT / ".env"


# ---------------------------------------------------------
# Runtime directories
# ---------------------------------------------------------

DATA_DIRECTORY = PROJECT_ROOT / "data"

BACKUPS_DIRECTORY = PROJECT_ROOT / "backups"

LOGS_DIRECTORY = PROJECT_ROOT / "logs"


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

DEFAULT_DATABASE_PATH = DATA_DIRECTORY / "bot.sqlite3"


# ---------------------------------------------------------
# Alembic
# ---------------------------------------------------------

ALEMBIC_DIRECTORY = PROJECT_ROOT / "alembic"
