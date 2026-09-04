from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from unittest.mock import (
    Mock,
)

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    ChecksumResult,
)
from django_assistant_bot.services.resource_monitor import (
    ProcessResourceMonitor,
    ProcessResourceSnapshot,
    benchmark_backup,
)


def build_backup_result() -> BackupResult:
    now = datetime.now(
        timezone.utc,
    )

    return BackupResult(
        project_id="project-1",
        project_name="Test Project",
        status=BackupStatus.SUCCESS,
        archive_path=Path("backup.zip"),
        started_at=now,
        finished_at=now,
        database_size_bytes=1000,
        media_size_bytes=3000,
        archive_size_bytes=2000,
        media_file_count=10,
        checksum=ChecksumResult(
            algorithm="sha256",
            value="abc123",
        ),
    )


def test_benchmark_measures_backup_resources() -> None:
    monitor = Mock(
        spec=ProcessResourceMonitor,
    )

    before = ProcessResourceSnapshot(
        rss_bytes=1000,
        vms_bytes=2000,
        cpu_percent=0,
        thread_count=5,
        open_file_count=2,
        read_bytes=100,
        write_bytes=200,
    )

    after = ProcessResourceSnapshot(
        rss_bytes=1500,
        vms_bytes=2500,
        cpu_percent=0,
        thread_count=6,
        open_file_count=2,
        read_bytes=1100,
        write_bytes=2200,
    )

    monitor.snapshot.side_effect = [
        before,
        after,
    ]

    monitor.delta.return_value = ProcessResourceMonitor.delta(
        before=before,
        after=after,
    )

    backup_result = build_backup_result()

    run_backup = Mock(
        return_value=backup_result,
    )

    result, benchmark = benchmark_backup(
        run_backup=run_backup,
        monitor=monitor,
    )

    assert result is backup_result

    assert benchmark.rss_before_bytes == 1000

    assert benchmark.rss_after_bytes == 1500

    assert benchmark.rss_delta_bytes == 500

    assert benchmark.thread_delta == 1

    assert benchmark.read_bytes == 1000

    assert benchmark.write_bytes == 2000

    assert benchmark.database_size_bytes == 1000

    assert benchmark.media_size_bytes == 3000

    assert benchmark.archive_size_bytes == 2000

    assert benchmark.media_file_count == 10

    assert benchmark.compression_ratio == 0.5


def test_benchmark_handles_zero_source_size() -> None:
    result = build_backup_result()

    result = result.__class__(
        project_id=result.project_id,
        project_name=result.project_name,
        status=result.status,
        archive_path=result.archive_path,
        started_at=result.started_at,
        finished_at=result.finished_at,
        database_size_bytes=0,
        media_size_bytes=0,
        archive_size_bytes=0,
        media_file_count=0,
        checksum=result.checksum,
    )

    monitor = Mock(
        spec=ProcessResourceMonitor,
    )

    snapshot = ProcessResourceSnapshot(
        rss_bytes=0,
        vms_bytes=0,
        cpu_percent=0,
        thread_count=0,
        open_file_count=0,
        read_bytes=0,
        write_bytes=0,
    )

    monitor.snapshot.side_effect = [
        snapshot,
        snapshot,
    ]

    monitor.delta.return_value = ProcessResourceMonitor.delta(
        before=snapshot,
        after=snapshot,
    )

    _, benchmark = benchmark_backup(
        run_backup=lambda: result,
        monitor=monitor,
    )

    assert benchmark.compression_ratio == 0.0
