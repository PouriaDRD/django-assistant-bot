from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram.types import Message

from django_assistant_bot.bot.handlers.projects.create import (
    project_schedule_handler,
)
from django_assistant_bot.bot.states.project import (
    ProjectCreationState,
)
from django_assistant_bot.core.environment import (
    AppEnvironment,
)

# =========================================================
# CONSTANTS
# =========================================================


PRODUCTION_MINIMUM_INTERVAL_MESSAGE = "حداقل فاصله در محیط پروداکشن 15 دقیقه است."


# =========================================================
# BUILDERS
# =========================================================


def build_context(
    environment: AppEnvironment,
):
    """
    Build minimal application context required by schedule
    environment validation.
    """

    return SimpleNamespace(
        environment=SimpleNamespace(
            environment=environment,
        ),
    )


def build_callback(
    data: str,
):
    """
    Build minimal callback query object.
    """

    message = Mock(
        spec=Message,
    )

    message.edit_text = AsyncMock()

    return SimpleNamespace(
        data=data,
        answer=AsyncMock(),
        message=message,
    )


def build_state():
    """
    Build minimal FSM context used by schedule handler.
    """

    return SimpleNamespace(
        update_data=AsyncMock(),
        get_data=AsyncMock(
            return_value={
                "project_name": "Test Project",
                "database_path": "/tmp/db.sqlite3",
                "media_path": "/tmp/media",
            }
        ),
        set_state=AsyncMock(),
        clear=AsyncMock(),
    )


# =========================================================
# PRODUCTION
# =========================================================


@pytest.mark.asyncio
async def test_production_rejects_one_minute_schedule() -> None:
    callback = build_callback(
        "project:schedule:1:minutes",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.PRODUCTION,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    callback.answer.assert_awaited_once_with(
        PRODUCTION_MINIMUM_INTERVAL_MESSAGE,
        show_alert=True,
    )

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()

    state.clear.assert_not_awaited()

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_production_rejects_two_minute_schedule() -> None:
    callback = build_callback(
        "project:schedule:2:minutes",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.PRODUCTION,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    callback.answer.assert_awaited_once_with(
        PRODUCTION_MINIMUM_INTERVAL_MESSAGE,
        show_alert=True,
    )

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_production_rejects_five_minute_schedule() -> None:
    callback = build_callback(
        "project:schedule:5:minutes",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.PRODUCTION,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    callback.answer.assert_awaited_once_with(
        PRODUCTION_MINIMUM_INTERVAL_MESSAGE,
        show_alert=True,
    )

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_production_rejects_ten_minute_schedule() -> None:
    callback = build_callback(
        "project:schedule:10:minutes",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.PRODUCTION,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    callback.answer.assert_awaited_once_with(
        PRODUCTION_MINIMUM_INTERVAL_MESSAGE,
        show_alert=True,
    )

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()

    state.clear.assert_not_awaited()

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_production_accepts_fifteen_minutes() -> None:
    callback = build_callback(
        "project:schedule:15:minutes",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.PRODUCTION,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    state.update_data.assert_awaited_once()

    state.set_state.assert_awaited_once_with(
        ProjectCreationState.waiting_for_confirmation,
    )

    callback.answer.assert_awaited_once_with()

    callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_production_accepts_thirty_minutes() -> None:
    callback = build_callback(
        "project:schedule:30:minutes",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.PRODUCTION,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    state.update_data.assert_awaited_once()

    state.set_state.assert_awaited_once_with(
        ProjectCreationState.waiting_for_confirmation,
    )


@pytest.mark.asyncio
async def test_production_accepts_hour_schedule() -> None:
    callback = build_callback(
        "project:schedule:1:hours",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.PRODUCTION,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    state.update_data.assert_awaited_once()

    state.set_state.assert_awaited_once_with(
        ProjectCreationState.waiting_for_confirmation,
    )


# =========================================================
# DEVELOPMENT
# =========================================================


@pytest.mark.asyncio
async def test_development_accepts_one_minute_schedule() -> None:
    callback = build_callback(
        "project:schedule:1:minutes",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.DEVELOPMENT,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    state.update_data.assert_awaited_once()

    state.set_state.assert_awaited_once_with(
        ProjectCreationState.waiting_for_confirmation,
    )


@pytest.mark.asyncio
async def test_development_accepts_ten_minute_schedule() -> None:
    callback = build_callback(
        "project:schedule:10:minutes",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.DEVELOPMENT,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    state.update_data.assert_awaited_once()

    state.set_state.assert_awaited_once_with(
        ProjectCreationState.waiting_for_confirmation,
    )


# =========================================================
# TESTING
# =========================================================


@pytest.mark.asyncio
async def test_testing_accepts_one_minute_schedule() -> None:
    callback = build_callback(
        "project:schedule:1:minutes",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.TESTING,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    state.update_data.assert_awaited_once()

    state.set_state.assert_awaited_once_with(
        ProjectCreationState.waiting_for_confirmation,
    )


@pytest.mark.asyncio
async def test_testing_accepts_ten_minute_schedule() -> None:
    callback = build_callback(
        "project:schedule:10:minutes",
    )

    state = build_state()

    context = build_context(
        AppEnvironment.TESTING,
    )

    await project_schedule_handler(
        callback,
        state,
        context,
    )

    state.update_data.assert_awaited_once()

    state.set_state.assert_awaited_once_with(
        ProjectCreationState.waiting_for_confirmation,
    )
