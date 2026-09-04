from __future__ import annotations

from types import (
    SimpleNamespace,
)
from unittest.mock import (
    Mock,
)

import psutil

from django_assistant_bot.services.resource_monitor import (
    ProcessResourceMonitor,
    ProcessResourceSnapshot,
)


def build_process() -> Mock:
    process = Mock(
        spec=psutil.Process,
    )

    process.memory_info.return_value = SimpleNamespace(
        rss=1000,
        vms=2000,
    )

    process.cpu_percent.return_value = 12.5

    process.num_threads.return_value = 4

    process.open_files.return_value = [
        object(),
        object(),
    ]

    process.io_counters.return_value = SimpleNamespace(
        read_bytes=3000,
        write_bytes=4000,
    )

    return process


def test_snapshot_reads_process_resources() -> None:
    process = build_process()

    monitor = ProcessResourceMonitor(
        process=process,
    )

    snapshot = monitor.snapshot()

    assert snapshot.rss_bytes == 1000

    assert snapshot.vms_bytes == 2000

    assert snapshot.cpu_percent == 12.5

    assert snapshot.thread_count == 4

    assert snapshot.open_file_count == 2

    assert snapshot.read_bytes == 3000

    assert snapshot.write_bytes == 4000


def test_delta_calculates_resource_changes() -> None:
    before = ProcessResourceSnapshot(
        rss_bytes=100,
        vms_bytes=200,
        cpu_percent=1.0,
        thread_count=2,
        open_file_count=1,
        read_bytes=1000,
        write_bytes=2000,
    )

    after = ProcessResourceSnapshot(
        rss_bytes=150,
        vms_bytes=250,
        cpu_percent=2.0,
        thread_count=3,
        open_file_count=2,
        read_bytes=1300,
        write_bytes=2600,
    )

    delta = ProcessResourceMonitor.delta(
        before=before,
        after=after,
    )

    assert delta.rss_bytes == 50

    assert delta.vms_bytes == 50

    assert delta.thread_count == 1

    assert delta.open_file_count == 1

    assert delta.read_bytes == 300

    assert delta.write_bytes == 600


def test_negative_io_delta_is_clamped_to_zero() -> None:
    before = ProcessResourceSnapshot(
        rss_bytes=0,
        vms_bytes=0,
        cpu_percent=0,
        thread_count=0,
        open_file_count=0,
        read_bytes=500,
        write_bytes=500,
    )

    after = ProcessResourceSnapshot(
        rss_bytes=0,
        vms_bytes=0,
        cpu_percent=0,
        thread_count=0,
        open_file_count=0,
        read_bytes=100,
        write_bytes=100,
    )

    delta = ProcessResourceMonitor.delta(
        before=before,
        after=after,
    )

    assert delta.read_bytes == 0

    assert delta.write_bytes == 0


def test_open_file_access_denied_returns_zero() -> None:
    process = build_process()

    process.open_files.side_effect = psutil.AccessDenied()

    monitor = ProcessResourceMonitor(
        process=process,
    )

    snapshot = monitor.snapshot()

    assert snapshot.open_file_count == 0


def test_io_access_denied_returns_zero() -> None:
    process = build_process()

    process.io_counters.side_effect = psutil.AccessDenied()

    monitor = ProcessResourceMonitor(
        process=process,
    )

    snapshot = monitor.snapshot()

    assert snapshot.read_bytes == 0

    assert snapshot.write_bytes == 0
