"""
Просмотр логов для TUI Parser2GIS.
"""

from collections import deque
from datetime import datetime
from typing import Literal

import pytermgui as ptg

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogViewer:
    """
    Виджет для просмотра логов.

    Отображает логи в реальном времени с прокруткой.
    """

    def __init__(self, max_lines: int = 100) -> None:
        """
        Инициализация просмотрщика логов.

        Args:
            max_lines: Максимальное количество хранимых строк
        """
        self._max_lines = max_lines
        self._logs: deque[str] = deque(maxlen=max_lines)

    def add_log(self, message: str, level: LogLevel = "INFO") -> None:
        """
        Добавить лог.

        Args:
            message: Сообщение лога
            level: Уровень лога
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_colors = {
            "DEBUG": "[dim]",
            "INFO": "[cyan]",
            "WARNING": "[yellow]",
            "ERROR": "[red]",
            "CRITICAL": "[red bold]",
        }

        color = level_colors.get(level, "[white]")
        log_line = f"{color}[{timestamp}] {level}: {message}[/]"

        self._logs.append(log_line)

    def _render_text(self) -> str:
        """
        Получить текстовое представление логов.

        Returns:
            Строка с логами
        """
        if not self._logs:
            return "[dim]Нет логов...[/dim]"

        return "\n".join(self._logs)

    def render(self) -> ptg.Container:
        """
        Рендерить лог-вьювер.

        Returns:
            Container с логами
        """
        if not self._logs:
            return ptg.Container(
                ptg.Label("[dim]Нет логов...[/dim]"),
                height=10,
            )

        # Создать контейнер с логами
        log_labels = [ptg.Label(log) for log in self._logs]

        return ptg.Container(
            *log_labels,
            height=10,
        )

    def clear(self) -> None:
        """Очистить логи."""
        self._logs.clear()

    def get_logs(self) -> list[str]:
        """
        Получить все логи.

        Returns:
            Список строк логов
        """
        return list(self._logs)

    @property
    def line_count(self) -> int:
        """Количество строк логов."""
        return len(self._logs)
