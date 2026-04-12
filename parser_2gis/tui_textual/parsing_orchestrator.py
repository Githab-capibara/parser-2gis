"""Оркестратор парсинга для TUI приложения.

ISSUE-026: Выделен из tui_textual/app.py для соблюдения SRP.
Отвечает за управление состоянием парсинга и координацию процессов.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ParsingState:
    """Состояние процесса парсинга.

    Attributes:
        running: Флаг активного парсинга.
        started_at: Время начала парсинга.
        total_urls: Общее количество URL.
        success_count: Количество успешных операций.
        error_count: Количество ошибок.
        current_category: Текущая категория.
        current_record: Текущая запись.

    """

    running: bool = False
    started_at: datetime | None = None
    total_urls: int = 0
    success_count: int = 0
    error_count: int = 0
    current_category: str = ""
    current_record: int = 0

    def reset(self) -> None:
        """Сбрасывает состояние парсинга."""
        self.running = False
        self.started_at = None
        self.total_urls = 0
        self.success_count = 0
        self.error_count = 0
        self.current_category = ""
        self.current_record = 0


class ParsingOrchestrator:
    """Оркестратор процесса парсинга.

    Отвечает за:
    - Управление состоянием парсинга (запуск, остановка, прогресс)
    - Сохранение и восстановление конфигурации
    - Координацию callback'ов прогресса
    - Обработку завершения и ошибок

    ISSUE-026: Выделен из TUIApp для соблюдения SRP.
    """

    def __init__(self) -> None:
        """Инициализирует оркестратор парсинга."""
        self._state = ParsingState()
        self._saved_config: dict[str, Any] | None = None
        self._progress_callback: Callable[[int, int, str], None] | None = None

    @property
    def state(self) -> ParsingState:
        """Возвращает текущее состояние парсинга."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Проверяет, запущено ли парсинг."""
        return self._state.running

    @property
    def saved_config(self) -> dict[str, Any] | None:
        """Возвращает сохранённую конфигурацию."""
        return self._saved_config

    def start(self, total_urls: int, saved_config: dict[str, Any] | None = None) -> None:
        """Запускает процесс парсинга.

        Args:
            total_urls: Общее количество URL для парсинга.
            saved_config: Сохранённая конфигурация для восстановления.

        """
        self._state.running = True
        self._state.started_at = datetime.now(timezone.utc)
        self._state.total_urls = total_urls
        self._state.success_count = 0
        self._state.error_count = 0
        self._saved_config = saved_config

    def stop(self) -> None:
        """Останавливает парсинг."""
        self._state.running = False

    def update_progress(
        self, success: int, failed: int, category: str = "", record: int = 0
    ) -> None:
        """Обновляет прогресс парсинга.

        Args:
            success: Количество успешных операций.
            failed: Количество ошибок.
            category: Текущая категория.
            record: Текущая запись.

        """
        if not self._state.running:
            return
        self._state.success_count = success
        self._state.error_count = failed
        if category:
            self._state.current_category = category
        if record:
            self._state.current_record = record

    def is_cancelled(self) -> bool:
        """Проверяет, отменён ли парсинг."""
        return not self._state.running

    def complete(self) -> bool:
        """Завершает парсинг и возвращает флаг успеха.

        Returns:
            True если парсинг был запущен.

        """
        was_running = self._state.running
        self._state.running = False
        return was_running

    def set_progress_callback(self, callback: Callable[[int, int, str], None] | None) -> None:
        """Устанавливает callback обновления прогресса.

        Args:
            callback: Функция обратного вызова.

        """
        self._progress_callback = callback

    def notify_progress(self, success: int, failed: int, filename: str) -> None:
        """Вызывает callback прогресса если установлен.

        Args:
            success: Количество успешных операций.
            failed: Количество ошибок.
            filename: Имя файла.

        """
        if self._progress_callback and self._state.running:
            self._progress_callback(success, failed, filename)
