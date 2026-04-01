"""
Лаунчер приложения Parser2GIS.

Модуль предоставляет класс ApplicationLauncher для разделения режимов работы приложения
и управления жизненным циклом.

Примечание:
    Реализует Dependency Inversion Principle (DIP):
    - Зависимости внедряются через __init__
    - Используются Protocol для абстракции зависимостей
"""

from __future__ import annotations

import argparse
import gc
import sqlite3
import threading
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Protocol

from parser_2gis.cache import CacheManager
from parser_2gis.chrome.remote import ChromeRemote
from parser_2gis.config import Configuration
from parser_2gis.logger import logger
from parser_2gis.utils.paths import cache_path
from parser_2gis.utils.signal_handler import SignalHandler

if TYPE_CHECKING:
    from parser_2gis.parser.options import ParserOptions


# =============================================================================
# PROTOCOLS ДЛЯ ВНЕШНИХ ЗАВИСИМОСТЕЙ (DIP)
# =============================================================================


class CleanupCallback(Protocol):
    """Protocol для callback очистки ресурсов."""

    def __call__(self) -> None:
        """Вызывает очистку ресурсов."""


class SignalHandlerFactory(Protocol):
    """Protocol для фабрики SignalHandler."""

    def __call__(self, cleanup_callback: Optional[CleanupCallback] = None) -> SignalHandler:
        """Создаёт SignalHandler."""


# =============================================================================
# СИГНАЛЫ И ОЧИСТКА РЕСУРСОВ
# =============================================================================


