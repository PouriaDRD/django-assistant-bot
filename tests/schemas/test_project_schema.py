from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectCreateSchema,
)


def test_project_name_is_trimmed() -> None:
    project = ProjectCreateSchema(
        name="  test  ",
        database=DatabaseSchema(
            path=Path("/db.sqlite3"),
        ),
        media=MediaSchema(
            path=Path("/media"),
        ),
    )

    assert project.name == "test"


def test_empty_project_name_is_invalid() -> None:
    with pytest.raises(
        ValidationError,
    ):
        ProjectCreateSchema(
            name="   ",
            database=DatabaseSchema(
                path=Path("/db.sqlite3"),
            ),
            media=MediaSchema(
                path=Path("/media"),
            ),
        )
