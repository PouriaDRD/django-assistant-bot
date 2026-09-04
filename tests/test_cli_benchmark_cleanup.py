from __future__ import annotations

from pathlib import (
    Path,
)

from django_assistant_bot.cli_benchmark import (
    cleanup_benchmark_archive,
)


def test_cleanup_benchmark_archive_removes_existing_file(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "benchmark.zip"

    archive_path.write_bytes(b"benchmark")

    assert archive_path.exists()

    result = cleanup_benchmark_archive(
        archive_path,
    )

    assert result is True

    assert not archive_path.exists()


def test_cleanup_benchmark_archive_accepts_missing_file(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "missing.zip"

    result = cleanup_benchmark_archive(
        archive_path,
    )

    assert result is True


def test_cleanup_benchmark_archive_reports_unlink_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    archive_path = tmp_path / "benchmark.zip"

    archive_path.write_bytes(b"benchmark")

    original_unlink = Path.unlink

    def failing_unlink(
        path: Path,
        *args,
        **kwargs,
    ) -> None:
        if path == archive_path:
            raise PermissionError("simulated cleanup failure")

        original_unlink(
            path,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        Path,
        "unlink",
        failing_unlink,
    )

    result = cleanup_benchmark_archive(
        archive_path,
    )

    assert result is False

    assert archive_path.exists()
