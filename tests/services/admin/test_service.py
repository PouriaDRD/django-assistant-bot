from __future__ import annotations

import pytest

from django_assistant_bot.database.session import (
    SessionManager,
)
from django_assistant_bot.repositories.admin import (
    AdminRepository,
)
from django_assistant_bot.services.admin import (
    AdminAlreadyExistsError,
    AdminNotFoundError,
    AdminService,
    AdminValidationError,
    LastAdminRemovalError,
)


@pytest.fixture()
def service(
    session_manager: SessionManager,
) -> AdminService:
    return AdminService(
        AdminRepository(
            session_manager,
        )
    )


# =========================================================
# CREATE
# =========================================================


def test_add_admin(
    service: AdminService,
) -> None:
    admin = service.add_admin(
        123456789,
    )

    assert admin.telegram_user_id == 123456789


def test_duplicate_admin_fails(
    service: AdminService,
) -> None:
    service.add_admin(
        123456789,
    )

    with pytest.raises(
        AdminAlreadyExistsError,
    ):
        service.add_admin(
            123456789,
        )


# =========================================================
# READ
# =========================================================


def test_is_admin(
    service: AdminService,
) -> None:
    service.add_admin(
        123456789,
    )

    assert (
        service.is_admin(
            123456789,
        )
        is True
    )

    assert (
        service.is_admin(
            987654321,
        )
        is False
    )


def test_list_admins(
    service: AdminService,
) -> None:
    service.add_admin(
        111,
    )

    service.add_admin(
        222,
    )

    admins = service.list_admins()

    assert {admin.telegram_user_id for admin in admins} == {
        111,
        222,
    }


# =========================================================
# DELETE
# =========================================================


def test_remove_admin(
    service: AdminService,
) -> None:
    service.add_admin(
        123,
    )

    service.add_admin(
        456,
    )

    service.remove_admin(
        123,
    )

    assert (
        service.is_admin(
            123,
        )
        is False
    )

    assert (
        service.is_admin(
            456,
        )
        is True
    )


def test_remove_unknown_admin_fails(
    service: AdminService,
) -> None:
    with pytest.raises(
        AdminNotFoundError,
    ):
        service.remove_admin(
            999,
        )


def test_last_admin_cannot_be_removed(
    service: AdminService,
) -> None:
    service.add_admin(
        123,
    )

    with pytest.raises(
        LastAdminRemovalError,
    ):
        service.remove_admin(
            123,
        )

    assert (
        service.is_admin(
            123,
        )
        is True
    )


def test_admin_can_be_removed_when_another_admin_exists(
    service: AdminService,
) -> None:
    service.add_admin(
        111,
    )

    service.add_admin(
        222,
    )

    service.remove_admin(
        111,
    )

    assert (
        service.is_admin(
            111,
        )
        is False
    )

    assert (
        service.is_admin(
            222,
        )
        is True
    )


# =========================================================
# VALIDATION
# =========================================================


@pytest.mark.parametrize(
    "telegram_user_id",
    [
        0,
        -1,
        -100,
    ],
)
def test_invalid_admin_id_fails(
    service: AdminService,
    telegram_user_id: int,
) -> None:
    with pytest.raises(
        AdminValidationError,
    ):
        service.add_admin(
            telegram_user_id,
        )
