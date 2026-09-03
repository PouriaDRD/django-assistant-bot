from __future__ import annotations

from django_assistant_bot.core.bootstrap import (
    bootstrap_application,
)


def test_application_bootstrap() -> None:
    bootstrap = bootstrap_application()

    try:
        assert bootstrap.engine is not None

        assert bootstrap.context.projects is not None

        assert bootstrap.context.admins is not None

        assert bootstrap.context.settings is not None

    finally:
        bootstrap.engine.dispose()
