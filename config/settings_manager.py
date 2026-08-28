from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock

from filelock import FileLock, Timeout
from pydantic import ValidationError

from .defaults import create_default_config
from .exceptions import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    ConfigWriteError,
)
from .models import AppConfig


class SettingsManager:
    """
    Thread-safe and process-safe JSON configuration manager.

    Responsibilities:
    - Load configuration from JSON.
    - Validate configuration using Pydantic.
    - Save configuration atomically.
    - Protect concurrent access using a process lock.
    """

    def __init__(
        self,
        config_path: Path,
        lock_timeout: float = 10.0,
    ) -> None:
        self._config_path = config_path.resolve()
        self._lock_path = self._config_path.with_suffix(
            f"{self._config_path.suffix}.lock"
        )

        self._thread_lock = RLock()
        self._file_lock = FileLock(
            str(self._lock_path),
            timeout=lock_timeout,
        )

    @property
    def config_path(self) -> Path:
        return self._config_path

    def initialize(self) -> AppConfig:
        """
        Create the configuration file if it does not exist.

        Returns:
            The current validated configuration.
        """
        with self._thread_lock:
            if not self._config_path.exists():
                config = create_default_config()
                self.save(config)
                return config

            return self.load()

    def load(self) -> AppConfig:
        """
        Load and validate the configuration.

        Raises:
            ConfigFileNotFoundError:
                If the config file does not exist.
            ConfigValidationError:
                If the JSON/configuration is invalid.
        """
        with self._thread_lock:
            if not self._config_path.exists():
                raise ConfigFileNotFoundError(
                    f"Configuration file not found: " f"{self._config_path}"
                )

            try:
                with self._file_lock:
                    raw_data = self._read_json()

                return AppConfig.model_validate(raw_data)

            except json.JSONDecodeError as exc:
                raise ConfigValidationError(
                    "Configuration file contains invalid JSON."
                ) from exc

            except ValidationError as exc:
                raise ConfigValidationError(f"Invalid configuration: {exc}") from exc

    def save(self, config: AppConfig) -> None:
        """
        Validate and atomically save configuration.
        """
        with self._thread_lock:
            try:
                validated_config = AppConfig.model_validate(config.model_dump())

                with self._file_lock:
                    self._atomic_write(validated_config)

            except (OSError, Timeout) as exc:
                raise ConfigWriteError(
                    f"Could not write configuration: " f"{self._config_path}"
                ) from exc

    def update(
        self,
        config: AppConfig,
    ) -> AppConfig:
        """
        Validate and persist configuration.

        Returns:
            The validated configuration.
        """
        self.save(config)
        return config

    def _read_json(self) -> object:
        with self._config_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def _atomic_write(
        self,
        config: AppConfig,
    ) -> None:
        self._config_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        serialized = config.model_dump_json(
            indent=4,
        )

        fd: int | None = None
        temporary_path: Path | None = None

        try:
            fd, temporary_name = tempfile.mkstemp(
                prefix=".config-",
                suffix=".tmp",
                dir=self._config_path.parent,
                text=True,
            )

            temporary_path = Path(temporary_name)

            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
            ) as file:
                fd = None

                file.write(serialized)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            temporary_path.replace(self._config_path)

        finally:
            if fd is not None:
                os.close(fd)

            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)
