"""Общий обработчик сигналов для merge операций.

ISSUE-046: Вынесено из merger.py и file_merger.py для устранения дублирования
логики обработки сигналов (signal handlers) и финализации (cleanup).

Пример использования:
    >>> from parser_2gis.parallel.common.signal_handler_common import MergeSignalHandler
    >>> handler = MergeSignalHandler(log_callback=lambda msg, lvl: print(msg))
    >>> handler.register()
    >>> # ... выполняем merge ...
    >>> handler.restore()
"""

from __future__ import annotations

import signal
import types
from collections.abc import Callable
from pathlib import Path



class MergeSignalHandler:
    """Обработчик сигналов для merge операций.

    Реализует:
    - Регистрацию обработчиков SIGINT и SIGTERM
    - Очистку временных файлов при прерывании
    - Восстановление оригинальных обработчиков

    Args:
        log_callback: Функция для логирования.
        temp_files_ref: Ссылка на список временных файлов для очистки.

    """

    def __init__(
        self,
        log_callback: Callable[[str, str], None] | None = None,
        temp_files_ref: list[Path] | None = None,
    ) -> None:
        """Инициализирует обработчик сигналов.

        Args:
            log_callback: Callback для логирования.
            temp_files_ref: Список временных файлов для очистки.

        """
        self._log_callback = log_callback
        self._temp_files_ref = temp_files_ref or []
        self._old_sigint_handler = None
        self._old_sigterm_handler = None
        self._sigint_registered = False
        self._sigterm_registered = False

    def _log(self, message: str, level: str = "debug") -> None:
        """Логирует сообщение."""
        if self._log_callback:
            self._log_callback(message, level)

    def cleanup_temp_files(self) -> None:
        """Очищает временные файлы при прерывании."""
        for temp_file in self._temp_files_ref:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    self._log(f"Временный файл удалён при прерывании: {temp_file}", "debug")
            except (OSError, RuntimeError, ValueError) as cleanup_error:
                self._log(
                    f"Ошибка при удалении временного файла {temp_file}: {cleanup_error}", "error"
                )

    def _signal_handler(self, signum: int, frame: types.FrameType | None) -> None:
        """Обработчик сигналов прерывания."""
        self._log(f"Получен сигнал {signum}, очистка временных файлов...", "warning")
        self.cleanup_temp_files()
        # Вызываем оригинальный обработчик если он есть
        if self._old_sigint_handler and callable(self._old_sigint_handler):
            self._old_sigint_handler(signum, frame)

    def register(self) -> None:
        """Регистрирует обработчики сигналов."""
        self._old_sigint_handler = signal.getsignal(signal.SIGINT)
        self._old_sigterm_handler = signal.getsignal(signal.SIGTERM)

        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            self._sigint_registered = True
            signal.signal(signal.SIGTERM, self._signal_handler)
            self._sigterm_registered = True
        except (OSError, ValueError) as sig_error:
            self._log(f"Не удалось зарегистрировать обработчики сигналов: {sig_error}", "warning")

    def restore(self) -> None:
        """Восстанавливает оригинальные обработчики сигналов."""
        if self._sigint_registered:
            try:
                signal.signal(signal.SIGINT, self._old_sigint_handler)
            except (OSError, ValueError, TypeError) as restore_error:
                self._log(f"Ошибка при восстановлении SIGINT обработчика: {restore_error}", "error")

        if self._sigterm_registered:
            try:
                signal.signal(signal.SIGTERM, self._old_sigterm_handler)
            except (OSError, ValueError, TypeError) as restore_error:
                self._log(
                    f"Ошибка при восстановлении SIGTERM обработчика: {restore_error}", "error"
                )

    def __enter__(self) -> MergeSignalHandler:
        """Контекстный менеджер: регистрирует обработчики."""
        self.register()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Контекстный менеджер: восстанавливает обработчики."""
        self.restore()
