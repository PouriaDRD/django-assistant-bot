class BackupError(Exception):
    """
    Base exception for all backup-related errors.
    """


class BackupValidationError(BackupError):
    """
    Invalid backup configuration or path.
    """


class ProjectBackupDisabledError(BackupValidationError):
    """
    Backup was requested for a disabled project.
    """


class DatabaseBackupError(BackupError):
    """
    Database backup operation failed.
    """


class MediaBackupError(BackupError):
    """
    Media collection failed.
    """


class ArchiveError(BackupError):
    """
    Archive creation failed.
    """


class ChecksumError(BackupError):
    """
    Checksum calculation failed.
    """


class RetentionError(BackupError):
    """
    Backup retention cleanup failed.
    """


class BackupCoordinatorError(BackupError):
    """
    Base exception for backup orchestration errors.
    """


class BackupDisabledError(BackupCoordinatorError):
    """
    Global backup functionality is disabled.
    """


class BackupAlreadyRunningError(BackupCoordinatorError):
    """
    A backup is already running for the requested project.
    """


class BackupExecutionError(BackupCoordinatorError):
    """
    Backup execution failed after orchestration started.
    """


class BackupHistoryError(BackupCoordinatorError):
    """
    Backup completed but its history record could not
    be persisted.
    """
