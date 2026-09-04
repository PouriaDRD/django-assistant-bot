from __future__ import annotations

import statistics
from dataclasses import (
    dataclass,
)
from pathlib import (
    Path,
)

from django_assistant_bot.schemas.project import (
    ProjectSchema,
)
from django_assistant_bot.services.backup import (
    BackupService,
)
from django_assistant_bot.services.resource_monitor.benchmark import (
    BackupBenchmarkResult,
    benchmark_backup,
)

# =========================================================
# DEFAULTS
# =========================================================


DEFAULT_COMPRESSION_LEVELS = (
    0,
    1,
    3,
    6,
    9,
)

DEFAULT_RUNS_PER_LEVEL = 5


# =========================================================
# RESULT MODELS
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class CompressionLevelBenchmark:
    """
    Aggregated benchmark metrics for one compression level.
    """

    compression_level: int

    runs: int

    median_duration_seconds: float

    min_duration_seconds: float

    max_duration_seconds: float

    median_archive_size_bytes: int

    median_compression_ratio: float

    median_read_bytes: int

    median_write_bytes: int

    median_rss_delta_bytes: int


@dataclass(
    frozen=True,
    slots=True,
)
class CompressionBenchmarkResult:
    """
    Complete multi-level compression benchmark.
    """

    project_id: str

    project_name: str

    runs_per_level: int

    levels: tuple[
        CompressionLevelBenchmark,
        ...,
    ]


# =========================================================
# BENCHMARK
# =========================================================


def benchmark_compression_levels(
    *,
    project: ProjectSchema,
    backup_directory: Path,
    compression_levels: tuple[int, ...] = (DEFAULT_COMPRESSION_LEVELS),
    runs_per_level: int = (DEFAULT_RUNS_PER_LEVEL),
    cleanup_archives: bool = True,
) -> CompressionBenchmarkResult:
    """
    Benchmark multiple ZIP compression levels.

    Each level is executed multiple times.

    Median values are used because filesystem cache,
    scheduler activity and operating-system noise can
    distort individual runs.

    Benchmark archives are removed after each run by
    default.
    """

    if runs_per_level < 1:
        raise ValueError("runs_per_level must be at least 1.")

    if not compression_levels:
        raise ValueError("At least one compression level is required.")

    results: list[CompressionLevelBenchmark] = []

    for compression_level in compression_levels:
        if not 0 <= compression_level <= 9:
            raise ValueError(("Compression level must be " "between 0 and 9."))

        level_runs: list[BackupBenchmarkResult] = []

        for _ in range(runs_per_level):
            backup_service = BackupService(
                backup_directory=(backup_directory),
                compression_level=(compression_level),
            )

            archive_path: Path | None = None

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

                archive_path = backup_result.archive_path

                level_runs.append(benchmark)

            finally:
                if cleanup_archives and archive_path is not None:
                    _remove_archive(archive_path)

        results.append(
            _aggregate_level(
                compression_level=(compression_level),
                runs=level_runs,
            )
        )

    return CompressionBenchmarkResult(
        project_id=project.id,
        project_name=project.name,
        runs_per_level=runs_per_level,
        levels=tuple(results),
    )


# =========================================================
# AGGREGATION
# =========================================================


def _aggregate_level(
    *,
    compression_level: int,
    runs: list[BackupBenchmarkResult],
) -> CompressionLevelBenchmark:
    """
    Aggregate one compression level using median values.
    """

    if not runs:
        raise ValueError("Benchmark runs cannot be empty.")

    durations = [item.duration_seconds for item in runs]

    archive_sizes = [item.archive_size_bytes for item in runs]

    ratios = [item.compression_ratio for item in runs]

    read_bytes = [item.read_bytes for item in runs]

    write_bytes = [item.write_bytes for item in runs]

    rss_deltas = [item.rss_delta_bytes for item in runs]

    return CompressionLevelBenchmark(
        compression_level=(compression_level),
        runs=len(runs),
        median_duration_seconds=(statistics.median(durations)),
        min_duration_seconds=min(durations),
        max_duration_seconds=max(durations),
        median_archive_size_bytes=int(statistics.median(archive_sizes)),
        median_compression_ratio=(statistics.median(ratios)),
        median_read_bytes=int(statistics.median(read_bytes)),
        median_write_bytes=int(statistics.median(write_bytes)),
        median_rss_delta_bytes=int(statistics.median(rss_deltas)),
    )


# =========================================================
# CLEANUP
# =========================================================


def _remove_archive(
    archive_path: Path,
) -> None:
    """
    Best-effort cleanup for benchmark artifacts.
    """

    try:
        archive_path.unlink(
            missing_ok=True,
        )

    except OSError:
        pass


# =========================================================
# EXPORTS
# =========================================================


__all__ = [
    "CompressionBenchmarkResult",
    "CompressionLevelBenchmark",
    "DEFAULT_COMPRESSION_LEVELS",
    "DEFAULT_RUNS_PER_LEVEL",
    "benchmark_compression_levels",
]
