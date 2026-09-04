from __future__ import annotations

from django_assistant_bot.core.bootstrap import (
    bootstrap_application,
)
from django_assistant_bot.services.project import (
    ProjectError,
)
from django_assistant_bot.services.resource_monitor import (
    CompressionBenchmarkResult,
    benchmark_compression_levels,
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
    Format bytes using binary units.
    """

    size = float(value)

    for unit in (
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ):
        if abs(size) < 1024:
            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} PB"


def format_signed_bytes(
    value: int,
) -> str:
    """
    Format signed memory delta.
    """

    if value > 0:
        return "+" f"{format_bytes(value)}"

    if value < 0:
        return "-" f"{format_bytes(abs(value))}"

    return format_bytes(0)


def format_compression_benchmark(
    result: CompressionBenchmarkResult,
) -> str:
    """
    Format compression benchmark table.
    """

    lines = [
        "Compression Benchmark",
        "",
        ("Project: " f"{result.project_name}"),
        ("Project ID: " f"{result.project_id}"),
        ("Runs per level: " f"{result.runs_per_level}"),
        "",
        ("Level | Median | Min | Max | " "Archive | Ratio | Read | Write | RSS Δ"),
        ("----- | ------ | --- | --- | " "------- | ----- | ---- | ----- | -----"),
    ]

    for item in result.levels:
        lines.append(
            (
                f"{item.compression_level} | "
                f"{item.median_duration_seconds:.3f}s | "
                f"{item.min_duration_seconds:.3f}s | "
                f"{item.max_duration_seconds:.3f}s | "
                f"{format_bytes(item.median_archive_size_bytes)} | "
                f"{item.median_compression_ratio * 100:.2f}% | "
                f"{format_bytes(item.median_read_bytes)} | "
                f"{format_bytes(item.median_write_bytes)} | "
                f"{format_signed_bytes(item.median_rss_delta_bytes)}"
            )
        )

    return "\n".join(lines)


# =========================================================
# COMMAND
# =========================================================


def compression_benchmark_command(
    project_id: str,
    *,
    runs: int = 5,
) -> int:
    """
    Run compression-level benchmark for one project.
    """

    normalized_project_id = project_id.strip()

    if not normalized_project_id:
        print("Project ID cannot be empty.")

        return EXIT_FAILURE

    if runs < 1:
        print("Runs must be at least 1.")

        return EXIT_FAILURE

    bootstrap = bootstrap_application()

    try:
        try:
            project = bootstrap.context.projects.get_project(normalized_project_id)

        except ProjectError:
            print(("Could not load project: " f"{normalized_project_id}"))

            return EXIT_FAILURE

        settings = bootstrap.context.settings.get_settings()

        print(
            (
                "Running compression benchmark...\n"
                "This may create temporary backup archives."
            )
        )

        result = benchmark_compression_levels(
            project=project,
            backup_directory=(settings.backup_directory),
            runs_per_level=runs,
            cleanup_archives=True,
        )

        print()

        print(format_compression_benchmark(result))

        return EXIT_SUCCESS

    finally:
        bootstrap.engine.dispose()


__all__ = [
    "EXIT_FAILURE",
    "EXIT_SUCCESS",
    "compression_benchmark_command",
    "format_compression_benchmark",
]
