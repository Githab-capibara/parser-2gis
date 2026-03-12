"""
Главное TUI приложение для Parser2GIS.

Предоставляет основной класс для управления TUI интерфейсом
с использованием rich Live display.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from rich.console import Console
from rich.live import Live
from rich.text import Text

from .components import (
    HeaderPanel,
    LogPanel,
    ProgressPanel,
    StatsPanel,
    TUIComponents,
    TUIState,
    create_main_layout,
)
from .logger import TUILogger, setup_tui_logger

if TYPE_CHECKING:
    import logging


class TUIApp:
    """
    Главное TUI приложение.

    Управляет отображением и обновлением TUI интерфейса
    с использованием rich Live display.

    Attributes:
        console: Rich консоль
        components: Компоненты TUI
        state: Состояние приложения
        live: Live display
        tui_logger: TUI логгер
    """

    def __init__(
        self,
        version: str = "1.0",
        log_dir: Optional[Path] = None,
        log_level: str = "DEBUG",
        refresh_rate: float = 0.1,
    ) -> None:
        """
        Инициализация TUI приложения.

        Args:
            version: Версия приложения
            log_dir: Директория для логов
            log_level: Уровень логирования
            refresh_rate: Частота обновления экрана (сек)
        """
        self._version = version
        self._refresh_rate = refresh_rate
        self._console = Console()
        self._components = TUIComponents()
        self._state = TUIState()
        self._live: Optional[Live] = None
        self._tui_logger: Optional[TUILogger] = None
        self._logger: Optional[logging.Logger] = None
        self._log_dir = log_dir or Path("logs")
        self._log_level = log_level

        # Флаги
        self._running = False
        self._started_at: Optional[datetime] = None

    def start(self) -> None:
        """Запустить TUI приложение."""
        self._started_at = datetime.now()
        self._state.start_time = self._started_at
        self._running = True

        # Настраиваем TUI логгер
        self._tui_logger = TUILogger(
            self._components.logs,
            self._log_dir,
            self._log_level,
        )
        self._logger = self._tui_logger.setup()

        # Инициализируем Live display
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=int(1 / self._refresh_rate),
            screen=True,
            redirect_stdout=False,
            redirect_stderr=False,
        )
        self._live.start()

        # Обновляем заголовок
        self._update_header()

        self._logger.info("TUI приложение запущено")

    def stop(self, success: bool = True) -> None:
        """
        Остановить TUI приложение.

        Args:
            success: Успешно ли завершение
        """
        self._running = False

        # Логируем завершение
        if self._logger:
            end_time = datetime.now()
            duration = end_time - self._started_at if self._started_at else None
            duration_str = str(duration).split(".")[0] if duration else "0:00:00"

            self._logger.info("=" * 80)
            self._logger.info("ЗАВЕРШЕНИЕ РАБОТЫ")
            self._logger.info(f"Статус: {'УСПЕШНО' if success else 'С ОШИБКАМИ'}")
            self._logger.info(f"Время работы: {duration_str}")
            self._logger.info(f"Всего записей: {self._state.current_record}")
            self._logger.info(f"Успешно: {self._state.success_count}")
            self._logger.info(f"Ошибок: {self._state.error_count}")
            self._logger.info("=" * 80)

        # Закрываем TUI логгер
        if self._tui_logger:
            self._tui_logger.close()

        # Останавливаем Live display
        if self._live:
            self._live.stop()

        # Финальный вывод
        self._console.print()
        if success:
            self._console.print("[bold green]✅ Парсинг завершён успешно![/bold green]")
        else:
            self._console.print("[bold red]❌ Парсинг завершён с ошибками[/bold red]")

        if self._tui_logger and self._tui_logger.log_file:
            self._console.print(
                f"[dim]Подробный лог сохранён в: {self._tui_logger.log_file.absolute()}[/dim]"
            )

    def update_state(self, **kwargs: Any) -> None:
        """
        Обновить состояние TUI.

        Args:
            **kwargs: Параметры для обновления состояния
        """
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)

        # Обновляем отображение
        self._update_all()

    def update_progress(
        self,
        url_completed: int = 0,
        page_completed: int = 0,
        record_completed: int = 0,
    ) -> None:
        """
        Обновить прогресс.

        Args:
            url_completed: Количество завершённых URL
            page_completed: Количество завершённых страниц
            record_completed: Количество завершённых записей
        """
        if url_completed > 0:
            self._components.progress.update_url(url_completed)
        if page_completed > 0:
            self._components.progress.update_page(page_completed)
        if record_completed > 0:
            self._components.progress.update_record(record_completed)

        self._state.current_record += record_completed
        self._state.current_page += page_completed

        self._update_stats()

    def add_log(self, message: str, level: str = "INFO") -> None:
        """
        Добавить лог.

        Args:
            message: Сообщение лога
            level: Уровень лога
        """
        self._components.logs.add_log(message, level)

        # Также логируем в файловый логгер
        if self._logger:
            log_method = getattr(self._logger, level.lower(), self._logger.info)
            log_method(message)

    def _update_header(self) -> None:
        """Обновить заголовок."""
        self._components.layout["header"].update(
            HeaderPanel.render(self._version)
        )

    def _update_progress(self) -> None:
        """Обновить панель прогресса."""
        self._components.layout["progress"].update(
            self._components.progress.render()
        )

    def _update_stats(self) -> None:
        """Обновить панель статистики."""
        # Вычисляем прошедшее время
        elapsed = "00:00:00"
        if self._started_at:
            delta = datetime.now() - self._started_at
            elapsed = str(delta).split(".")[0]

        # Вычисляем скорость
        speed = "0 записей/сек"
        if self._started_at and self._state.current_record > 0:
            elapsed_seconds = (datetime.now() - self._started_at).total_seconds()
            if elapsed_seconds > 0:
                records_per_sec = self._state.current_record / elapsed_seconds
                speed = f"{records_per_sec:.1f} записей/сек"

        self._components.stats.update(
            city=self._state.current_city,
            category=self._state.current_category,
            success=self._state.success_count,
            errors=self._state.error_count,
            speed=speed,
            elapsed=elapsed,
        )

        self._components.layout["stats"].update(
            self._components.stats.render()
        )

    def _update_logs(self) -> None:
        """Обновить панель логов."""
        self._components.layout["logs"].update(
            self._components.logs.render()
        )

    def _update_all(self) -> None:
        """Обновить все панели."""
        self._update_stats()
        self._update_logs()

        if self._live and self._running:
            self._live.update(self._render())

    def _render(self) -> str:
        """
        Рендерит всё приложение.

        Returns:
            Строка для отображения
        """
        from io import StringIO

        output = StringIO()
        console = Console(file=output, force_terminal=True)

        # Заголовок
        console.print(HeaderPanel.render(self._version))
        console.print()

        # Прогресс
        console.print(self._components.progress.render())
        console.print()

        # Статистика и логи
        console.print(self._components.stats.render())
        console.print()
        console.print(self._components.logs.render())

        return output.getvalue()

    @property
    def logger(self) -> Optional[logging.Logger]:
        """Логгер."""
        return self._logger

    @property
    def state(self) -> TUIState:
        """Состояние TUI."""
        return self._state

    @property
    def log_file(self) -> Optional[Path]:
        """Путь к файлу лога."""
        return self._tui_logger.log_file if self._tui_logger else None


class TUIManager:
    """
    Менеджер TUI для удобного управления приложением.

    Предоставляет упрощённый интерфейс для работы с TUI.
    """

    _instance: Optional[TUIManager] = None
    _app: Optional[TUIApp] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> TUIManager:
        """Singleton паттерн."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        version: str = "1.0",
        log_dir: Optional[Path] = None,
        log_level: str = "DEBUG",
    ) -> None:
        """
        Инициализация менеджера.

        Args:
            version: Версия приложения
            log_dir: Директория для логов
            log_level: Уровень логирования
        """
        if self._app is None:
            self._app = TUIApp(version, log_dir, log_level)

    def start(self) -> None:
        """Запустить TUI."""
        if self._app:
            self._app.start()

    def stop(self, success: bool = True) -> None:
        """
        Остановить TUI.

        Args:
            success: Успешно ли завершение
        """
        if self._app:
            self._app.stop(success)

    def update(
        self,
        total_urls: Optional[int] = None,
        current_url: Optional[str] = None,
        current_city: Optional[str] = None,
        current_category: Optional[str] = None,
        total_pages: Optional[int] = None,
        current_page: Optional[int] = None,
        success_count: Optional[int] = None,
        error_count: Optional[int] = None,
    ) -> None:
        """
        Обновить состояние TUI.

        Args:
            total_urls: Общее количество URL
            current_url: Текущий URL
            current_city: Текущий город
            current_category: Текущая категория
            total_pages: Общее количество страниц
            current_page: Текущая страница
            success_count: Количество успешных записей
            error_count: Количество ошибок
        """
        if not self._app:
            return

        kwargs = {}
        if total_urls is not None:
            kwargs["total_urls"] = total_urls
            self._app._components.progress.set_url_total(total_urls)
        if current_url is not None:
            kwargs["current_url"] = current_url
        if current_city is not None:
            kwargs["current_city"] = current_city
        if current_category is not None:
            kwargs["current_category"] = current_category
        if total_pages is not None:
            kwargs["total_pages"] = total_pages
            self._app._components.progress.set_page_total(total_pages)
        if current_page is not None:
            kwargs["current_page"] = current_page
        if success_count is not None:
            kwargs["success_count"] = success_count
        if error_count is not None:
            kwargs["error_count"] = error_count

        self._app.update_state(**kwargs)

    def progress(self, url: int = 0, page: int = 0, record: int = 0) -> None:
        """
        Обновить прогресс.

        Args:
            url: Прогресс URL
            page: Прогресс страниц
            record: Прогресс записей
        """
        if self._app:
            self._app.update_progress(url, page, record)

    def log(self, message: str, level: str = "INFO") -> None:
        """
        Добавить лог.

        Args:
            message: Сообщение лога
            level: Уровень лога
        """
        if self._app:
            self._app.add_log(message, level)

    @property
    def app(self) -> Optional[TUIApp]:
        """TUI приложение."""
        return self._app

    @property
    def logger(self) -> Optional[logging.Logger]:
        """Логгер."""
        return self._app.logger if self._app else None

    @property
    def log_file(self) -> Optional[Path]:
        """Путь к файлу лога."""
        return self._app.log_file if self._app else None
