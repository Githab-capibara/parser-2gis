"""Абстракция стратегии файловой блокировки.

ISSUE 076: Создаёт FileLockStrategy абстракцию для управления файловыми
блокировками с разными реализациями.

Пример использования:
    >>> from pathlib import Path
    >>> from parser_2gis.utils.file_lock_abstraction import FcntlLockStrategy
    >>> with FcntlLockStrategy(Path("/tmp/lock.lock")) as acquired:
    ...     if acquired:
    ...         # Выполняем защищённую операцию
    ...         pass
"""

from __future__ import annotations

import fcntl
import os
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, TextIO

from parser_2gis.constants import MAX_LOCK_FILE_AGE, MERGE_LOCK_TIMEOUT


class BaseLockStrategy:
    """Базовый класс для стратегий файловой блокировки.

    Определяет общий интерфейс и базовую логику.
    """

    def __init__(
        self, lock_path: Path, timeout: int = MERGE_LOCK_TIMEOUT, max_attempts: int = 50
    ) -> None:
        """Инициализирует базовую стратегию блокировки.

        Args:
            lock_path: Путь к файлу блокировки.
            timeout: Таймаут ожидания в секундах.
            max_attempts: Максимальное количество попыток.

        """
        self._lock_path = lock_path
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._acquired = False

    @property
    def is_acquired(self) -> bool:
        """Проверяет, получена ли блокировка."""
        return self._acquired

    def _check_orphaned_lock(self) -> bool:
        """Проверяет и удаляет осиротевшую блокировку.

        Returns:
            True если осиротевшая блокировка была удалена.

        """
        if not self._lock_path.exists():
            return False

        try:
            lock_age = time.time() - self._lock_path.stat().st_mtime
            if lock_age > MAX_LOCK_FILE_AGE:
                try:
                    with open(self._lock_path, encoding="utf-8") as f:
                        lock_pid = int(f.read().strip())
                    os.kill(lock_pid, 0)
                    # Процесс всё ещё жив — блокировка активна
                    return False
                except (ProcessLookupError, ValueError, OSError):
                    # Процесс мёртв — удаляем осиротевшую блокировку
                    self._lock_path.unlink()
                    return True
        except OSError:
            pass
        return False

    def acquire(self) -> bool:
        """Получает блокировку. Переопределяется в подклассах."""
        raise NotImplementedError

    def release(self) -> None:
        """Освобождает блокировку. Переопределяется в подклассах."""
        raise NotImplementedError

    def __enter__(self) -> bool:
        """Контекстный менеджер: получает блокировку."""
        return self.acquire()

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Контекстный менеджер: освобождает блокировку."""
        if self._acquired:
            self.release()


class FcntlLockStrategy(BaseLockStrategy):
    """Стратегия файловой блокировки на основе fcntl.

    ISSUE 076: Реализует FileLockStrategy с использованием fcntl.flock().
    Подходит для Unix-систем.
    """

    def __init__(
        self, lock_path: Path, timeout: int = MERGE_LOCK_TIMEOUT, max_attempts: int = 50
    ) -> None:
        """Инициализирует стратегию блокировки.

        Args:
            lock_path: Путь к файлу блокировки.
            timeout: Таймаут ожидания в секундах.
            max_attempts: Максимальное количество попыток.

        """
        super().__init__(lock_path, timeout, max_attempts)
        self._lock_handle: TextIO | None = None

    def acquire(self) -> bool:
        """Получает блокировку через fcntl.

        Returns:
            True если блокировка получена, False если таймаут.

        Raises:
            RuntimeError: При превышении количества попыток.

        """
        # Проверяем и очищаем осиротевшие блокировки
        self._check_orphaned_lock()

        start_time = time.time()
        attempt = 0

        while attempt < self._max_attempts:
            attempt += 1

            if time.time() - start_time > self._timeout:
                return False

            try:
                lock_fd = os.open(
                    str(self._lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o600
                )
                try:
                    self._lock_handle = os.fdopen(lock_fd, "w", encoding="utf-8")
                    lock_fd = None

                    fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self._lock_handle.write(f"{os.getpid()}\n")
                    self._lock_handle.flush()
                    self._acquired = True
                    return True
                finally:
                    if lock_fd is not None:
                        with suppress(OSError):
                            os.close(lock_fd)

            except (OSError, FileExistsError):
                if self._lock_handle is not None:
                    with suppress(OSError):
                        self._lock_handle.close()
                    self._lock_handle = None

                if time.time() - start_time > self._timeout:
                    return False

                time.sleep(1)

        raise RuntimeError(f"Не удалось получить lock файл после {self._max_attempts} попыток")

    def release(self) -> None:
        """Освобождает блокировку и удаляет файл."""
        try:
            if self._lock_handle is not None:
                fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
                self._lock_handle.close()
                if self._lock_path.exists():
                    self._lock_path.unlink()
        except OSError:
            pass
        finally:
            self._lock_handle = None
            self._acquired = False


class NoOpLockStrategy(BaseLockStrategy):
    """Стратегия блокировки без реальных блокировок (для тестирования).

    Всегда возвращает True при acquire.
    """

    def acquire(self) -> bool:
        """Всегда получает блокировку."""
        self._acquired = True
        return True

    def release(self) -> None:
        """Освобождает блокировку (no-op)."""
        self._acquired = False


__all__ = ["BaseLockStrategy", "FcntlLockStrategy", "NoOpLockStrategy"]
