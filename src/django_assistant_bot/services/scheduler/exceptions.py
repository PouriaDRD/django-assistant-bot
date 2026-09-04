from __future__ import annotations


class SchedulerServiceError(Exception):
    """
    Base exception for scheduler operations.
    """


class SchedulerNotStartedError(SchedulerServiceError):
    """
    Scheduler operation requires a running scheduler.
    """
