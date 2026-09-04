from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection
from sqlalchemy.engine import Engine

import django_assistant_bot.database.models  # noqa: F401

from django_assistant_bot.core.paths import (
    DATABASE_PATH,
)
from django_assistant_bot.database.base import (
    Base,
)
from django_assistant_bot.database.engine import (
    build_database_url,
    create_database_engine,
)

# =========================================================
# ALEMBIC CONFIG
# =========================================================


config = context.config


if config.config_file_name is not None:
    fileConfig(
        config.config_file_name,
    )


# =========================================================
# DATABASE
# =========================================================


database_url = build_database_url(
    DATABASE_PATH,
)


config.set_main_option(
    "sqlalchemy.url",
    database_url.render_as_string(
        hide_password=False,
    ),
)


# =========================================================
# METADATA
# =========================================================


target_metadata = Base.metadata


# =========================================================
# OFFLINE MIGRATIONS
# =========================================================


def run_migrations_offline() -> None:
    """
    Run migrations without creating a live database
    connection.
    """

    context.configure(
        url=database_url.render_as_string(
            hide_password=False,
        ),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# =========================================================
# CONNECTION CONFIGURATION
# =========================================================


def configure_connection(
    connection: Connection,
) -> None:
    """
    Configure Alembic for a live database connection.
    """

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
    )


# =========================================================
# ONLINE MIGRATIONS
# =========================================================


def run_migrations_online() -> None:
    """
    Run migrations against the application's fixed
    SQLite database.
    """

    engine: Engine = create_database_engine()

    try:
        with engine.connect() as connection:
            configure_connection(
                connection,
            )

            with context.begin_transaction():
                context.run_migrations()

    finally:
        engine.dispose()


# =========================================================
# EXECUTION
# =========================================================


if context.is_offline_mode():
    run_migrations_offline()

else:
    run_migrations_online()
