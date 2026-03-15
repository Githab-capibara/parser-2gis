"""
Главное приложение TUI Parser2GIS на pytermgui.

Управляет всеми экранами, навигацией и состоянием приложения.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import pytermgui as ptg

from ..config import Configuration
from ..data.categories_93 import CATEGORIES_93
from ..parallel_parser import ParallelCityParser
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
from .styles import get_default_styles
from .utils import ScreenManager

if TYPE_CHECKING:
    from ..parallel_parser import ParallelCityParser as ParallelParser


class TUIApp:
    """
    Главное приложение TUI Parser2GIS.

    Управляет окнами, навигацией и состоянием приложения.
    """

    def __init__(self) -> None:
        """Инициализация приложения."""
        self._manager: Optional[ptg.WindowManager] = None
        self._config = self._load_config()
        self._state = self._init_state()
        self._screen_manager: Optional[ScreenManager] = None
        self._logger: Optional[logging.Logger] = None
        self._log_file: Optional[Path] = None
        self._parser: Optional[ParallelParser] = None

        # Флаги
        self._running = False
        self._started_at: Optional[datetime] = None

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

    def run(self) -> None:
        """Запустить приложение."""
        # Загрузка стилей
        self._load_styles()

        # Создание менеджера окон
        with ptg.WindowManager() as self._manager:
            # Создание главного меню
            self._screen_manager = ScreenManager(self)
            self._show_main_menu()

            # Запуск цикла событий
            self._manager.run()

    def _load_styles(self) -> None:
        """Загрузить стили из YAML."""
        styles_yaml = get_default_styles()
        with ptg.YamlLoader() as loader:
            loader.load(styles_yaml)

    def _show_main_menu(self) -> None:
        """Показать главное меню."""
        if not self._manager or not self._screen_manager:
            return

        # Очистить все окна - удалить все существующие
        for window in list(self._manager._windows):
            self._manager.remove(window)

        # Создать главное меню
        main_menu = MainMenuScreen(self)
        main_window = main_menu.create_window()

        self._manager.add(main_window)
        self._screen_manager.push("main_menu", main_menu)

    def _show_city_selector(self) -> None:
        """Показать экран выбора городов."""
        if not self._manager or not self._screen_manager:
            return

        # Очистить все окна - удалить все существующие
        for window in list(self._manager._windows):
            self._manager.remove(window)

        # Создать экран выбора городов
        city_selector = CitySelectorScreen(self)
        city_window = city_selector.create_window()

        self._manager.add(city_window)
        self._screen_manager.push("city_selector", city_selector)

    def _show_category_selector(self) -> None:
        """Показать экран выбора категорий."""
        if not self._manager or not self._screen_manager:
            return

        # Очистить все окна - удалить все существующие
        for window in list(self._manager._windows):
            self._manager.remove(window)

        # Создать экран выбора категорий
        category_selector = CategorySelectorScreen(self)
        category_window = category_selector.create_window()

        self._manager.add(category_window)
        self._screen_manager.push("category_selector", category_selector)

    def _show_browser_settings(self) -> None:
        """Показать экран настроек браузера."""
        if not self._manager or not self._screen_manager:
            return

        # Очистить все окна - удалить все существующие
        for window in list(self._manager._windows):
            self._manager.remove(window)

        # Создать экран настроек браузера
        browser_settings = BrowserSettingsScreen(self)
        browser_window = browser_settings.create_window()

        self._manager.add(browser_window)
        self._screen_manager.push("browser_settings", browser_settings)

    def _show_parser_settings(self) -> None:
        """Показать экран настроек парсера."""
        if not self._manager or not self._screen_manager:
            return

        # Очистить все окна - удалить все существующие
        for window in list(self._manager._windows):
            self._manager.remove(window)

        # Создать экран настроек парсера
        parser_settings = ParserSettingsScreen(self)
        parser_window = parser_settings.create_window()

        self._manager.add(parser_window)
        self._screen_manager.push("parser_settings", parser_settings)

    def _show_output_settings(self) -> None:
        """Показать экран настроек вывода."""
        if not self._manager or not self._screen_manager:
            return

        # Очистить все окна - удалить все существующие
        for window in list(self._manager._windows):
            self._manager.remove(window)

        # Создать экран настроек вывода
        output_settings = OutputSettingsScreen(self)
        output_window = output_settings.create_window()

        self._manager.add(output_window)
        self._screen_manager.push("output_settings", output_settings)

    def _show_cache_viewer(self) -> None:
        """Показать экран просмотра кэша."""
        if not self._manager or not self._screen_manager:
            return

        # Очистить все окна - удалить все существующие
        for window in list(self._manager._windows):
            self._manager.remove(window)

        # Создать экран просмотра кэша
        cache_viewer = CacheViewerScreen(self)
        cache_window = cache_viewer.create_window()

        self._manager.add(cache_window)
        self._screen_manager.push("cache_viewer", cache_viewer)

    def _show_about(self) -> None:
        """Показать экран О программе."""
        if not self._manager or not self._screen_manager:
            return

        # Очистить все окна - удалить все существующие
        for window in list(self._manager._windows):
            self._manager.remove(window)

        # Создать экран О программе
        about_screen = AboutScreen(self)
        about_window = about_screen.create_window()

        self._manager.add(about_window)
        self._screen_manager.push("about", about_screen)

    def _show_parsing_screen(self) -> None:
        """Показать экран парсинга."""
        if not self._manager or not self._screen_manager:
            return

        # Очистить все окна - удалить все существующие
        for window in list(self._manager._windows):
            self._manager.remove(window)

        # Создать экран парсинга
        parsing_screen = ParsingScreen(self)
        parsing_window = parsing_screen.create_window()

        self._manager.add(parsing_window)
        self._screen_manager.push("parsing", parsing_screen)

        # Запустить парсинг
        self._start_parsing()

    def go_back(self) -> None:
        """Вернуться к предыдущему экрану."""
        if not self._manager or not self._screen_manager:
            return

        previous_screen = self._screen_manager.pop()

        if previous_screen:
            # Очистить все окна - удалить все существующие
            for window in list(self._manager._windows):
                self._manager.remove(window)

            # Восстановить предыдущий экран
            if self._screen_manager.current_instance:
                window = self._screen_manager.current_instance.create_window()
                self._manager.add(window)
        else:
            # Если стек пуст, показать главное меню
            self._show_main_menu()

    def _start_parsing(self) -> None:
        """Запустить парсинг."""
        self._running = True
        self._started_at = datetime.now()

        # Получить конфигурацию
        config = self._config

        # Настроить параметры для парсинга
        config.chrome.headless = True
        config.chrome.disable_images = True
        config.chrome.silent_browser = True

        config.parser.stop_on_first_404 = True
        config.parser.max_consecutive_empty_pages = 5
        config.parser.max_retries = 3
        config.parser.retry_on_network_errors = True

        # Загрузить города
        cities_data = self.get_cities()
        selected_cities_data = [
            city for city in cities_data
            if city.get("name") in self.selected_cities
        ]

        if not selected_cities_data:
            self._add_log_to_parsing_screen("Ошибка: не выбраны города", "ERROR")
            return

        # Загрузить категории
        all_categories = self.get_categories()
        selected_categories_data = [
            cat for cat in all_categories
            if cat.get("name") in self.selected_categories
        ]

        if not selected_categories_data:
            self._add_log_to_parsing_screen("Ошибка: не выбраны категории", "ERROR")
            return

        # Добавить лог
        self._add_log_to_parsing_screen(
            f"Запуск парсинга: {len(selected_cities_data)} городов × {len(selected_categories_data)} категорий",
            "INFO",
        )
        self._add_log_to_parsing_screen(f"Потоков: {self._config.parser.max_retries}", "DEBUG")

        # Запустить парсер в отдельном потоке
        thread = threading.Thread(
            target=self._run_parallel_parser,
            args=(selected_cities_data, selected_categories_data, config),
            daemon=True,
        )
        thread.start()

    def _run_parallel_parser(
        self,
        cities: list[dict],
        categories: list[dict],
        config: Configuration,
    ) -> None:
        """
        Запустить параллельный парсер.

        Args:
            cities: Список городов
            categories: Список категорий
            config: Конфигурация
        """
        try:
            # Создать парсер
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir="output",
                config=config,
                max_workers=10,  # 10 параллельных браузеров
                timeout_per_url=300,
            )

            # Обновить состояние
            total_urls = len(cities) * len(categories)
            self.update_state(total_urls=total_urls)

            # Создать callback для обновления прогресса
            def progress_callback(success: int, failed: int, filename: str) -> None:
                # Извлечь категорию из имени файла
                category = filename.replace(".csv", "").split("_")[-1] if "_" in filename else ""

                # Обновить состояние
                self.update_state(
                    success_count=success,
                    error_count=failed,
                    current_category=category,
                    current_record=success + failed,
                )

                # Добавить лог
                if success % 5 == 0 or failed > 0:
                    self._add_log_to_parsing_screen(
                        f"Обработано: {success} успешно, {failed} ошибок",
                        "INFO",
                    )

            # Запустить парсинг
            output_file = f"Омск_парсинг_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            result = parser.run(
                output_file=output_file,
                progress_callback=progress_callback,
            )

            # Завершить
            self._stop_parsing(success=result)

        except KeyboardInterrupt:
            self._add_log_to_parsing_screen("Парсинг прерван пользователем", "WARNING")
            self._stop_parsing(success=False)
        except Exception as e:
            self._add_log_to_parsing_screen(f"Критическая ошибка: {e}", "ERROR")
            self._stop_parsing(success=False)

    def _add_log_to_parsing_screen(self, message: str, level: str = "INFO") -> None:
        """
        Добавить лог на экран парсинга.

        Args:
            message: Сообщение лога
            level: Уровень лога
        """
        if self._screen_manager:
            screen = self._screen_manager.current_instance
            if screen and hasattr(screen, "add_log"):
                screen.add_log(message, level)

    def _stop_parsing(self, success: bool = True) -> None:
        """
        Остановить парсинг.

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
            self._logger.info(f"Всего записей: {self._state['current_record']}")
            self._logger.info(f"Успешно: {self._state['success_count']}")
            self._logger.info(f"Ошибок: {self._state['error_count']}")
            self._logger.info("=" * 80)

    def update_state(self, **kwargs: Any) -> None:
        """
        Обновить состояние приложения.

        Args:
            **kwargs: Параметры для обновления состояния
        """
        for key, value in kwargs.items():
            if key in self._state:
                self._state[key] = value

    def get_state(self, key: str) -> Any:
        """
        Получить значение из состояния.

        Args:
            key: Ключ состояния

        Returns:
            Значение состояния
        """
        return self._state.get(key)

    def save_config(self) -> None:
        """Сохранить конфигурацию."""
        self._config.save_config()

    def get_config(self) -> Configuration:
        """Получить конфигурацию."""
        return self._config

    def get_cities(self) -> list[dict[str, Any]]:
        """
        Получить список городов.

        Returns:
            Список городов
        """
        cities_path = Path(__file__).parent.parent / "data" / "cities.json"
        if cities_path.exists():
            with open(cities_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def get_categories(self) -> list[dict[str, str | int]]:
        """
        Получить список категорий.

        Returns:
            Список категорий с полями name, query, rubric_code
        """
        return CATEGORIES_93  # type: ignore[return-value]

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


class Parser2GISTUI:
    """
    Основной класс для запуска TUI Parser2GIS.

    Обёртка над TUIApp для удобного запуска.
    """

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
