"""Общий менеджер файловых блокировок для параллельного парсинга.

ISSUE-044: Вынесен из parallel_parser.py и merger.py для устранения дублирования
логики получения блокировок (lock acquisition logic).

Пример использования:
    >>> from pathlib import Path
    >>> from parser_2gis.parallel.common.file_lock import FileLockManager
    >>> with FileLockManager(Path("/tmp/.merge.lock"), timeout=7200) as (lock_file, acquired):
    ...     if acquired:
    ...         # Выполняем merge операцию
    ...         pass
"""

from __future__ import annotations

import fcntl
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from collections.abc import Callable

from parser_2gis.constants import MAX_LOCK_FILE_AGE, MERGE_LOCK_TIMEOUT


class FileLockManager:
    """Менеджер файловых блокировок для merge операций.

    Реализует:
    - Проверку возраста lock файла
    - Очистку осиротевших блокировок
    - Атомарное создание lock через O_CREAT | O_EXCL
    - Таймаут ожидания блокировки

    Args:
        lock_file_path: Путь к lock файлу.
        timeout: Таймаут ожидания блокировки в секундах.
        max_lock_attempts: Максимальное количество попыток получения блокировки.
        log_callback: Функция для логирования (принимает message, level).

    """

    def __init__(
        self,
        lock_file_path: Path,
        timeout: int = MERGE_LOCK_TIMEOUT,
        max_lock_attempts: int = 50,
        log_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        """Инициализирует менеджер блокировок.

        Args:
            lock_file_path: Путь к lock файлу.
            timeout: Таймаут ожидания в секундах.
            max_lock_attempts: Максимальное количество попыток.
            log_callback: Callback для логирования.

        """
        self._lock_file_path = lock_file_path
        self._timeout = timeout
        self._max_lock_attempts = max_lock_attempts
        self._log_callback = log_callback
        self._lock_handle: TextIO | None = None
        self._lock_acquired = False

    def _log(self, message: str, level: str = "debug") -> None:
        """Логирует сообщение через callback."""
        if self._log_callback:
            self._log_callback(message, level)

    def acquire(self) -> tuple[TextIO | None, bool]:
        """Получает блокировку merge операции.

        Returns:
            Кортеж (lock_file_handle, lock_acquired).

        Raises:
            RuntimeError: Если превышено количество попыток получения блокировки.

        """
        self._lock_handle = None
        self._lock_acquired = False

        try:
            # Проверка и очистка осиротевших lock файлов
            if self._lock_file_path.exists():
                try:
                    lock_age = time.time() - self._lock_file_path.stat().st_mtime
                    if lock_age > MAX_LOCK_FILE_AGE:
                        try:
                            with open(self._lock_file_path, encoding="utf-8") as f:
                                lock_pid = int(f.read().strip())
                            os.kill(lock_pid, 0)
                            self._log(
                                f"Lock файл существует "
                                f"(возраст: {lock_age:.0f} сек, PID: {lock_pid}), "
                                f"ожидаем..."
                            )
                        except (ProcessLookupError, ValueError, OSError):
                            self._log(
                                f"Удаление осиротевшего lock файла (возраст: {lock_age:.0f} сек)"
                            )
                            self._lock_file_path.unlink()
                    else:
                        self._log(
                            f"Lock файл существует (возраст: {lock_age:.0f} сек), ожидаем...",
                            "warning",
                        )
                except OSError as e:
                    self._log(f"Ошибка проверки lock файла: {e}", "debug")

            # Атомарное создание lock файла
            start_time = time.time()
            lock_attempts = 0
            while not self._lock_acquired:
                lock_attempts += 1
                if lock_attempts > self._max_lock_attempts:
                    self._log(
                        "Превышено максимальное число попыток "
                        f"получения lock ({self._max_lock_attempts})",
                        "error",
                    )
                    msg = f"Не удалось получить lock файл после {self._max_lock_attempts} попыток"
                    raise RuntimeError(msg)

                lock_fd = None
                try:
                    lock_fd = os.open(
                        str(self._lock_file_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o600
                    )
                    try:
                        self._lock_handle = os.fdopen(lock_fd, "w", encoding="utf-8")
                        lock_fd = None

                        fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        self._lock_handle.write(f"{os.getpid()}\n")
                        self._lock_handle.flush()
                        self._lock_acquired = True
                        self._log("Lock file получен успешно", "debug")
                    finally:
                        if lock_fd is not None:
                            try:
                                os.close(lock_fd)
                            except OSError as close_error:
                                self._log(
                                    f"Ошибка при закрытии fd lock файла: {close_error}", "debug"
                                )

                except (OSError, FileExistsError):
                    if self._lock_handle is not None:
                        try:
                            self._lock_handle.close()
                        except OSError as close_error:
                            self._log(f"Ошибка при закрытии lock файла: {close_error}", "error")
                    self._lock_handle = None
                    lock_fd = None

                    if time.time() - start_time > self._timeout:
                        self._log(f"Таймаут ожидания lock файла ({self._timeout} сек)", "error")
                        return None, False

                    time.sleep(1)

        except (OSError, RuntimeError, ValueError) as lock_error:
            self._log(f"Ошибка при получении lock файла: {lock_error}", "error")
            if self._lock_handle:
                try:
                    self._lock_handle.close()
                except OSError as close_error:
                    self._log(f"Ошибка при закрытии lock файла: {close_error}", "error")
            return None, False

        return self._lock_handle, self._lock_acquired

    def release(self) -> None:
        """Освобождает и удаляет lock файл."""
        try:
            if self._lock_handle:
                fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
                self._lock_handle.close()
                if self._lock_file_path.exists():
                    self._lock_file_path.unlink()
                self._log("Lock файл удалён", "debug")
        except (OSError, RuntimeError, ValueError) as lock_error:
            self._log(f"Ошибка при удалении lock файла: {lock_error}", "debug")
        finally:
            self._lock_handle = None
            self._lock_acquired = False

    @property
    def is_acquired(self) -> bool:
        """Проверяет, получена ли блокировка."""
        return self._lock_acquired

    def __enter__(self) -> tuple[TextIO | None, bool]:
        """Контекстный менеджер: получает блокировку."""
        return self.acquire()

    def __exit__(self, _exc_type: object, _exc_val: object, _exc_tb: object) -> None:
        """Контекстный менеджер: освобождает блокировку."""
        self.release()
