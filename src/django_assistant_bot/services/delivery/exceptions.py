from __future__ import annotations


class BackupDeliveryError(Exception):
    """
    Base exception for backup delivery operations.
    """


class BackupDeliveryFileNotFoundError(BackupDeliveryError):
    """
    Backup archive does not exist.
    """


class BackupDeliveryFileTooLargeError(BackupDeliveryError):
    """
    Backup archive exceeds delivery backend limit.
    """


class BackupDeliveryUnavailableError(BackupDeliveryError):
    """
    Delivery backend is temporarily unavailable.
    """
