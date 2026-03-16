"""
Современный просмотр логов для TUI Parser2GIS.

Использует Unicode иконки, цветовое кодирование и разделители
для красивого и удобного отображения логов.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Literal

import pytermgui as ptg

from ..utils import UnicodeIcons, truncate_text

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "SUCCESS"]


class LogViewer:
    """
    Современный виджет для просмотра логов.

    Особенности:
    - Unicode иконки для каждого уровня логов
    - Цветовое кодирование с градиентами
    - Разделители между важными сообщениями
    - Временные метки с цветом
    - Поддержка длинных сообщений с обрезкой
    - Автоскролл к новым сообщениям
    """

    # Конфигурация стилей для уровней логов
    LOG_STYLES = {
        "DEBUG": {
            "icon": UnicodeIcons.EMOJI_DEBUG,
            "color": "#666666",
            "bg_color": "#1A1A1A",
            "time_color": "#4A4A4A",
            "prefix": "[[DBG]]",
        },
        "INFO": {
            "icon": UnicodeIcons.EMOJI_INFO,
            "color": "#00BFFF",
            "bg_color": "#0D1A26",
            "time_color": "#00688B",
            "prefix": "[[INF]]",
        },
        "SUCCESS": {
            "icon": UnicodeIcons.EMOJI_SUCCESS,
            "color": "#00FF88",
            "bg_color": "#0D261A",
            "time_color": "#006400",
            "prefix": "[[OK]]",
        },
        "WARNING": {
            "icon": UnicodeIcons.EMOJI_WARNING,
            "color": "#FFAA00",
            "bg_color": "#261F0D",
            "time_color": "#B8860B",
            "prefix": "[[WRN]]",
        },
        "ERROR": {
            "icon": UnicodeIcons.EMOJI_ERROR,
            "color": "#FF4444",
            "bg_color": "#260D0D",
            "time_color": "#8B0000",
            "prefix": "[[ERR]]",
        },
        "CRITICAL": {
            "icon": UnicodeIcons.EMOJI_CRITICAL,
            "color": "#FF0000",
            "bg_color": "#3D0D0D",
            "time_color": "#8B0000",
            "prefix": "[[CRT]]",
            "bold": True,
            "reverse": True,
        },
    }

    # Разделители для разных типов сообщений
    DIVIDERS = {
        "none": "",
        "thin": "─" * 60,
        "thick": "═" * 60,
        "dotted": "┈" * 60,
        "double": "═" * 60,
    }

    def __init__(
        self,
        max_lines: int = 100,
        show_timestamp: bool = True,
        show_level: bool = True,
        show_icons: bool = True,
        show_prefix: bool = False,
        truncate_length: int | None = None,
        add_dividers: bool = False,
        divider_on_level: Literal["WARNING", "ERROR", "CRITICAL"] = "WARNING",
    ) -> None:
        """
        Инициализация просмотрщика логов.

        Args:
            max_lines: Максимальное количество хранимых строк
            show_timestamp: Показывать временные метки
            show_level: Показывать уровень лога
            show_icons: Показывать Unicode иконки
            show_prefix: Показывать текстовый префикс уровня
            truncate_length: Максимальная длина сообщения (None для безлимита)
            add_dividers: Добавлять разделители перед важными сообщениями
            divider_on_level: Уровень лога для добавления разделителя
        """
        self._max_lines = max_lines
        self._show_timestamp = show_timestamp
        self._show_level = show_level
        self._show_icons = show_icons
        self._show_prefix = show_prefix
        self._truncate_length = truncate_length
        self._add_dividers = add_dividers
        self._divider_on_level = divider_on_level

        # Хранилище логов с метаданными
        self._logs: deque[dict] = deque(maxlen=max_lines)

        # Счётчики по уровням
        self._counts: dict[LogLevel, int] = {
            "DEBUG": 0,
            "INFO": 0,
            "WARNING": 0,
            "ERROR": 0,
            "CRITICAL": 0,
            "SUCCESS": 0,
        }

    def add_log(self, message: str, level: LogLevel = "INFO") -> None:
        """
        Добавить лог.

        Args:
            message: Сообщение лога
            level: Уровень лога
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        style = self.LOG_STYLES.get(level, self.LOG_STYLES["INFO"])

        # Обрезать сообщение если нужно
        display_message = message
        if self._truncate_length and len(message) > self._truncate_length:
            display_message = truncate_text(message, self._truncate_length)

        # Создать структурированный лог
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": display_message,
            "original_message": message,
            "style": style,
            "divider": self._add_dividers and level == self._divider_on_level,
        }

        self._logs.append(log_entry)

        # Обновить счётчик
        if level in self._counts:
            self._counts[level] += 1

    def _format_log_entry(self, log_entry: dict) -> str:
        """
        Форматировать запись лога для отображения.

        Args:
            log_entry: Запись лога

        Returns:
            Форматированная строка
        """
        style = log_entry["style"]
        parts = []

        # Разделитель если нужен
        if log_entry.get("divider"):
            parts.append(f"[dim]{self.DIVIDERS['thin']}[/]")

        # Иконка
        if self._show_icons:
            parts.append(f"{style['icon']} ")

        # Временная метка
        if self._show_timestamp:
            parts.append(f"[{style['time_color']}][{log_entry['timestamp']}][/] ")

        # Уровень лога
        if self._show_level:
            if self._show_prefix:
                parts.append(f"[{style['color']}]{style['prefix']}[/] ")
            else:
                parts.append(f"[{style['color']}][{log_entry['level']}][/] ")

        # Сообщение
        message_style = style["color"]
        if style.get("bold"):
            message_style = f"bold {message_style}"
        if style.get("reverse"):
            message_style = f"reverse {message_style}"

        parts.append(f"[{message_style}]{log_entry['message']}[/]")

        return "".join(parts)

    def _render_text(self) -> str:
        """
        Получить текстовое представление логов.

        Returns:
            Строка с логами
        """
        if not self._logs:
            # Пустое состояние с иконкой
            return ptg.tim.parse(f"[dim]{UnicodeIcons.EMOJI_INFO} Нет логов...[/]")

        # Отформатировать все логи
        formatted_logs = []
        for log_entry in self._logs:
            formatted = self._format_log_entry(log_entry)
            formatted_logs.append(formatted)

        return "\n".join(formatted_logs)

    def render(self) -> ptg.Container:
        """
        Рендерить лог-вьювер.

        Returns:
            Container с логами
        """
        if not self._logs:
            return ptg.Container(
                ptg.Label(ptg.tim.parse(f"[dim]{UnicodeIcons.EMOJI_INFO} Нет логов...[/]")),
                height=10,
                box="ROUNDED",
            )

        # Создать контейнер с логами
        log_labels = []
        for log_entry in self._logs:
            formatted = self._format_log_entry(log_entry)
            log_labels.append(ptg.Label(ptg.tim.parse(formatted)))

        return ptg.Container(
            *log_labels,
            height=10,
            box="ROUNDED",
        )

    def clear(self) -> None:
        """Очистить логи."""
        self._logs.clear()
        self._counts = {level: 0 for level in self._counts}

    def get_logs(self, level: LogLevel | None = None) -> list[dict]:
        """
        Получить логи.

        Args:
            level: Фильтр по уровню (None для всех)

        Returns:
            Список записей логов
        """
        if level:
            return [log for log in self._logs if log["level"] == level]
        return list(self._logs)

    def get_counts(self) -> dict[LogLevel, int]:
        """
        Получить счётчики по уровням.

        Returns:
            Словарь с количеством логов по уровням
        """
        return self._counts.copy()

    def get_summary(self) -> str:
        """
        Получить краткую сводку по логам.

        Returns:
            Строка со сводкой
        """
        total = sum(self._counts.values())
        if total == 0:
            return "Нет логов"

        parts = []
        for level, count in self._counts.items():
            if count > 0:
                style = self.LOG_STYLES[level]
                parts.append(f"[{style['color']}]{level}: {count}[/]")

        return " | ".join(parts)

    def render_summary(self) -> str:
        """
        Отрендерить сводку по логам.

        Returns:
            Строка со сводкой
        """
        summary = self.get_summary()
        return ptg.tim.parse(f"[dim]Логи:[/] {summary}")

    @property
    def line_count(self) -> int:
        """Количество строк логов."""
        return len(self._logs)

    @property
    def total_count(self) -> int:
        """Общее количество логов."""
        return sum(self._counts.values())

    @property
    def error_count(self) -> int:
        """Количество ошибок."""
        return self._counts.get("ERROR", 0) + self._counts.get("CRITICAL", 0)

    @property
    def warning_count(self) -> int:
        """Количество предупреждений."""
        return self._counts.get("WARNING", 0)

    @property
    def success_count(self) -> int:
        """Количество успешных сообщений."""
        return self._counts.get("SUCCESS", 0)


