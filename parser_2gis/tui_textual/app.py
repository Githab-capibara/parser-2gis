"""
Главное приложение TUI Parser2GIS на Textual.

Современный интерфейс с использованием библиотеки Textual.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from parser_2gis.config import Configuration
from parser_2gis.data.categories_93 import CATEGORIES_93
from parser_2gis.parallel import ParallelCityParser

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


class TUIApp(App):
    """
    Главное приложение TUI Parser2GIS на Textual.

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
    BINDINGS = [
        Binding("q", "quit", "Выход", priority=True),
        Binding("escape", "go_back", "Назад", priority=True),
        Binding("d", "toggle_dark", "Тёмная тема"),
    ]

    # Регистрация экранов
    SCREENS = {
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
        self._state = self._init_state()
        self._file_logger: Optional[logging.Logger] = None
        self._log_file: Optional[Path] = None
        self._parser: Optional[ParallelCityParser] = None
        self._running = False
        self._started_at: Optional[datetime] = None
        self._last_notification: Optional[dict[str, str]] = None

    def _load_config(self) -> Configuration:
        """Загрузить конфигурацию."""
        return Configuration.load_config()

    def _init_state(self) -> dict[str, Any]:
        """Инициализировать состояние приложения."""
        return {
            "selected_cities": [],
            "selected_categories": [],
            "parsing_active": False,
            "parsing_progress": 0,
            "total_urls": 0,
            "current_url": 0,
            "current_city": "",
            "current_category": "",
            "success_count": 0,
            "error_count": 0,
            "total_pages": 0,
            "current_page": 0,
            "total_records": 0,
            "current_record": 0,
        }

    @property
    def last_notification(self) -> Optional[dict[str, str]]:
        """Последнее уведомление."""
        return self._last_notification

    @property
    def selected_cities(self) -> list[str]:
        """Выбранные города."""
        return self._state["selected_cities"]

    @selected_cities.setter
    def selected_cities(self, value: list[str]) -> None:
        self._state["selected_cities"] = value

    @property
    def selected_categories(self) -> list[str]:
        """Выбранные категории."""
        return self._state["selected_categories"]

    @selected_categories.setter
    def selected_categories(self, value: list[str]) -> None:
        self._state["selected_categories"] = value

    @property
    def running(self) -> bool:
        """Флаг работы приложения."""
        return self._running

    @running.setter
    def running(self, value: bool) -> None:
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
            with open(cities_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def get_categories(self) -> list[dict[str, str | int]]:
        """Получить список категорий."""
        return CATEGORIES_93  # type: ignore[return-value]

    def update_state(self, **kwargs: Any) -> None:
        """Обновить состояние приложения."""
        for key, value in kwargs.items():
            if key in self._state:
                self._state[key] = value

    def get_state(self, key: str) -> Any:
        """Получить значение из состояния."""
        return self._state.get(key)

    def notify_user(self, message: str, level: str = "info") -> None:
        """
        Показать уведомление пользователю.

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
        self._file_logger = logging.getLogger("parser_2gis.tui")
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

    def stop_parsing(self) -> None:
        """Остановить парсинг.

        Корректно останавливает фоновый процесс парсинга
        без остановки всего приложения.
        """
        if self._running:
            self._running = False
            self.notify_user("Парсинг остановлен", level="warning")

    def start_parsing(self, cities: list[dict], categories: list[dict]) -> None:
        """
        Запустить парсинг.

        Args:
            cities: Список городов
            categories: Список категорий
        """
        # Проверка что данные выбраны перед запуском
        if not cities:
            self.notify_user("Ошибка: не выбраны города для парсинга!", level="error")
            return

        if not categories:
            self.notify_user("Ошибка: не выбраны категории для парсинга!", level="error")
            return

        # Сначала открываем экран парсинга, потом запускаем процесс
        self.push_screen("parsing")
        # Запуск парсинга в фоновом режиме
        self._run_parsing(cities, categories)

    @work(exclusive=True, thread=True)
    def _run_parsing(self, cities: list[dict], categories: list[dict]) -> None:
        """
        Запустить парсинг в фоне.

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

            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="output",
                config=config,
                max_workers=max_workers,
                timeout_per_url=300,
            )

            total_urls = len(cities) * len(categories)
            self.update_state(total_urls=total_urls)

            def progress_callback(success: int, failed: int, filename: str) -> None:
                """Callback для обновления прогресса парсинга.

                Args:
                    success: Количество успешных операций
                    failed: Количество неудачных операций
                    filename: Имя файла вывода
                """
                # Проверка флага остановки во время парсинга
                if not self._running:
                    return

                category = filename.replace(".csv", "").split("_")[-1] if "_" in filename else ""
                self.update_state(
                    success_count=success,
                    error_count=failed,
                    current_category=category,
                    current_record=success + failed,
                )

                # Дополнительная проверка флага остановки после обновления состояния
                if not self._running:
                    return

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

    def _parsing_complete(self, success: bool) -> None:
        """Обработка завершения парсинга."""
        screen = self.screen
        if hasattr(screen, "on_parsing_complete"):
            screen.on_parsing_complete(success)

    def _parsing_error(self, error: str) -> None:
        """Обработка ошибки парсинга."""
        screen = self.screen
        if hasattr(screen, "on_parsing_error"):
            screen.on_parsing_error(error)


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
