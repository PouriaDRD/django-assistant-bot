from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)

from django_assistant_bot.database.models.admin import AdminModel
from django_assistant_bot.database.session import SessionManager
from django_assistant_bot.repositories.exceptions import (
    DuplicateEntityError,
    PersistenceError,
)
from django_assistant_bot.schemas.admin import (
    AdminCreateSchema,
    AdminSchema,
)


class AdminRepository:
    def __init__(
        self,
        sessions: SessionManager,
    ) -> None:
        self._sessions = sessions

    def list_all(self) -> list[AdminSchema]:
        try:
            with self._sessions.session() as session:
                statement = select(AdminModel).order_by(AdminModel.created_at.asc())

                models = list(session.scalars(statement))

                return [self._to_schema(model) for model in models]

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not load administrators.") from exc

    def exists(
        self,
        telegram_user_id: int,
    ) -> bool:
        try:
            with self._sessions.session() as session:
                model = session.get(
                    AdminModel,
                    telegram_user_id,
                )

                return model is not None

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not check administrator.") from exc

    def create(
        self,
        data: AdminCreateSchema,
    ) -> AdminSchema:
        model = AdminModel(
            telegram_user_id=(data.telegram_user_id),
        )

        try:
            with self._sessions.transaction() as session:
                session.add(model)
                session.flush()

                admin = self._to_schema(model)

            return admin

        except IntegrityError as exc:
            raise DuplicateEntityError("Administrator already exists.") from exc

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not create administrator.") from exc

    def delete(
        self,
        telegram_user_id: int,
    ) -> bool:
        try:
            with self._sessions.transaction() as session:
                model = session.get(
                    AdminModel,
                    telegram_user_id,
                )

                if model is None:
                    return False

                session.delete(model)

            return True

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not delete administrator.") from exc

    @staticmethod
    def _to_schema(
        model: AdminModel,
    ) -> AdminSchema:
        return AdminSchema(
            telegram_user_id=(model.telegram_user_id),
            created_at=model.created_at,
        )
