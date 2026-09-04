from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import (
    Path,
)
from unittest.mock import (
    Mock,
    patch,
)

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    ChecksumResult,
)
from django_assistant_bot.services.resource_monitor import (
    BackupBenchmarkResult,
    benchmark_compression_levels,
)


def build_backup_result(
    archive_path: Path,
) -> BackupResult:
    now = datetime.now(timezone.utc)

    return BackupResult(
        project_id="project-1",
        project_name="Test",
        status=BackupStatus.SUCCESS,
        archive_path=archive_path,
        started_at=now,
        finished_at=now,
        database_size_bytes=1000,
        media_size_bytes=3000,
        archive_size_bytes=2000,
        media_file_count=10,
        checksum=ChecksumResult(
            algorithm="sha256",
            value="abc",
        ),
    )


def build_benchmark(
    duration: float,
) -> BackupBenchmarkResult:
    return BackupBenchmarkResult(
        duration_seconds=duration,
        rss_before_bytes=100,
        rss_after_bytes=120,
        rss_delta_bytes=20,
        thread_delta=0,
        read_bytes=1000,
        write_bytes=2000,
        database_size_bytes=1000,
        media_size_bytes=3000,
        archive_size_bytes=2000,
        media_file_count=10,
        compression_ratio=0.5,
    )


def test_compression_benchmark_aggregates_runs(
    tmp_path: Path,
) -> None:
    project = Mock()

    project.id = "project-1"
    project.name = "Test"

    durations = [
        0.3,
        0.1,
        0.2,
    ]

    benchmark_results = []

    for index, duration in enumerate(durations):
        archive = tmp_path / f"backup-{index}.zip"

        archive.write_bytes(b"test")

        benchmark_results.append(
            (
                build_backup_result(archive),
                build_benchmark(duration),
            )
        )

    with patch(
        (
            "django_assistant_bot.services."
            "resource_monitor.compression_benchmark."
            "benchmark_backup"
        ),
        side_effect=benchmark_results,
    ):
        result = benchmark_compression_levels(
            project=project,
            backup_directory=tmp_path,
            compression_levels=(6,),
            runs_per_level=3,
        )

    assert result.runs_per_level == 3

    assert len(result.levels) == 1

    level = result.levels[0]

    assert level.compression_level == 6

    assert level.median_duration_seconds == 0.2

    assert level.min_duration_seconds == 0.1

    assert level.max_duration_seconds == 0.3

    for index in range(3):
        assert not (tmp_path / f"backup-{index}.zip").exists()