class ApplicationLauncher:
    """Лаунчер приложения с разделением режимов работы.

    Управляет инициализацией, обработкой сигналов и запуском приложения
    в различных режимах (TUI, CLI, параллельный парсинг).

    Реализует Dependency Inversion Principle:
    - Зависимости внедряются через __init__
    - Используются Protocol для абстракции

    Attributes:
        config: Конфигурация приложения.
        options: Опции парсера.
        signal_handler: Обработчик сигналов.
        signal_handler_factory: Фабрика для создания SignalHandler.

    Example:
        >>> # Использование с dependency injection
        >>> launcher = ApplicationLauncher(config, options)
        >>> launcher.launch(args)
    """

    def __init__(
        self,
        config: "Configuration",
        options: "ParserOptions",
        signal_handler_factory: Optional[SignalHandlerFactory] = None,
    ):
        """Инициализация лаунчера.

        Args:
            config: Конфигурация приложения.
            options: Опции парсера.
            signal_handler_factory: Опциональная фабрика SignalHandler
                                   для внедрения зависимости (тестирование).

        Note:
            По умолчанию используется SignalHandler, но для тестирования
            можно передать mock фабрику.
        """
        self.config = config
        self.options = options
        self._signal_handler: Optional[SignalHandler] = None
        self._signal_handler_lock = threading.Lock()
        self._signal_handler_factory = signal_handler_factory or SignalHandler

    def launch(self, args: argparse.Namespace) -> int:
        """Запуск приложения в выбранном режиме.

        Args:
            args: Аргументы командной строки.

        Returns:
            Код завершения приложения.
        """
        self._setup_signal_handlers()

        # Обработка TUI режимов
        if getattr(args, "tui_new_omsk", False):
            return self._run_tui_mode(args, tui_type="omsk")
        elif getattr(args, "tui_new", False):
            return self._run_tui_mode(args, tui_type="main")
        elif getattr(args, "parallel_workers", 1) > 1 or getattr(args, "cities", None):
            return self._run_parallel_mode(args)
        else:
            return self._run_cli_mode(args)

    def _setup_signal_handlers(self) -> None:
        """Настройка обработчиков сигналов SIGINT и SIGTERM.

        Использует внедрённую фабрику SignalHandler для создания обработчика.
        """
        with self._signal_handler_lock:
            # Используем внедрённую зависимость (DIP)
            self._signal_handler = self._signal_handler_factory(
                cleanup_callback=self._cleanup_resources
            )
            self._signal_handler.register()
        logger.debug("Обработчики сигналов SIGINT и SIGTERM установлены через ApplicationLauncher")

    def _run_tui_mode(self, args: argparse.Namespace, tui_type: str = "main") -> int:
        """Запуск TUI режима.

        Args:
            args: Аргументы командной строки.
            tui_type: Тип TUI ("main" или "omsk").

        Returns:
            Код завершения приложения.
        """
        # Опциональный импорт TUI модулей
        try:
            if tui_type == "omsk":
                from parser_2gis.tui_textual import run_tui as run_new_tui_omsk

                if run_new_tui_omsk is None:
                    logger.error("TUI модуль (textual) недоступен")
                    return 1
                run_new_tui_omsk()
                return 0
            else:
                from parser_2gis.tui_textual import Parser2GISTUI

                if Parser2GISTUI is None:
                    logger.error("TUI модуль (textual) недоступен")
                    return 1
                app = Parser2GISTUI()
                app.run()
                return 0

        except ImportError as e:
            logger.error("TUI модуль недоступен: %s", e)
            return 1
        except Exception as e:
            logger.error("Ошибка при запуске TUI: %s", e, exc_info=True)
            return 1

    def _run_parallel_mode(self, args: argparse.Namespace) -> int:
        """Запуск параллельного режима парсинга.

        Args:
            args: Аргументы командной строки.

        Returns:
            Код завершения приложения.
        """
        try:
            # Импортируем здесь для избежания циклических зависимостей
            from parser_2gis.parallel import ParallelCityParser
            from parser_2gis.resources import CATEGORIES_93, load_cities_json
            from parser_2gis.utils.paths import resources_path

            # Загружаем города
            cities_path = resources_path() / "cities.json"
            all_cities = load_cities_json(str(cities_path))
            selected_cities = [city for city in all_cities if city["code"] in args.cities]

            if not selected_cities:
                logger.error("Города с кодами %s не найдены", args.cities)
                return 1

            # Создаём конфигурацию
            from parser_2gis.chrome.options import ChromeOptions
            from parser_2gis.parallel.options import ParallelOptions
            from parser_2gis.parser.options import ParserOptions
            from parser_2gis.writer.options import WriterOptions

            config = Configuration(
                parallel=ParallelOptions(
                    max_workers=self.config.parallel.max_workers, use_temp_file_cleanup=True
                ),
                chrome=ChromeOptions(
                    headless=self.config.chrome.headless,
                    disable_images=self.config.chrome.disable_images,
                ),
                parser=ParserOptions(
                    max_records=self.config.parser.max_records,
                    delay_ms=self.config.parser.delay_between_clicks,
                    retry_on_network_errors=self.config.parser.retry_on_network_errors,
                ),
                writer=WriterOptions(format="csv", encoding="utf-8-sig", deduplicate=True),
            )

            # Определяем output_dir
            output_dir = self._get_output_dir(getattr(args, "output_path", None))
            output_dir.mkdir(parents=True, exist_ok=True)

            # Создаём парсер
            parser = ParallelCityParser(
                cities=selected_cities,
                categories=CATEGORIES_93,
                output_dir=str(output_dir),
                config=config,
                max_workers=self.config.parallel.max_workers,
                timeout_per_url=1800,
            )

            def progress_callback(success: int, failed: int, filename: str) -> None:
                """Callback для обновления прогресса."""
                logger.info("Прогресс: успешно=%d, ошибок=%d, файл=%s", success, failed, filename)

            # Определяем имя выходного файла
            output_file = self._get_output_filename(args, "omsk_all_categories.csv")
            output_file_path = output_dir / output_file

            result = parser.run(
                output_file=str(output_file_path), progress_callback=progress_callback
            )

            if result:
                logger.info("Парсинг успешно завершён")
                return 0
            else:
                logger.error("Парсинг завершён с ошибками")
                return 1

        except (FileNotFoundError, ValueError, OSError) as e:
            logger.error("Ошибка при загрузке городов: %s", e)
            return 1
        except Exception as e:
            logger.error("Ошибка параллельного парсинга: %s", e, exc_info=True)
            return 1
        finally:
            self._cleanup_resources()

    def _run_cli_mode(self, args: argparse.Namespace) -> int:
        """Запуск CLI режима.

        Args:
            args: Аргументы командной строки.

        Returns:
            Код завершения приложения.
        """
        try:
            from parser_2gis.cli import cli_app
            from parser_2gis.resources import load_cities_json
            from parser_2gis.utils.paths import resources_path
            from parser_2gis.utils.url_utils import generate_city_urls

            urls = args.url or []
            categories_mode = getattr(args, "categories_mode", False)
            has_cities = hasattr(args, "cities") and args.cities is not None

            # Обработка городов
            if has_cities:
                cities_path = resources_path() / "cities.json"
                all_cities = load_cities_json(str(cities_path))
                selected_cities = [city for city in all_cities if city["code"] in args.cities]

                if not selected_cities:
                    logger.error("Города с кодами %s не найдены", args.cities)
                    return 1

                if categories_mode:
                    # Категории уже обработаны в parallel_mode
                    logger.error("Режим категорий должен запускаться через parallel_mode")
                    return 1

                query = args.query or "Организации"
                rubric = {"code": args.rubric} if args.rubric else None
                generated_urls = generate_city_urls(selected_cities, query, rubric)
                urls.extend(generated_urls)

            # Валидация входных данных
            if not categories_mode:
                if not urls and not has_cities:
                    logger.error("Не указан источник URL. Используйте -i/--url или --cities")
                    return 1

                output_path = getattr(args, "output_path", None)
                output_format = getattr(args, "format", None)

                if not output_path:
                    logger.error("Не указан путь к выходному файлу. Используйте -o/--output-path")
                    return 1

                if not output_format:
                    logger.error("Не указан формат выходного файла. Используйте -f/--format")
                    return 1

            # Запуск CLI приложения
            cli_app(urls, output_path, output_format, self.config)
            return 0

        except KeyboardInterrupt:
            logger.info("Работа приложения прервана пользователем (KeyboardInterrupt).")
            return 0
        except FileNotFoundError as e:
            logger.error("Файл не найден: %s", e)
            return 1
        except PermissionError as e:
            logger.error("Ошибка доступа к файлу: %s", e)
            return 1
        except ValueError as e:
            logger.error("Ошибка валидации данных: %s", e)
            return 1
        except TimeoutError as e:
            logger.error("Превышено время ожидания операции: %s", e)
            return 1
        except ConnectionError as e:
            logger.error("Ошибка соединения: %s", e)
            return 1
        except OSError as e:
            logger.error("Ошибка операционной системы: %s", e)
            return 1
        except (sqlite3.Error, TypeError, RuntimeError) as e:
            logger.error("Критическая ошибка приложения: %s", e, exc_info=True)
            return 1
        finally:
            self._cleanup_resources()

    def _get_output_dir(self, output_path: Optional[str]) -> Path:
        """Определяет директорию для результатов.

        Args:
            output_path: Путь к файлу или директории.

        Returns:
            Path объект директории.
        """
        if output_path is None:
            return Path("output")

        output_path_obj = Path(output_path)
        if output_path_obj.suffix and output_path_obj.parent.exists():
            return output_path_obj.parent
        return output_path_obj.parent if output_path_obj.parent != Path(".") else output_path_obj

    def _get_output_filename(self, args: argparse.Namespace, default: str) -> str:
        """Определяет имя выходного файла.

        Args:
            args: Аргументы командной строки.
            default: Имя файла по умолчанию.

        Returns:
            Имя выходного файла.
        """
        output_path = getattr(args, "output_path", None)
        if output_path:
            output_path_obj = Path(output_path)
            if output_path_obj.suffix:
                return output_path_obj.name
        return default

    def _cleanup_resources(self) -> None:
        """Выполняет централизованную очистку ресурсов приложения."""
        try:
            logger.debug("Очистка кэша ресурсов...")

            # Очистка ChromeRemote
            self._cleanup_chrome_remote()

            # Очистка кэша
            self._cleanup_cache()

            # Сборка мусора
            self._cleanup_gc()

            logger.info("Очистка ресурсов завершена")

        except MemoryError as e:
            logger.critical("Критическая ошибка: нехватка памяти при очистке ресурсов: %s", e)
        except Exception as e:
            logger.error("Непредвиденная ошибка при очистке ресурсов: %s", e, exc_info=True)

    def _cleanup_chrome_remote(self) -> None:
        """Очищает активные соединения ChromeRemote."""
        if not hasattr(ChromeRemote, "_active_instances"):
            return

        try:
            chrome_instances_closed = 0
            chrome_errors = 0

            for instance in ChromeRemote._active_instances:
                try:
                    if instance is not None:
                        instance.stop()
                        chrome_instances_closed += 1
                except (AttributeError, RuntimeError) as e:
                    logger.error("Ошибка при закрытии ChromeRemote: %s", e, exc_info=True)
                    chrome_errors += 1

            logger.info(
                "Закрыто экземпляров ChromeRemote: %d, ошибок: %d",
                chrome_instances_closed,
                chrome_errors,
            )

        except (TypeError, AttributeError) as e:
            logger.error("Ошибка итерации _active_instances: %s", e, exc_info=True)

    def _cleanup_cache(self) -> None:
        """Очищает кэш базы данных CacheManager."""
        try:
            cache = CacheManager(cache_path())
            cache.close()
            logger.info("Кэш базы данных успешно закрыт")
        except Exception as e:
            logger.error("Ошибка при закрытии кэша: %s", e, exc_info=True)

    def _cleanup_gc(self) -> None:
        """Выполняет принудительный сборщик мусора."""
        try:
            gc.collect()
            logger.debug("Сборщик мусора завершён")
        except Exception as e:
            logger.error("Ошибка gc.collect(): %s", e, exc_info=True)


# =============================================================================
# LRU CACHE ДЛЯ SIGNAL HANDLER
# =============================================================================


@lru_cache(maxsize=1)
def _get_signal_handler_cached(handler_instance: SignalHandler) -> SignalHandler:
    """Кэшированная версия получения SignalHandler.

    Args:
        handler_instance: Экземпляр SignalHandler.

    Returns:
        Тот же экземпляр SignalHandler.
    """
    return handler_instance


__all__ = ["ApplicationLauncher", "_get_signal_handler_cached"]
