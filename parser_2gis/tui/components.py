"""
Компоненты TUI интерфейса для Parser2GIS.

Предоставляет визуальные компоненты:
- Заголовок
- Прогресс-бары
- Панель статистики
- Панель логов
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from rich.layout import Layout
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text


@dataclass
class TUIState:
    """Состояние TUI приложения.

    Attributes:
        total_urls: Общее количество URL для обработки
        current_url: Текущий обрабатываемый URL
        current_url_index: Индекс текущего URL (0-based)
        total_pages: Общее количество страниц в текущем URL
        current_page: Текущая страница
        total_records: Общее количество записей
        current_record: Текущая запись
        success_count: Количество успешных записей
        error_count: Количество ошибок
        start_time: Время начала парсинга
        current_city: Текущий город
        current_category: Текущая категория
        status_message: Текущее сообщение статуса
    """

    total_urls: int = 0
    current_url: str = ""
    current_url_index: int = 0
    total_pages: int = 0
    current_page: int = 0
    total_records: int = 0
    current_record: int = 0
    success_count: int = 0
    error_count: int = 0
    start_time: Optional[datetime] = None
    current_city: str = ""
    current_category: str = ""
    status_message: str = "Ожидание запуска..."


class HeaderPanel:
    """Панель заголовка."""

    @staticmethod
    def render(version: str = "1.0") -> Panel:
        """
        Рендерит заголовок.

        Args:
            version: Версия приложения.

        Returns:
            Panel с заголовком.
        """
        title = Text()
        title.append("Parser2GIS", style="bold cyan")
        title.append(f" v{version}", style="dim white")

        subtitle = Text("Современный парсер данных 2GIS", style="italic green")

        return Panel(
            title,
            subtitle=subtitle,
            border_style="cyan",
            padding=(1, 2),
        )


class ProgressPanel:
    """Панель прогресс-баров."""

    def __init__(self) -> None:
        """Инициализация панели прогресса."""
        self._progress = Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40, complete_style="green", finished_style="bright_green"),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            expand=True,
        )

        # Задачи прогресса
        self._url_task_id: Optional[TaskID] = None
        self._page_task_id: Optional[TaskID] = None
        self._record_task_id: Optional[TaskID] = None

    def start(self, total_urls: int, total_pages: int = 100, total_records: int = 1000) -> None:
        """
        Запуск прогресс-баров.

        Args:
            total_urls: Общее количество URL
            total_pages: Общее количество страниц
            total_records: Общее количество записей
        """
        self._url_task_id = self._progress.add_task(
            "URL",
            total=total_urls,
            start=True,
        )
        self._page_task_id = self._progress.add_task(
            "Страницы",
            total=total_pages,
            start=False,
        )
        self._record_task_id = self._progress.add_task(
            "Записи",
            total=total_records,
            start=False,
        )

    def update_url(self, completed: int = 1) -> None:
        """Обновить прогресс URL."""
        if self._url_task_id is not None:
            self._progress.update(self._url_task_id, advance=completed)

    def update_page(self, completed: int = 1) -> None:
        """Обновить прогресс страниц."""
        if self._page_task_id is not None:
            self._progress.update(self._page_task_id, advance=completed)

    def update_record(self, completed: int = 1) -> None:
        """Обновить прогресс записей."""
        if self._record_task_id is not None:
            self._progress.update(self._record_task_id, advance=completed)

    def set_url_total(self, total: int) -> None:
        """Установить общее количество URL."""
        if self._url_task_id is not None:
            self._progress.update(self._url_task_id, total=total)

    def set_page_total(self, total: int) -> None:
        """Установить общее количество страниц."""
        if self._page_task_id is not None:
            self._progress.update(self._page_task_id, total=total)

    def set_record_total(self, total: int) -> None:
        """Установить общее количество записей."""
        if self._record_task_id is not None:
            self._progress.update(self._record_task_id, total=total)

    def render(self) -> Progress:
        """
        Рендерит прогресс-бары.

        Returns:
            Progress объект.
        """
        return self._progress


class StatsPanel:
    """Панель статистики."""

    def __init__(self) -> None:
        """Инициализация панели статистики."""
        self._stats: dict[str, str | int] = {
            "Город": "—",
            "Категория": "—",
            "Успешно": 0,
            "Ошибки": 0,
            "Скорость": "0 записей/сек",
            "Время": "00:00:00",
        }

    def update(
        self,
        city: str = "",
        category: str = "",
        success: int = 0,
        errors: int = 0,
        speed: str = "0 записей/сек",
        elapsed: str = "00:00:00",
    ) -> None:
        """
        Обновление статистики.

        Args:
            city: Текущий город
            category: Текущая категория
            success: Количество успешных записей
            errors: Количество ошибок
            speed: Скорость обработки
            elapsed: Прошедшее время
        """
        if city:
            self._stats["Город"] = city
        if category:
            self._stats["Категория"] = category
        self._stats["Успешно"] = success
        self._stats["Ошибки"] = errors
        self._stats["Скорость"] = speed
        self._stats["Время"] = elapsed

    def render(self) -> Panel:
        """
        Рендерит панель статистики.

        Returns:
            Panel со статистикой.
        """
        table = Table.grid(padding=(0, 2), expand=True)
        table.add_column(style="cyan", justify="left")
        table.add_column(style="white", justify="right")

        for key, value in self._stats.items():
            # Цвет для числовых значений
            if isinstance(value, int):
                if value > 0 and key == "Успешно":
                    value_str = f"[green]{value}[/]"
                elif value > 0 and key == "Ошибки":
                    value_str = f"[red]{value}[/]"
                else:
                    value_str = str(value)
            else:
                value_str = str(value)

            table.add_row(f"{key}:", value_str)

        return Panel(
            table,
            title="[bold]📊 Статистика[/]",
            border_style="green",
            padding=(1, 2),
        )


class LogPanel:
    """Панель логов."""

    def __init__(self, max_lines: int = 10) -> None:
        """
        Инициализация панели логов.

        Args:
            max_lines: Максимальное количество отображаемых строк логов.
        """
        self._max_lines = max_lines
        self._logs: list[Text] = []

    def add_log(self, message: str, level: str = "INFO") -> None:
        """
        Добавление лога.

        Args:
            message: Сообщение лога
            level: Уровень лога (INFO, DEBUG, WARNING, ERROR)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Цвет для уровня
        level_colors = {
            "INFO": "cyan",
            "DEBUG": "dim white",
            "WARNING": "yellow",
            "ERROR": "red",
            "SUCCESS": "green",
        }
        color = level_colors.get(level, "white")

        log_text = Text()
        log_text.append(f"[{timestamp}] ", style="dim")
        log_text.append(f"[{level}] ", style=color)
        log_text.append(message, style="white")

        self._logs.append(log_text)

        # Ограничиваем количество строк
        if len(self._logs) > self._max_lines:
            self._logs = self._logs[-self._max_lines:]

    def clear(self) -> None:
        """Очистить логи."""
        self._logs = []

    def render(self) -> Panel:
        """
        Рендерит панель логов.

        Returns:
            Panel с логами.
        """
        from rich.console import Group

        # Используем Union type для content, так как он может быть Text или Group
        content: Text | Group
        if not self._logs:
            content = Text("[dim]Ожидание логов...[/]")
        else:
            content = Group(*self._logs)

        return Panel(
            content,
            title="[bold]📋 Логи[/]",
            border_style="blue",
            padding=(1, 2),
        )


def create_main_layout() -> Layout:
    """
    Создаёт основную раскладку TUI.

    Returns:
        Layout с основной структурой.
    """
    layout = Layout()

    # Разделяем на три части: заголовок, прогресс, статус/логи
    layout.split(
        Layout(name="header", size=5),
        Layout(name="progress", size=10),
        Layout(name="main", ratio=2),
    )

    # Основную часть делим на статус и логи
    layout["main"].split_row(
        Layout(name="stats", size=40),
        Layout(name="logs"),
    )

    return layout


@dataclass
class TUIComponents:
    """Контейнер для всех компонентов TUI."""

    header: HeaderPanel = field(default_factory=HeaderPanel)
    progress: ProgressPanel = field(default_factory=ProgressPanel)
    stats: StatsPanel = field(default_factory=StatsPanel)
    logs: LogPanel = field(default_factory=LogPanel)
    layout: Layout = field(default_factory=create_main_layout)
