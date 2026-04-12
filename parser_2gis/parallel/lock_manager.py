"""Менеджер блокировок для параллельного парсинга.

ISSUE-024: Выделен из parallel/parallel_parser.py для соблюдения SRP.
Отвечает исключительно за управление lock файлами при merge операциях.
"""

from __future__ import annotations

import fcntl
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from parser_2gis.constants import MAX_LOCK_FILE_AGE, MERGE_LOCK_TIMEOUT


class ParallelLockManager:
    """Управление блокировками при параллельном парсинге.

    Отвечает за:
    - Проверку и очистку осиротевших lock файлов
    - Атомарное создание lock файлов
    - Освобождение и удаление lock файлов
    """

    MAX_LOCK_ATTEMPTS = 50

    def __init__(self, log_callback: Callable[..., Any] | None = None) -> None:
        """Инициализирует менеджер блокировок.

        Args:
            log_callback: Функция логирования.

        """
        self._log_callback = log_callback

    def _log(self, message: str, level: str = "debug") -> None:
        """Логирует сообщение."""
        if self._log_callback:
            self._log_callback(message, level)

    def acquire_merge_lock(self, lock_file_path: Path) -> tuple[TextIO | None, bool]:
        """Получает блокировку merge операции.

        Args:
            lock_file_path: Путь к lock файлу.

        Returns:
            Кортеж (lock_file_handle, lock_acquired).

        """
        lock_file_handle: TextIO | None = None
        lock_acquired = False

        try:
            # Проверка и очистка осиротевших lock файлов
            if lock_file_path.exists():
                try:
                    lock_age = time.time() - lock_file_path.stat().st_mtime
                    if lock_age > MAX_LOCK_FILE_AGE:
                        try:
                            with open(lock_file_path, encoding="utf-8") as f:
                                lock_pid = int(f.read().strip())
                            os.kill(lock_pid, 0)
                            self._log(
                                f"Lock файл существует "
                                f"(возраст: {lock_age:.0f} сек, PID: {lock_pid}), "
                                f"ожидаем..."
                            )
                        except (ProcessLookupError, ValueError, OSError):
                            self._log(
                                "Удаление осиротевшего lock файла "
                                f"(возраст: {lock_age:.0f} сек, PID: {lock_pid})"
                            )
                            lock_file_path.unlink()
                    else:
                        self._log(
                            f"Lock файл существует (возраст: {lock_age:.0f} сек), ожидаем...",
                            level="warning",
                        )
                except OSError as e:
                    self._log(f"Ошибка проверки lock файла: {e}", "debug")

            # Атомарное создание lock файла
            start_time = time.time()
            lock_attempts = 0
            while not lock_acquired:
                lock_attempts += 1
                if lock_attempts > self.MAX_LOCK_ATTEMPTS:
                    self._log(
                        "Превышено максимальное число попыток "
                        f"получения lock ({self.MAX_LOCK_ATTEMPTS})",
                        "error",
                    )
                    msg = f"Не удалось получить lock файл после {self.MAX_LOCK_ATTEMPTS} попыток"
                    raise RuntimeError(
                        msg
                    )
                lock_fd = None
                try:
                    lock_fd = os.open(
                        str(lock_file_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o600
                    )
                    try:
                        lock_file_handle = os.fdopen(lock_fd, "w", encoding="utf-8")
                        lock_fd = None

                        fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        lock_file_handle.write(f"{os.getpid()}\n")
                        lock_file_handle.flush()
                        lock_acquired = True
                        self._log("Lock file получен успешно", "debug")
                    finally:
                        if lock_fd is not None:
                            try:
                                os.close(lock_fd)
                            except OSError as close_error:
                                self._log(
                                    "Ошибка при закрытии fd lock файла "
                                    f"(игнорируется): {close_error}",
                                    "debug",
                                )
                except (OSError, FileExistsError):
                    if lock_file_handle is not None:
                        try:
                            lock_file_handle.close()
                        except (OSError, RuntimeError, ValueError) as close_error:
                            self._log(f"Ошибка при закрытии lock файла: {close_error}", "error")
                    lock_file_handle = None
                    lock_fd = None

                    if time.time() - start_time > MERGE_LOCK_TIMEOUT:
                        self._log(
                            f"Таймаут ожидания lock файла ({MERGE_LOCK_TIMEOUT} сек)", "error"
                        )
                        return None, False

                    time.sleep(1)

        except (OSError, RuntimeError, ValueError) as lock_error:
            self._log(f"Ошибка при получении lock файла: {lock_error}", "error")
            if lock_file_handle:
                try:
                    lock_file_handle.close()
                except (OSError, RuntimeError, ValueError) as close_error:
                    self._log(f"Ошибка при закрытии lock файла: {close_error}", "error")
            return None, False

        return lock_file_handle, lock_acquired

    def cleanup_merge_lock(self, lock_file_handle: TextIO | None, lock_file_path: Path) -> None:
        """Очищает и удаляет lock файл.

        Args:
            lock_file_handle: Дескриптор lock файла.
            lock_file_path: Путь к lock файлу.

        """
        try:
            if lock_file_handle:
                fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
                lock_file_handle.close()
                lock_file_path.unlink()
                self._log("Lock файл удалён", "debug")
        except (OSError, RuntimeError, ValueError) as lock_error:
            self._log(f"Ошибка при удалении lock файла: {lock_error}", "debug")