class CompactLogViewer(LogViewer):
    """
    Компактная версия просмотрщика логов.

    Использует более плотный формат отображения
    для экономии места на экране.
    """

    def __init__(self, max_lines: int = 50, **kwargs) -> None:
        """
        Инициализация компактного просмотрщика.

        Args:
            max_lines: Максимальное количество строк
            **kwargs: Дополнительные параметры для LogViewer
        """
        super().__init__(
            max_lines=max_lines,
            show_timestamp=True,
            show_level=False,
            show_icons=True,
            show_prefix=False,
            truncate_length=80,
            **kwargs,
        )

    def _format_log_entry(self, log_entry: dict) -> str:
        """
        Форматировать запись в компактном стиле.

        Args:
            log_entry: Запись лога

        Returns:
            Компактная строка
        """
        style = log_entry["style"]

        # Компактный формат: [ВРЕМЯ] Иконка Сообщение
        return (
            f"[dim][{log_entry['timestamp']}][/] "
            f"{style['icon']} "
            f"[{style['color']}]{log_entry['message']}[/]"
        )


class DetailedLogViewer(LogViewer):
    """
    Детальная версия просмотрщика логов.

    Показывает полную информацию с разделителями
    и дополнительным форматированием.
    """

    def __init__(self, max_lines: int = 200, **kwargs) -> None:
        """
        Инициализация детального просмотрщика.

        Args:
            max_lines: Максимальное количество строк
            **kwargs: Дополнительные параметры для LogViewer
        """
        super().__init__(
            max_lines=max_lines,
            show_timestamp=True,
            show_level=True,
            show_icons=True,
            show_prefix=True,
            truncate_length=None,
            add_dividers=True,
            divider_on_level="WARNING",
            **kwargs,
        )

    def _format_log_entry(self, log_entry: dict) -> str:
        """
        Форматировать запись в детальном стиле.

        Args:
            log_entry: Запись лога

        Returns:
            Детальная строка
        """
        style = log_entry["style"]

        # Детальный формат: [ВРЕМЯ] [УРОВЕНЬ] Иконка Сообщение
        return (
            f"[{style['time_color']}][{log_entry['timestamp']}][/] "
            f"[bold {style['color']}][{log_entry['level']}][/] "
            f"{style['icon']} "
            f"[{style['color']}]{log_entry['message']}[/]"
        )
