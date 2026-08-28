from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BackupResult:
    project_id: str
    archive_path: Path
    started_at: datetime
    finished_at: datetime
    size_bytes: int
