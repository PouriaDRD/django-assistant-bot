from __future__ import annotations

from django_assistant_bot.cli_compression_benchmark import (
    format_compression_benchmark,
)
from django_assistant_bot.services.resource_monitor import (
    CompressionBenchmarkResult,
    CompressionLevelBenchmark,
)


def test_format_compression_benchmark() -> None:
    result = CompressionBenchmarkResult(
        project_id="project-1",
        project_name="Test",
        runs_per_level=5,
        levels=(
            CompressionLevelBenchmark(
                compression_level=6,
                runs=5,
                median_duration_seconds=0.2,
                min_duration_seconds=0.1,
                max_duration_seconds=0.3,
                median_archive_size_bytes=(1024 * 1024),
                median_compression_ratio=0.5,
                median_read_bytes=(2 * 1024 * 1024),
                median_write_bytes=(1024 * 1024),
                median_rss_delta_bytes=1024,
            ),
        ),
    )

    output = format_compression_benchmark(result)

    assert "Compression Benchmark" in output

    assert "0.200s" in output

    assert "50.00%" in output

    assert "1.00 MB" in output
