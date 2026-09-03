from __future__ import annotations

from django_assistant_bot.repositories.admin import AdminRepository
from django_assistant_bot.repositories.exceptions import (
    DuplicateEntityError,
    PersistenceError,
)
from django_assistant_bot.schemas.admin import (
    AdminCreateSchema,
    AdminSchema,
)
from django_assistant_bot.services.admin.exceptions import (
    AdminAlreadyExistsError,
    AdminNotFoundError,
    AdminPersistenceError,
    AdminValidationError,
)


class AdminService:
    """
    Application service for Telegram administrator management.
    """

    def __init__(
        self,
        repository: AdminRepository,
    ) -> None:
        self._repository = repository

    def list_admins(self) -> list[AdminSchema]:
        try:
            return self._repository.list_all()

        except PersistenceError as exc:
            raise AdminPersistenceError("Could not load administrators.") from exc

    def is_admin(
        self,
        telegram_user_id: int,
    ) -> bool:
        self._validate_user_id(
            telegram_user_id,
        )

        try:
            return self._repository.exists(
                telegram_user_id,
            )

        except PersistenceError as exc:
            raise AdminPersistenceError("Could not check administrator.") from exc

    def add_admin(
        self,
        telegram_user_id: int,
    ) -> AdminSchema:
        self._validate_user_id(
            telegram_user_id,
        )

        try:
            return self._repository.create(
                AdminCreateSchema(
                    telegram_user_id=telegram_user_id,
                )
            )

        except DuplicateEntityError as exc:
            raise AdminAlreadyExistsError("Administrator already exists.") from exc

        except PersistenceError as exc:
            raise AdminPersistenceError("Could not create administrator.") from exc

    def remove_admin(
        self,
        telegram_user_id: int,
    ) -> None:
        self._validate_user_id(
            telegram_user_id,
        )

        try:
            deleted = self._repository.delete(
                telegram_user_id,
            )

        except PersistenceError as exc:
            raise AdminPersistenceError("Could not delete administrator.") from exc

        if not deleted:
            raise AdminNotFoundError("Administrator not found.")

    @staticmethod
    def _validate_user_id(
        telegram_user_id: int,
    ) -> None:
        if telegram_user_id <= 0:
            raise AdminValidationError("Telegram user ID must be positive.")
