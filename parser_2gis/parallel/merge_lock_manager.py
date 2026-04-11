"""Менеджер блокировок для операций слияния CSV файлов.

ISSUE-025: Выделен из parallel/merger.py для соблюдения SRP.
Отвечает исключительно за получение и освобождение lock файлов.
"""

from __future__ import annotations

import fcntl
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from parser_2gis.constants import MAX_LOCK_FILE_AGE, MERGE_LOCK_TIMEOUT


class MergeLockManager:
    """Управление блокировками при операциях слияния.

    Отвечает за:
    - Проверку и очистку осиротевших lock файлов
    - Атомарное получение блокировки с таймаутом
    - Освобождение и удаление lock файлов
    """

    def __init__(
        self,
        log_callback: Callable[[str, str], None] | None = None,
        timeout: int = MERGE_LOCK_TIMEOUT,
    ) -> None:
        """Инициализирует менеджер блокировок.

        Args:
            log_callback: Функция логирования (message, level).
            timeout: Таймаут ожидания блокировки в секундах.

        """
        self._log_callback = log_callback
        self._timeout = timeout

    def _log(self, message: str, level: str = "debug") -> None:
        """Логирует сообщение."""
        if self._log_callback:
            self._log_callback(message, level)

    def acquire_lock(self, lock_file_path: Path) -> tuple[TextIO | None, bool]:
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
                        self._log(
                            f"Удаление осиротевшего lock файла (возраст: {lock_age:.0f} сек)",
                            "debug",
                        )
                        lock_file_path.unlink()
                    else:
                        self._log(
                            f"Lock файл существует (возраст: {lock_age:.0f} сек), ожидаем...",
                            "warning",
                        )
                except OSError as e:
                    self._log(f"Ошибка проверки lock файла: {e}", "debug")

            start_time = time.time()
            while not lock_acquired:
                try:
                    lock_file_handle = open(lock_file_path, "w", encoding="utf-8")  # noqa: SIM115
                    try:
                        fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        lock_file_handle.write(f"{os.getpid()}\n")
                        lock_file_handle.flush()
                        lock_acquired = True
                        self._log("Lock file получен успешно", "debug")
                    except OSError:
                        try:
                            lock_file_handle.close()
                        except (OSError, RuntimeError, ValueError) as close_error:
                            self._log(f"Ошибка при закрытии lock файла: {close_error}", "error")
                        lock_file_handle = None

                        if time.time() - start_time > self._timeout:
                            self._log(f"Таймаут ожидания lock файла ({self._timeout} сек)", "error")
                            return None, False

                        time.sleep(1)
                except OSError:
                    if lock_file_handle:
                        try:
                            lock_file_handle.close()
                        except (OSError, RuntimeError, ValueError) as close_error:
                            self._log(f"Ошибка при закрытии lock файла: {close_error}", "error")
                        lock_file_handle = None

                    if time.time() - start_time > self._timeout:
                        self._log(f"Таймаут ожидания lock файла ({self._timeout} сек)", "error")
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

    def release_lock(self, lock_file_handle: TextIO | None, lock_file_path: Path) -> None:
        """Освобождает и удаляет lock файл.

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
