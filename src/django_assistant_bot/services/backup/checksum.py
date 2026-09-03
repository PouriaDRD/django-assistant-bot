from __future__ import annotations

import hashlib
from pathlib import Path

from django_assistant_bot.services.backup.exceptions import ChecksumError
from django_assistant_bot.services.backup.models import ChecksumResult


class ChecksumService:
    """
    Calculates SHA-256 checksums using chunks.
    """

    CHUNK_SIZE = 1024 * 1024

    def calculate(
        self,
        file_path: Path,
    ) -> ChecksumResult:
        if not file_path.exists():
            raise ChecksumError("File does not exist: " f"{file_path}")

        if not file_path.is_file():
            raise ChecksumError("Path is not a file: " f"{file_path}")

        digest = hashlib.sha256()

        try:
            with file_path.open("rb") as file:
                while chunk := file.read(
                    self.CHUNK_SIZE,
                ):
                    digest.update(chunk)

        except OSError as exc:
            raise ChecksumError("Failed to calculate SHA-256: " f"{file_path}") from exc

        return ChecksumResult(
            algorithm="sha256",
            value=digest.hexdigest(),
        )
