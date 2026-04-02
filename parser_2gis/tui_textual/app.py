"""Главное приложение TUI Parser2GIS на Textual.

Современный интерфейс с использованием библиотеки Textual.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from parser_2gis.config import Configuration
from parser_2gis.logger import logger
from parser_2gis.parallel import ParallelCityParser
from parser_2gis.resources import CATEGORIES_93

from .screens import (
    AboutScreen,
    BrowserSettingsScreen,
    CacheViewerScreen,
    CategorySelectorScreen,
    CitySelectorScreen,
    MainMenuScreen,
    OutputSettingsScreen,
    ParserSettingsScreen,
    ParsingScreen,
)

# =============================================================================
# DATACLASS ДЛЯ СОСТОЯНИЯ ПРИЛОЖЕНИЯ (ISSUE-020)
# =============================================================================


@dataclass
class AppState:
    """Состояние приложения TUI.

    ISSUE-020: Замена TypedDict на dataclass для лучшей типизации и управления состоянием.

    Attributes:
        selected_cities: Выбранные города для парсинга.
        selected_categories: Выбранные категории для парсинга.
        parsing_active: Флаг активного парсинга.
        parsing_progress: Прогресс парсинга в процентах.
        total_urls: Общее количество URL для парсинга.
        current_url: Текущий обрабатываемый URL.
        current_city: Текущий город.
        current_category: Текущая категория.
        success_count: Количество успешных операций.
        error_count: Количество ошибок.
        total_pages: Общее количество страниц.
        current_page: Текущая страница.
        total_records: Общее количество записей.
        current_record: Текущая запись.
        _parsing_logs: Буфер логов парсинга.

    """

    selected_cities: list[str] = field(default_factory=list)
    selected_categories: list[str] = field(default_factory=list)
    parsing_active: bool = False
    parsing_progress: int = 0
    total_urls: int = 0
    current_url: int = 0
    current_city: str = ""
    current_category: str = ""
    success_count: int = 0
    error_count: int = 0
    total_pages: int = 0
    current_page: int = 0
    total_records: int = 0
    current_record: int = 0
    _parsing_logs: list[str] = field(default_factory=list)

    def reset(self) -> None:
        """Сбрасывает состояние к значениям по умолчанию."""
        self.selected_cities = []
        self.selected_categories = []
        self.parsing_active = False
        self.parsing_progress = 0
        self.total_urls = 0
        self.current_url = 0
        self.current_city = ""
        self.current_category = ""
        self.success_count = 0
        self.error_count = 0
        self.total_pages = 0
        self.current_page = 0
        self.total_records = 0
        self.current_record = 0
        self._parsing_logs = []

    def update(self, **kwargs: Any) -> None:
        """Обновляет поля состояния.

        Args:
            **kwargs: Ключ-значение для обновления.

        Note:
            Для ключа "_parsing_logs" применяется ограничение размера буфера
            до MAX_LOG_BUFFER_SIZE записей.

        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Ограничиваем буфер логов
        if len(self._parsing_logs) > MAX_LOG_BUFFER_SIZE:
            self._parsing_logs = self._parsing_logs[-MAX_LOG_BUFFER_SIZE:]

    def to_dict(self) -> dict[str, Any]:
        """Конвертирует состояние в словарь.

        Returns:
            Словарь с полями состояния.

        """
        return {
            "selected_cities": self.selected_cities,
            "selected_categories": self.selected_categories,
            "parsing_active": self.parsing_active,
            "parsing_progress": self.parsing_progress,
            "total_urls": self.total_urls,
            "current_url": self.current_url,
            "current_city": self.current_city,
            "current_category": self.current_category,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "total_pages": self.total_pages,
            "current_page": self.current_page,
            "total_records": self.total_records,
            "current_record": self.current_record,
            "_parsing_logs": self._parsing_logs,
        }


# =============================================================================
# КОНСТАНТЫ ПРИЛОЖЕНИЯ
# =============================================================================

# Максимальный размер буфера логов для предотвращения утечки памяти
MAX_LOG_BUFFER_SIZE: int = 1000


