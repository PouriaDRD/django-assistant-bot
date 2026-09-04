from __future__ import annotations

from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class SchedulerRuntimeStatus(StrEnum):
    """
    Current runtime state of the backup scheduler.
    """

    RUNNING = "running"

    PAUSED = "paused"

    STOPPED = "stopped"


class SystemStatusSchema(BaseModel):
    """
    Read-only snapshot of application and host runtime status.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    # =====================================================
    # APPLICATION
    # =====================================================

    bot_enabled: bool

    backup_enabled: bool

    proxy_enabled: bool

    retention_enabled: bool

    database_healthy: bool

    scheduler_status: SchedulerRuntimeStatus

    uptime_seconds: float = Field(
        ge=0,
    )

    # =====================================================
    # PROJECTS
    # =====================================================

    project_count: int = Field(
        ge=0,
    )

    enabled_project_count: int = Field(
        ge=0,
    )

    scheduled_project_count: int = Field(
        ge=0,
    )

    admin_count: int = Field(
        ge=0,
    )

    # =====================================================
    # RUNTIME
    # =====================================================

    python_version: str

    operating_system: str

    operating_system_version: str

    architecture: str

    # =====================================================
    # CPU
    # =====================================================

    cpu_usage_percent: float = Field(
        ge=0,
        le=100,
    )

    cpu_physical_cores: int | None = Field(
        default=None,
        ge=1,
    )

    cpu_logical_cores: int = Field(
        ge=1,
    )

    # =====================================================
    # MEMORY
    # =====================================================

    memory_total_bytes: int = Field(
        ge=0,
    )

    memory_used_bytes: int = Field(
        ge=0,
    )

    memory_available_bytes: int = Field(
        ge=0,
    )

    memory_usage_percent: float = Field(
        ge=0,
        le=100,
    )

    # =====================================================
    # DISK
    # =====================================================

    disk_total_bytes: int = Field(
        ge=0,
    )

    disk_used_bytes: int = Field(
        ge=0,
    )

    disk_free_bytes: int = Field(
        ge=0,
    )

    disk_usage_percent: float = Field(
        ge=0,
        le=100,
    )


__all__ = [
    "SchedulerRuntimeStatus",
    "SystemStatusSchema",
]
