from __future__ import annotations


class BackupHistoryServiceError(Exception):
    """
    Base exception for backup history operations.
    """


class BackupHistoryNotFoundError(BackupHistoryServiceError):
    """
    Requested backup history record was not found.
    """


class BackupHistoryValidationError(BackupHistoryServiceError):
    """
    Invalid backup history query parameters.
    """


class BackupHistoryPersistenceError(BackupHistoryServiceError):
    """
    Backup history persistence operation failed.
    """
