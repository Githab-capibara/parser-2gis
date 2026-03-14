"""
Экран парсинга с прогресс-барами и логами.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytermgui as ptg

from ..widgets import LogViewer, ProgressBar

if TYPE_CHECKING:
    from .app import TUIApp
    from ..parallel_parser import ParallelParser


class ParsingScreen:
    """
    Экран парсинга.

    Отображает прогресс-бары, статистику и логи в реальном времени.
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация экрана парсинга.

        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._parser: ParallelParser | None = None
        self._log_viewer = LogViewer(max_lines=100)

        # Прогресс-бары
        self._url_progress = ProgressBar(label="URL", total=100, bar_width=30)
        self._page_progress = ProgressBar(label="Страницы", total=100, bar_width=30)
        self._record_progress = ProgressBar(label="Записи", total=1000, bar_width=30)

        # Статистика
        self._stats: dict[str, Any] = {
            "current_city": "",
            "current_category": "",
            "success_count": 0,
            "error_count": 0,
            "speed": "0 записей/сек",
            "elapsed": "00:00:00",
            "eta": "N/A",
        }

        # Таймер обновления
        self._last_update = datetime.now()
        self._start_time: datetime | None = None

        # Кнопки
        self._button_pause: ptg.Button | None = None
        self._button_stop: ptg.Button | None = None
        self._button_minimize: ptg.Button | None = None

        self._paused = False

    def create_window(self) -> ptg.Window:
        """
        Создать окно экрана парсинга.

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]Парсинг данных[/bold cyan]",
            justify="center",
        )

        # Прогресс-бары
        url_progress_label = self._url_progress.render()
        page_progress_label = self._page_progress.render()
        record_progress_label = self._record_progress.render()

        # Статистика
        stats_label = self._render_stats()

        # Логи
        self._log_viewer.add_log("Запуск парсинга...", "INFO")
        logs_box = self._log_viewer.render()

        # Кнопки управления
        self._button_pause = ptg.Button(
            "⏸ Пауза",
            callback=self._toggle_pause,
            style="primary",
        )

        self._button_stop = ptg.Button(
            "⏹ Стоп",
            callback=self._stop_parsing,
            style="error",
        )

        self._button_minimize = ptg.Button(
            "🗕 Свернуть",
            callback=self._minimize,
            style="primary",
        )

        # Создание окна
        window = ptg.Window(
            "",
            header,
            "",
            ptg.BoxLayout(
                ptg.Label("[bold]Прогресс:[/bold]"),
                direction="vertical",
            ),
            "",
            url_progress_label,
            page_progress_label,
            record_progress_label,
            "",
            ptg.BoxLayout(
                ptg.Label("[bold]Статистика:[/bold]"),
                direction="vertical",
            ),
            "",
            stats_label,
            "",
            ptg.BoxLayout(
                ptg.Label("[bold]Логи:[/bold]"),
                direction="vertical",
            ),
            "",
            logs_box,
            "",
            ptg.BoxLayout(
                self._button_pause,
                self._button_stop,
                self._button_minimize,
                direction="horizontal",
            ),
            width=90,
            box="DOUBLE",
        ).set_title("[bold green]Parser2GIS - Парсинг[/bold green]")

        return window.center()

    def _render_stats(self) -> ptg.Label:
        """
        Рендерить статистику.

        Returns:
            Label со статистикой
        """
        stats_text = (
            f"[bold]Город:[/bold] {self._stats['current_city'] or 'N/A'}\n"
            f"[bold]Категория:[/bold] {self._stats['current_category'] or 'N/A'}\n"
            f"[bold]Успешно:[/bold] [green]{self._stats['success_count']}[/green]\n"
            f"[bold]Ошибок:[/bold] [red]{self._stats['error_count']}[/red]\n"
            f"[bold]Скорость:[/bold] {self._stats['speed']}\n"
            f"[bold]Время:[/bold] {self._stats['elapsed']}\n"
            f"[bold]ETA:[/bold] {self._stats['eta']}"
        )

        return ptg.Label(stats_text)

    def update_progress(
        self,
        url_completed: int = 0,
        url_total: int | None = None,
        page_completed: int = 0,
        page_total: int | None = None,
        record_completed: int = 0,
        record_total: int | None = None,
    ) -> None:
        """
        Обновить прогресс.

        Args:
            url_completed: Количество завершённых URL
            url_total: Общее количество URL
            page_completed: Количество завершённых страниц
            page_total: Общее количество страниц
            record_completed: Количество завершённых записей
            record_total: Общее количество записей
        """
        if url_total is not None:
            self._url_progress.set_total(url_total)
        if url_completed > 0:
            self._url_progress.update(url_completed)

        if page_total is not None:
            self._page_progress.set_total(page_total)
        if page_completed > 0:
            self._page_progress.update(page_completed)

        if record_total is not None:
            self._record_progress.set_total(record_total)
        if record_completed > 0:
            self._record_progress.update(record_completed)

        self._update_stats()

    def add_log(self, message: str, level: str = "INFO") -> None:
        """
        Добавить лог.

        Args:
            message: Сообщение лога
            level: Уровень лога
        """
        self._log_viewer.add_log(message, level)  # type: ignore

    def update_stats(
        self,
        current_city: str | None = None,
        current_category: str | None = None,
        success_count: int | None = None,
        error_count: int | None = None,
    ) -> None:
        """
        Обновить статистику.

        Args:
            current_city: Текущий город
            current_category: Текущая категория
            success_count: Количество успешных записей
            error_count: Количество ошибок
        """
        if current_city is not None:
            self._stats["current_city"] = current_city
        if current_category is not None:
            self._stats["current_category"] = current_category
        if success_count is not None:
            self._stats["success_count"] = success_count
        if error_count is not None:
            self._stats["error_count"] = error_count

        self._update_stats()

    def _update_stats(self) -> None:
        """Обновить отображение статистики."""
        # Вычислить прошедшее время
        if self._start_time:
            delta = datetime.now() - self._start_time
            self._stats["elapsed"] = str(delta).split(".")[0]

            # Вычислить скорость
            if self._stats["success_count"] > 0:
                elapsed_seconds = delta.total_seconds()
                if elapsed_seconds > 0:
                    records_per_sec = self._stats["success_count"] / elapsed_seconds
                    self._stats["speed"] = f"{records_per_sec:.1f} записей/сек"

        # Вычислить ETA
        total_records = self._record_progress._total
        current_record = self._record_progress._completed

        if current_record > 0 and total_records > 0:
            elapsed_seconds = (datetime.now() - self._start_time).total_seconds() if self._start_time else 1
            records_per_sec = current_record / elapsed_seconds if elapsed_seconds > 0 else 1
            remaining = total_records - current_record
            eta_seconds = remaining / records_per_sec if records_per_sec > 0 else 0

            eta_minutes = eta_seconds / 60
            if eta_minutes < 60:
                self._stats["eta"] = f"{eta_minutes:.1f} мин"
            else:
                eta_hours = eta_minutes / 60
                self._stats["eta"] = f"{eta_hours:.1f} ч"

    def _toggle_pause(self, *args) -> None:
        """Переключить паузу."""
        self._paused = not self._paused

        if self._button_pause:
            if self._paused:
                self._button_pause.set_label("▶ Продолжить")
                self.add_log("Парсинг приостановлен", "WARNING")
            else:
                self._button_pause.set_label("⏸ Пауза")
                self.add_log("Парсинг продолжен", "INFO")

    def _stop_parsing(self, *args) -> None:
        """Остановить парсинг."""
        self.add_log("Остановка парсинга пользователем...", "WARNING")
        self._app._stop_parsing(success=False)
        self._app.go_back()

    def _minimize(self, *args) -> None:
        """Свернуть окно."""
        # TODO: Реализовать сворачивание
        self.add_log("Функция сворачивания в разработке", "INFO")

    def _start_parsing(self) -> None:
        """Запустить парсинг."""
        self._start_time = datetime.now()
        self._app._start_parsing()

        # TODO: Интеграция с ParallelParser
        # Здесь будет запуск реального парсера

    def _update_display(self) -> None:
        """Обновить отображение."""
        # Проверить, нужно ли обновлять
        now = datetime.now()
        delta = (now - self._last_update).total_seconds()

        if delta >= 0.5:  # Обновлять каждые 0.5 секунды
            self._update_stats()
            self._last_update = now
