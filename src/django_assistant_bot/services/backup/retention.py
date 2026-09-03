from __future__ import annotations

from pathlib import Path


class RetentionService:
    """
    Keeps only the newest configured number
    of project backups.
    """

    def cleanup(
        self,
        project_directory: Path,
        keep_last: int,
    ) -> list[Path]:
        if keep_last < 1:
            return []

        if not project_directory.exists():
            return []

        archives = sorted(
            (
                path
                for path in project_directory.glob(
                    "*.zip",
                )
                if path.is_file()
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        removed: list[Path] = []

        for archive_path in archives[keep_last:]:
            try:
                archive_path.unlink()
                removed.append(archive_path)
            except OSError:
                continue

        return removed
