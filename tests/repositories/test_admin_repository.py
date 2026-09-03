from __future__ import annotations

import pytest

from django_assistant_bot.database.session import SessionManager
from django_assistant_bot.repositories.admin import AdminRepository
from django_assistant_bot.repositories.exceptions import (
    DuplicateEntityError,
)
from django_assistant_bot.schemas.admin import AdminCreateSchema


def test_create_admin(
    session_manager: SessionManager,
) -> None:
    repository = AdminRepository(
        session_manager,
    )

    admin = repository.create(
        AdminCreateSchema(
            telegram_user_id=123456789,
        )
    )

    assert admin.telegram_user_id == 123456789


def test_admin_exists(
    session_manager: SessionManager,
) -> None:
    repository = AdminRepository(
        session_manager,
    )

    repository.create(
        AdminCreateSchema(
            telegram_user_id=123456789,
        )
    )

    assert repository.exists(123456789)

    assert not repository.exists(987654321)


def test_duplicate_admin_is_rejected(
    session_manager: SessionManager,
) -> None:
    repository = AdminRepository(
        session_manager,
    )

    data = AdminCreateSchema(
        telegram_user_id=123456789,
    )

    repository.create(data)

    with pytest.raises(
        DuplicateEntityError,
    ):
        repository.create(data)


def test_list_admins(
    session_manager: SessionManager,
) -> None:
    repository = AdminRepository(
        session_manager,
    )

    repository.create(
        AdminCreateSchema(
            telegram_user_id=111,
        )
    )

    repository.create(
        AdminCreateSchema(
            telegram_user_id=222,
        )
    )

    admins = repository.list_all()

    assert len(admins) == 2

    assert {admin.telegram_user_id for admin in admins} == {
        111,
        222,
    }


def test_delete_admin(
    session_manager: SessionManager,
) -> None:
    repository = AdminRepository(
        session_manager,
    )

    repository.create(
        AdminCreateSchema(
            telegram_user_id=123,
        )
    )

    assert repository.delete(123) is True
    assert repository.exists(123) is False


def test_delete_unknown_admin_returns_false(
    session_manager: SessionManager,
) -> None:
    repository = AdminRepository(
        session_manager,
    )

    assert repository.delete(999999) is False
