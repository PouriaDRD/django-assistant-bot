class BackupError(Exception):
    """Base exception for backup errors."""


class BackupValidationError(BackupError):
    """Invalid backup configuration or path."""


class DatabaseBackupError(BackupError):
    """Database backup failed."""


class MediaBackupError(BackupError):
    """Media collection failed."""


class ArchiveError(BackupError):
    """Archive creation failed."""


class ChecksumError(BackupError):
    """Checksum calculation failed."""


class RetentionError(BackupError):
    """Backup retention cleanup failed."""
