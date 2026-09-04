from __future__ import annotations

from pathlib import (
    Path,
)

from django_assistant_bot.core.bootstrap import (
    bootstrap_application,
)
from django_assistant_bot.services.backup import (
    BackupError,
    BackupService,
)
from django_assistant_bot.services.project import (
    ProjectError,
)
from django_assistant_bot.services.resource_monitor import (
    BackupBenchmarkResult,
    benchmark_backup,
)

# =========================================================
# EXIT CODES
# =========================================================


EXIT_SUCCESS = 0

EXIT_FAILURE = 1


# =========================================================
# FORMATTERS
# =========================================================


def format_bytes(
    value: int,
) -> str:
    """
    Format byte values using compact binary units.
    """

    size = float(
        value,
    )

    units = (
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    )

    for unit in units:
        if abs(size) < 1024.0:
            return f"{size:.2f} {unit}"

        size /= 1024.0

    return f"{size:.2f} PB"


def format_signed_bytes(
    value: int,
) -> str:
    """
    Format a signed byte delta.
    """

    if value > 0:
        return "+" f"{format_bytes(value)}"

    if value < 0:
        return "-" f"{format_bytes(abs(value))}"

    return format_bytes(
        0,
    )


def format_compression_ratio(
    ratio: float,
) -> str:
    """
    Format archive/source size ratio as percentage.
    """

    return f"{ratio * 100:.2f}%"


def format_benchmark(
    *,
    project_name: str,
    project_id: str,
    result: BackupBenchmarkResult,
) -> str:
    """
    Build human-readable benchmark output.
    """

    lines = [
        "Backup Benchmark",
        "",
        f"Project: {project_name}",
        f"Project ID: {project_id}",
        "",
        ("Duration: " f"{result.duration_seconds:.3f} s"),
        "",
        ("RSS before: " f"{format_bytes(result.rss_before_bytes)}"),
        ("RSS after: " f"{format_bytes(result.rss_after_bytes)}"),
        ("RSS delta: " f"{format_signed_bytes(result.rss_delta_bytes)}"),
        ("Thread delta: " f"{result.thread_delta:+d}"),
        "",
        ("Disk read: " f"{format_bytes(result.read_bytes)}"),
        ("Disk write: " f"{format_bytes(result.write_bytes)}"),
        "",
        ("Database size: " f"{format_bytes(result.database_size_bytes)}"),
        ("Media size: " f"{format_bytes(result.media_size_bytes)}"),
        ("Archive size: " f"{format_bytes(result.archive_size_bytes)}"),
        ("Media files: " f"{result.media_file_count}"),
        ("Compression ratio: " f"{format_compression_ratio(result.compression_ratio)}"),
    ]

    return "\n".join(
        lines,
    )


# =========================================================
# BACKUP BENCHMARK
# =========================================================


def benchmark_backup_command(
    project_id: str,
) -> int:
    """
    Run a real backup benchmark for one persisted project.

    This command intentionally bypasses:
    - BackupCoordinator
    - history persistence
    - retention
    - scheduler
    - Telegram delivery

    Only the core backup pipeline is measured.
    """

    normalized_project_id = project_id.strip()

    if not normalized_project_id:
        print("Project ID cannot be empty.")

        return EXIT_FAILURE

    bootstrap = bootstrap_application()

    archive_path: Path | None = None

    try:
        # -------------------------------------------------
        # LOAD CONFIGURATION
        # -------------------------------------------------

        try:
            project = bootstrap.context.projects.get_project(
                normalized_project_id,
            )

        except ProjectError:
            print(("Could not load project: " f"{normalized_project_id}"))

            return EXIT_FAILURE

        settings = bootstrap.context.settings.get_settings()

        # -------------------------------------------------
        # BUILD CORE BACKUP SERVICE
        # -------------------------------------------------

        backup_service = BackupService(
            backup_directory=(settings.backup_directory),
            compression_level=(settings.compression_level),
        )

        # -------------------------------------------------
        # BENCHMARK
        # -------------------------------------------------

        try:
            backup_result, benchmark = benchmark_backup(
                run_backup=(
                    lambda: (
                        backup_service.backup_project(
                            project,
                        )
                    )
                ),
            )

        except BackupError:
            print(("Backup benchmark failed " "during backup execution."))

            return EXIT_FAILURE

        archive_path = backup_result.archive_path

        print(
            format_benchmark(
                project_name=(project.name),
                project_id=(project.id),
                result=benchmark,
            )
        )

        print()

        print(("Archive: " f"{archive_path}"))

        return EXIT_SUCCESS

    finally:
        bootstrap.engine.dispose()


# =========================================================
# EXPORTS
# =========================================================


__all__ = [
    "EXIT_FAILURE",
    "EXIT_SUCCESS",
    "benchmark_backup_command",
    "format_benchmark",
    "format_bytes",
    "format_compression_ratio",
    "format_signed_bytes",
]
