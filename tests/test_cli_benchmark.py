from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import (
    Path,
)
from types import (
    SimpleNamespace,
)
from unittest.mock import (
    Mock,
    patch,
)

from django_assistant_bot import (
    cli_benchmark,
)
from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    ChecksumResult,
)
from django_assistant_bot.services.resource_monitor import (
    BackupBenchmarkResult,
)

# =========================================================
# HELPERS
# =========================================================


def build_project() -> SimpleNamespace:
    return SimpleNamespace(
        id="project-1",
        name="Test Project",
    )


def build_backup_result() -> BackupResult:
    now = datetime.now(
        timezone.utc,
    )

    return BackupResult(
        project_id="project-1",
        project_name="Test Project",
        status=BackupStatus.SUCCESS,
        archive_path=Path(
            "backup.zip",
        ),
        started_at=now,
        finished_at=now,
        database_size_bytes=(1024),
        media_size_bytes=(2048),
        archive_size_bytes=(1536),
        media_file_count=(10),
        checksum=ChecksumResult(
            algorithm="sha256",
            value="abc123",
        ),
    )


def build_benchmark_result() -> BackupBenchmarkResult:
    return BackupBenchmarkResult(
        duration_seconds=1.25,
        rss_before_bytes=(10 * 1024 * 1024),
        rss_after_bytes=(12 * 1024 * 1024),
        rss_delta_bytes=(2 * 1024 * 1024),
        thread_delta=0,
        read_bytes=(5 * 1024 * 1024),
        write_bytes=(3 * 1024 * 1024),
        database_size_bytes=(1024),
        media_size_bytes=(2048),
        archive_size_bytes=(1536),
        media_file_count=10,
        compression_ratio=0.5,
    )


def build_bootstrap() -> SimpleNamespace:
    projects = Mock()

    projects.get_project.return_value = build_project()

    settings = Mock()

    settings.get_settings.return_value = AppSettingsSchema()

    context = SimpleNamespace(
        projects=projects,
        settings=settings,
    )

    engine = Mock()

    return SimpleNamespace(
        context=context,
        engine=engine,
    )


# =========================================================
# FORMATTERS
# =========================================================


def test_format_bytes() -> None:
    assert (
        cli_benchmark.format_bytes(
            1024,
        )
        == "1.00 KB"
    )

    assert (
        cli_benchmark.format_bytes(
            1024 * 1024,
        )
        == "1.00 MB"
    )


def test_format_signed_bytes() -> None:
    assert (
        cli_benchmark.format_signed_bytes(
            1024,
        )
        == "+1.00 KB"
    )

    assert (
        cli_benchmark.format_signed_bytes(
            -1024,
        )
        == "-1.00 KB"
    )


def test_format_benchmark_contains_metrics() -> None:
    output = cli_benchmark.format_benchmark(
        project_name=("Test Project"),
        project_id=("project-1"),
        result=(build_benchmark_result()),
    )

    assert "Backup Benchmark" in output

    assert "Test Project" in output

    assert "1.250 s" in output

    assert "2.00 MB" in output

    assert "Compression ratio: 50.00%" in output


# =========================================================
# COMMAND
# =========================================================


def test_backup_benchmark_command() -> None:
    bootstrap = build_bootstrap()

    backup_result = build_backup_result()

    benchmark_result = build_benchmark_result()

    backup_service = Mock()

    with (
        patch.object(
            cli_benchmark,
            "bootstrap_application",
            return_value=bootstrap,
        ),
        patch.object(
            cli_benchmark,
            "BackupService",
            return_value=backup_service,
        ) as backup_service_class,
        patch.object(
            cli_benchmark,
            "benchmark_backup",
            return_value=(
                backup_result,
                benchmark_result,
            ),
        ) as benchmark_runner,
    ):
        exit_code = cli_benchmark.benchmark_backup_command(
            "project-1",
        )

    assert exit_code == 0

    bootstrap.context.projects.get_project.assert_called_once_with(
        "project-1",
    )

    backup_service_class.assert_called_once()

    benchmark_runner.assert_called_once()

    bootstrap.engine.dispose.assert_called_once_with()


def test_empty_project_id_fails_without_bootstrap() -> None:
    with patch.object(
        cli_benchmark,
        "bootstrap_application",
    ) as bootstrap:
        exit_code = cli_benchmark.benchmark_backup_command(
            "   ",
        )

    assert exit_code == 1

    bootstrap.assert_not_called()
