from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class AdminCreateSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    telegram_user_id: int = Field(
        gt=0,
    )


class AdminSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    telegram_user_id: int

    created_at: datetime