class TUIApp(App):
    """Главное приложение TUI Parser2GIS на Textual.

    Управляет экранами, навигацией и состоянием приложения.
    """

    # CSS стили приложения
    CSS = """
    /* Базовые стили для всех экранов */
    Screen {
        background: $surface;
        align: center middle;
    }

    /* Контейнер главного меню */
    #main-menu {
        width: 100%;
        max-width: 60;
        min-width: 50;
        height: auto;
        align: center middle;
    }

    /* Контейнер заголовка */
    .title-container {
        width: 100%;
        height: auto;
        content-align: center middle;
        margin-bottom: 1;
    }

    /* Заголовок */
    .title {
        text-style: bold;
        color: $text;
        width: 100%;
        content-align: center top;
    }

    /* Подзаголовок */
    .subtitle {
        color: $text-muted;
        width: 100%;
        content-align: center top;
    }

    /* Контейнер меню */
    .menu-container {
        width: 100%;
        max-width: 50;
        min-width: 40;
        height: auto;
        background: $surface-darken-2;
        border: solid $primary;
        padding: 1 2;
        align: center middle;
    }

    /* Кнопка меню */
    .menu-button {
        width: 100%;
        margin: 1 0;
        align: center middle;
    }

    /* Логотип */
    .logo {
        width: 100%;
        content-align: center top;
        color: $accent;
        text-style: bold;
    }

    /* Счётчик */
    .counter-panel {
        width: 100%;
        height: 3;
        content-align: center middle;
        margin: 1 0;
    }

    /* Статистика */
    .stats-container {
        width: 100%;
        height: auto;
    }

    /* Метка статистики */
    .stat-label {
        width: 100%;
        margin: 0;
    }

    /* Контейнер прогресса */
    .progress-container {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    /* Лог */
    .log-container {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }

    /* Панель поиска */
    .search-panel {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    /* Список городов */
    .city-list {
        width: 100%;
        height: 1fr;
    }

    /* Ряд кнопок */
    .button-row {
        width: 100%;
        height: auto;
        align: center middle;
        dock: bottom;
    }

    /* Разделитель */
    .divider {
        height: 1;
        background: $primary;
        margin: 1 0;
    }
    """

    # Горячие клавиши
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Выход", priority=True),
        Binding("escape", "go_back", "Назад", priority=True),
        Binding("d", "toggle_dark", "Тёмная тема"),
    ]

    # Регистрация экранов
    SCREENS: ClassVar[dict[str, type]] = {
        "main_menu": MainMenuScreen,
        "city_selector": CitySelectorScreen,
        "category_selector": CategorySelectorScreen,
        "parsing": ParsingScreen,
        "browser_settings": BrowserSettingsScreen,
        "parser_settings": ParserSettingsScreen,
        "output_settings": OutputSettingsScreen,
        "cache_viewer": CacheViewerScreen,
        "about": AboutScreen,
    }

    def __init__(self, **kwargs: Mapping[str, Any]) -> None:
        """Инициализация приложения.

        Args:
            **kwargs: Аргументы для родительского класса App.

        """
        super().__init__(**kwargs)
        self._config = self._load_config()
        self._state = AppState()  # ISSUE-020: Используем dataclass
        self._file_logger: logging.Logger | None = None
        self._log_file: Path | None = None
        self._parser: ParallelCityParser | None = None
        self._running = False
        self._started_at: datetime | None = None
        self._last_notification: dict[str, str] | None = None
        self._cleanup_in_progress: bool = False

    def _load_config(self) -> Configuration:
        """Загружает конфигурацию приложения.

        Формат конфигурации:
            Конфигурация загружается через Configuration.load_config() и содержит:
            - chrome: Настройки браузера Chrome (headless, disable_images, и т.д.)
            - parser: Настройки парсера (max_retries, timeout, и т.д.)
            - parallel: Настройки параллельного парсинга (max_workers, и т.д.)
            - output: Настройки вывода (format, output_dir, и т.д.)

        Returns:
            Объект Configuration с загруженными настройками.

        """
        return Configuration.load_config()

    def _init_state(self) -> AppState:
        """Инициализировать состояние приложения.

        Returns:
            Новый экземпляр AppState.

        """
        return AppState()

    def _clear_state(self) -> None:
        """Очистить состояние приложения для освобождения памяти."""
        self._state.reset()
        self._parser = None
        self._last_notification = None

    @property
    def last_notification(self) -> dict[str, str] | None:
        """Последнее уведомление."""
        return self._last_notification

    @property
    def selected_cities(self) -> list[str]:
        """Выбранные города."""
        return self._state.selected_cities

    @selected_cities.setter
    def selected_cities(self, value: list[str]) -> None:
        """Устанавливает список выбранных городов.

        Args:
            value: Список названий городов для выбора.

        """
        self._state.selected_cities = value

    @property
    def selected_categories(self) -> list[str]:
        """Выбранные категории."""
        return self._state.selected_categories

    @selected_categories.setter
    def selected_categories(self, value: list[str]) -> None:
        """Устанавливает список выбранных категорий.

        Args:
            value: Список названий категорий для выбора.

        """
        self._state.selected_categories = value

    @property
    def running(self) -> bool:
        """Флаг работы приложения."""
        return self._running

    @running.setter
    def running(self, value: bool) -> None:
        """Устанавливает флаг работы приложения.

        Args:
            value: True если приложение работает, False иначе.

        """
        self._running = value

    def get_config(self) -> Configuration:
        """Получить конфигурацию."""
        return self._config

    def save_config(self) -> None:
        """Сохранить конфигурацию."""
        self._config.save_config()

    def get_cities(self) -> list[dict[str, Any]]:
        """Получить список городов."""
        cities_path = Path(__file__).parent.parent / "data" / "cities.json"
        if cities_path.exists():
            with open(cities_path, encoding="utf-8") as f:
                return json.load(f)
        return []

    def get_categories(self) -> list[dict[str, str | int]]:
        """Получить список категорий."""
        return CATEGORIES_93  # type: ignore[return-value]

    def update_state(self, **kwargs: Any) -> None:
        """Обновить состояние приложения.

        ISSUE-020: Использует dataclass метод update().

        Args:
            **kwargs: Ключ-значение для обновления состояния.

        """
        self._state.update(**kwargs)

    def get_state(self, key: str) -> Any:
        """Получить значение из состояния."""
        return getattr(self._state, key, None)

    def notify_user(self, message: str, level: str = "info") -> None:
        """Показать уведомление пользователю.

        Args:
            message: Текст сообщения
            level: Уровень (info, success, warning, error)

        """
        self._last_notification = {"message": message, "level": level}

        # Логирование
        if self._file_logger:
            log_method = getattr(self._file_logger, level, self._file_logger.info)
            log_method(message)
        else:
            logging.getLogger(__name__).info("[%s] %s", level, message)

        # Показ уведомления через Textual
        self.notify(message, title=level.upper())

    def compose(self) -> ComposeResult:
        """Создать интерфейс приложения."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Вызывается при монтировании приложения."""
        self._setup_logging()
        # Push main menu as the default screen
        self.push_screen("main_menu")

    def _setup_logging(self) -> None:
        """Настроить логирование."""
        # Используем существующий logger с очисткой предыдущих handlers
        self._file_logger = logging.getLogger("parser_2gis.tui")

        # Очищаем существующие handlers для предотвращения утечки ресурсов
        if self._file_logger.handlers:
            for handler in self._file_logger.handlers[:]:
                try:
                    handler.close()
                    self._file_logger.removeHandler(handler)
                except (OSError, RuntimeError, TypeError, ValueError):
                    pass  # Игнорируем ошибки при очистке

        self._file_logger.setLevel(logging.INFO)

    def action_go_back(self) -> None:
        """Вернуться назад."""
        self.pop_screen()

    def action_toggle_dark(self) -> None:
        """Переключить тёмную тему."""
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"

    def push_main_menu(self) -> None:
        """Показать главное меню."""
        self.push_screen("main_menu")

    def push_city_selector(self) -> None:
        """Показать выбор городов."""
        self.push_screen("city_selector")

    def push_category_selector(self) -> None:
        """Показать выбор категорий."""
        self.push_screen("category_selector")

    def push_browser_settings(self) -> None:
        """Показать настройки браузера."""
        self.push_screen("browser_settings")

    def push_parser_settings(self) -> None:
        """Показать настройки парсера."""
        self.push_screen("parser_settings")

    def push_output_settings(self) -> None:
        """Показать настройки вывода."""
        self.push_screen("output_settings")

    def push_cache_viewer(self) -> None:
        """Показать просмотр кэша."""
        self.push_screen("cache_viewer")

    def push_about_screen(self) -> None:
        """Показать информацию о программе."""
        self.push_screen("about")

    def push_parsing_screen(self) -> None:
        """Показать экран парсинга."""
        self.push_screen("parsing")

    def switch_to_main_menu(self) -> None:
        """Переключиться на главное меню (замена текущего экрана)."""
        self.switch_screen("main_menu")

    def stop_parsing(self) -> None:
        """Остановить парсинг.

        Корректно останавливает фоновый процесс парсинга
        без остановки всего приложения.
        """
        if self._running:
            self._running = False
            self.notify_user("Парсинг остановлен", level="warning")

    def start_parsing(self, cities: list[dict], categories: list[dict]) -> None:
        """Запустить парсинг.

        Args:
            cities: Список городов
            categories: Список категорий

        """
        # Проверка что данные выбраны перед запуском
        if not cities:
            self.notify_user("Ошибка: не выбраны города для парсинга!", level="error")
            # Вернуться в главное меню
            self.call_from_thread(self.switch_to_main_menu)
            return

        if not categories:
            self.notify_user("Ошибка: не выбраны категории для парсинга!", level="error")
            # Вернуться в главное меню
            self.call_from_thread(self.switch_to_main_menu)
            return

        # Экран парсинга уже открыт через switch_screen из category_selector
        # Запускаем только фоновый процесс парсинга
        # Примечание: push_screen НЕ вызывается здесь, чтобы избежать дублирования экранов
        self._run_parsing(cities, categories)

    @work(exclusive=True, thread=True)
    def _run_parsing(self, cities: list[dict], categories: list[dict]) -> None:
        """Запустить парсинг в фоне.

        Args:
            cities: Список городов
            categories: Список категорий

        """
        try:
            self._running = True
            self._started_at = datetime.now()

            # Проверка флага остановки перед началом работы
            if not self._running:
                return

            config = self._config
            config.chrome.headless = True
            config.chrome.disable_images = True
            config.chrome.silent_browser = True
            config.parser.stop_on_first_404 = True
            config.parser.max_consecutive_empty_pages = 5
            config.parser.max_retries = 3
            config.parser.retry_on_network_errors = True

            max_workers = getattr(config.parallel, "max_workers", 10)

            from parser_2gis.constants.cache import DEFAULT_OUTPUT_DIR

            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=DEFAULT_OUTPUT_DIR,
                config=config,
                max_workers=max_workers,
                timeout_per_url=1800,  # 30 минут для парсинга одной категории
            )

            total_urls = len(cities) * len(categories)
            self.update_state(total_urls=total_urls)

            def progress_callback(success: int, failed: int, filename: str) -> None:
                """Callback для обновления прогресса парсинга.

                Args:
                    success: Количество успешных операций
                    failed: Количество неудачных операций
                    filename: Имя файла вывода

                Note:
                    Использует call_from_thread для синхронизации с главным потоком
                    и предотвращения race condition при доступе к состоянию приложения.

                """
                # Проверка флага остановки во время парсинга
                if not self._running:
                    return

                # Синхронизация с главным потоком для предотвращения race condition
                def update_progress_state() -> None:
                    """Обновляет состояние прогресса парсинга в главном потоке.

                    Извлекает название категории из имени файла и обновляет
                    счётчики успешных/неудачных операций в состоянии приложения.
                    """
                    if not self._running:
                        return
                    category = (
                        filename.replace(".csv", "").split("_")[-1] if "_" in filename else ""
                    )
                    self.update_state(
                        success_count=success,
                        error_count=failed,
                        current_category=category,
                        current_record=success + failed,
                    )
                    if not self._running:
                        return

                self.call_from_thread(update_progress_state)

            output_file = f"Омск_парсинг_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            result = parser.run(output_file=output_file, progress_callback=progress_callback)

            # Проверка флага остановки после завершения парсинга
            if not self._running:
                return

            self._running = False
            self.call_from_thread(self._parsing_complete, result)

        except Exception as e:
            self._running = False
            self.call_from_thread(self._parsing_error, str(e))
            # Вернуться в главное меню при ошибке
            self.call_from_thread(self.switch_to_main_menu)
        finally:
            # P0-5: Гарантированная очистка ресурсов парсинга
            # Вызываем parser.cancel() и get_stats() корректно
            if "parser" in locals():
                try:
                    parser.stop()  # Вызываем cancel через метод stop()
                    parser_stats = parser.get_statistics()
                    logger.debug("Статистика парсера после завершения: %s", parser_stats)
                except (
                    OSError,
                    RuntimeError,
                    TypeError,
                    ValueError,
                    AttributeError,
                ) as cleanup_error:
                    logger.debug("Ошибка при очистке парсера: %s", cleanup_error)

            if not self._cleanup_in_progress:
                self._cleanup_in_progress = True
                try:
                    self.stop_parsing()
                finally:
                    self._cleanup_in_progress = False

    def _parsing_complete(self, success: bool) -> None:
        """Обработка завершения парсинга."""
        screen = self.screen
        if hasattr(screen, "on_parsing_complete"):
            screen.on_parsing_complete(success)
        # Вернуться в главное меню после завершения
        self.switch_to_main_menu()

    def _parsing_error(self, error: str) -> None:
        """Обработка ошибки парсинга."""
        screen = self.screen
        if hasattr(screen, "on_parsing_error"):
            screen.on_parsing_error(error)
        # Вернуться в главное меню после ошибки
        self.switch_to_main_menu()


class Parser2GISTUI:
    """Обёртка для запуска TUI."""

    def __init__(self) -> None:
        """Инициализация TUI."""
        self._app = TUIApp()

    def run(self) -> None:
        """Запустить TUI приложение."""
        self._app.run()


def run_tui() -> None:
    """Точка входа для запуска TUI."""
    app = Parser2GISTUI()
    app.run()
