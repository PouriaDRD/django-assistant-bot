from __future__ import annotations

from django_assistant_bot.repositories.admin import (
    AdminRepository,
)
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
    LastAdminRemovalError,
)


class AdminService:
    """
    Application service for Telegram administrator
    management.
    """

    def __init__(
        self,
        repository: AdminRepository,
    ) -> None:
        self._repository = repository

    # =====================================================
    # READ
    # =====================================================

    def list_admins(
        self,
    ) -> list[AdminSchema]:
        """
        Return all configured Telegram administrators.
        """

        try:
            return self._repository.list_all()

        except PersistenceError as exc:
            raise AdminPersistenceError("Could not load administrators.") from exc

    def is_admin(
        self,
        telegram_user_id: int,
    ) -> bool:
        """
        Return whether a Telegram user is an administrator.
        """

        self._validate_user_id(
            telegram_user_id,
        )

        try:
            return self._repository.exists(
                telegram_user_id,
            )

        except PersistenceError as exc:
            raise AdminPersistenceError("Could not check administrator.") from exc

    # =====================================================
    # CREATE
    # =====================================================

    def add_admin(
        self,
        telegram_user_id: int,
    ) -> AdminSchema:
        """
        Add a Telegram administrator.
        """

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

    # =====================================================
    # DELETE
    # =====================================================

    def remove_admin(
        self,
        telegram_user_id: int,
    ) -> None:
        """
        Remove a Telegram administrator.

        The final remaining administrator cannot be removed
        because doing so would permanently lock access to
        the bot.
        """

        self._validate_user_id(
            telegram_user_id,
        )

        try:
            admins = self._repository.list_all()

        except PersistenceError as exc:
            raise AdminPersistenceError("Could not load administrators.") from exc

        if not any(admin.telegram_user_id == telegram_user_id for admin in admins):
            raise AdminNotFoundError("Administrator not found.")

        if len(admins) <= 1:
            raise LastAdminRemovalError("The final administrator cannot be removed.")

        try:
            deleted = self._repository.delete(
                telegram_user_id,
            )

        except PersistenceError as exc:
            raise AdminPersistenceError("Could not delete administrator.") from exc

        if not deleted:
            raise AdminNotFoundError("Administrator not found.")

    # =====================================================
    # VALIDATION
    # =====================================================

    @staticmethod
    def _validate_user_id(
        telegram_user_id: int,
    ) -> None:
        """
        Validate Telegram numeric user identifier.
        """

        if telegram_user_id <= 0:
            raise AdminValidationError("Telegram user ID must be positive.")
