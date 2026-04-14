"""Лаунчер приложения Parser2GIS.

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
from typing import TYPE_CHECKING, Any, Protocol

from parser_2gis.config import Configuration
from parser_2gis.logger import logger
from parser_2gis.utils.signal_handler import SignalHandler

if TYPE_CHECKING:
    from parser_2gis.cache import CacheManager
    from parser_2gis.parser.options import ParserOptions


# =============================================================================
# ОБЩАЯ ЛОГИКА TUI (ISSUE-045: УСТРАНЕНИЕ ДУБЛИРОВАНИЯ)
# =============================================================================


def _import_tui_main() -> tuple[Any, Any]:
    """Импортирует TUI модули.

    ISSUE-045: Вынесена общая логика импорта TUI из launcher.py и main.py.

    Returns:
        Кортеж (Parser2GISTUI, run_tui_omsk).
        Если модуль недоступен, возвращает (None, None).

    """
    try:
        from parser_2gis.tui_textual import Parser2GISTUI
        from parser_2gis.tui_textual import run_tui as run_new_tui_omsk

        return Parser2GISTUI, run_new_tui_omsk
    except ImportError as e:
        logger.error("TUI модуль (textual) недоступен: %s", e)
        return None, None


def run_tui_application(tui_type: str = "main") -> int:
    """Запускает TUI приложение.

    ISSUE-045: Общая функция для запуска TUI из launcher.py и main.py.

    Args:
        tui_type: Тип TUI ("main" или "omsk").

    Returns:
        Код завершения (0 - успех, 1 - ошибка).

    """
    Parser2GISTUI, run_new_tui_omsk = _import_tui_main()

    if Parser2GISTUI is None and run_new_tui_omsk is None:
        logger.error("TUI модуль (textual) недоступен")
        return 1

    try:
        if tui_type == "omsk" and run_new_tui_omsk is None:
            logger.error("TUI режим 'omsk' недоступен")
            return 1
        elif tui_type == "omsk":
            run_new_tui_omsk()
        elif Parser2GISTUI is None:
            logger.error("TUI режим 'main' недоступен")
            return 1
        else:
            app = Parser2GISTUI()
            app.run()
        return 0
    except (KeyboardInterrupt, SystemExit):
        return 1
    except (ImportError, RuntimeError, OSError) as e:
        logger.error("Ошибка при запуске TUI: %s", e, exc_info=True)
        return 1


# =============================================================================
# PROTOCOLS ДЛЯ ВНЕШНИХ ЗАВИСИМОСТЕЙ (DIP)
# =============================================================================


class CleanupCallback(Protocol):
    """Protocol для callback очистки ресурсов."""

    def __call__(self) -> None:
        """Вызывает очистку ресурсов."""


class SignalHandlerFactory(Protocol):
    """Protocol для фабрики SignalHandler."""

    def __call__(self, cleanup_callback: CleanupCallback | None = None) -> SignalHandler:
        """Создаёт SignalHandler."""
        ...  # Protocol method stub


class ChromeRemoteFactory(Protocol):
    """Protocol для фабрики ChromeRemote."""

    def __call__(self) -> Any:
        """Создаёт или возвращает экземпляр ChromeRemote."""
        ...  # Protocol method stub


class CacheManagerFactory(Protocol):
    """Protocol для фабрики CacheManager."""

    def __call__(self, _cache_path_obj: Path) -> CacheManager:
        """Создаёт CacheManager."""
        ...  # Protocol method stub


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
        chrome_factory: Фабрика для создания ChromeRemote.
        cache_factory: Фабрика для создания CacheManager.

    Example:
        >>> # Использование с dependency injection
        >>> launcher = ApplicationLauncher(config, options)
        >>> launcher.launch(args)

    """

    def __init__(
        self,
        config: Configuration,
        options: ParserOptions,
        signal_handler_factory: SignalHandlerFactory | None = None,
        chrome_factory: ChromeRemoteFactory | None = None,
        cache_factory: CacheManagerFactory | None = None,
    ) -> None:
        """Инициализация лаунчера.

        Args:
            config: Конфигурация приложения.
            options: Опции парсера.
            signal_handler_factory: Опциональная фабрика SignalHandler
                                   для внедрения зависимости (тестирование).
            chrome_factory: Опциональная фабрика ChromeRemote для DI.
            cache_factory: Опциональная фабрика CacheManager для DI.

        Note:
            По умолчанию используются стандартные фабрики, но для тестирования
            можно передать mock фабрики.

        """
        self.config = config
        self.options = options
        self._signal_handler: SignalHandler | None = None
        self._signal_handler_lock = threading.Lock()
        self._signal_handler_factory = signal_handler_factory or SignalHandler
        self._chrome_factory = chrome_factory
        self._cache_factory = cache_factory

    def launch(self, args: argparse.Namespace) -> int:
        """Запуск приложения в выбранном режиме.

        Args:
            args: Аргументы командной строки.

        Returns:
            Код завершения приложения.

        """
        try:
            self._setup_signal_handlers()
        except (TypeError, AttributeError, RuntimeError) as e:
            logger.error("Ошибка при настройке обработчиков сигналов: %s", e, exc_info=True)
            return 1
        except (KeyboardInterrupt, SystemExit):
            return 1

        # Обработка TUI режимов
        if getattr(args, "tui_new_omsk", False):
            return self._run_tui_mode(args, tui_type="omsk")
        if getattr(args, "tui_new", False):
            return self._run_tui_mode(args, tui_type="main")
        if getattr(args, "parallel_workers", 1) > 1 or getattr(args, "cities", None):
            return self._run_parallel_mode(args)
        return self._run_cli_mode(args)

    def _setup_signal_handlers(self) -> None:
        """Настройка обработчиков сигналов SIGINT и SIGTERM.

        Использует внедрённую фабрику SignalHandler для создания обработчика.
        """
        with self._signal_handler_lock:
            # Используем внедрённую зависимость (DIP)
            self._signal_handler = self._signal_handler_factory(
                cleanup_callback=self._cleanup_resources,
            )
            self._signal_handler.register()
        logger.debug("Обработчики сигналов SIGINT и SIGTERM установлены через ApplicationLauncher")

    def _run_tui_mode(self, _args: argparse.Namespace, tui_type: str = "main") -> int:
        """Запуск TUI режима.

        ISSUE-045: Использует общую функцию run_tui_application для устранения дублирования.

        Args:
            _args: Аргументы командной строки.
            tui_type: Тип TUI ("main" или "omsk").

        Returns:
            Код завершения приложения.

        """
        return run_tui_application(tui_type=tui_type)

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
                    max_workers=self.config.parallel.max_workers,
                    use_temp_file_cleanup=True,
                ),
                chrome=ChromeOptions(
                    headless=self.config.chrome.headless,
                    disable_images=self.config.chrome.disable_images,
                ),
                parser=ParserOptions(  # type: ignore[call-arg]
                    max_records=self.config.parser.max_records,
                    delay_between_clicks=self.config.parser.delay_between_clicks,
                    retry_on_network_errors=self.config.parser.retry_on_network_errors,
                ),
                writer=WriterOptions(
                    encoding="utf-8-sig",
                ),
            )

            # Определяем output_dir
            output_dir = self._get_output_dir(getattr(args, "output_path", None))
            output_dir.mkdir(parents=True, exist_ok=True)

            # Создаём парсер
            parser = ParallelCityParser(
                cities=selected_cities,
                categories=CATEGORIES_93,  # type: ignore[arg-type]
                output_dir=str(output_dir),
                config=config,
                max_workers=self.config.parallel.max_workers,
                timeout_per_url=self.config.parser.timeout,
            )

            def progress_callback(success: int, failed: int, filename: str) -> None:
                """Записать информацию о прогрессе парсинга в лог."""
                logger.info("Прогресс: успешно=%d, ошибок=%d, файл=%s", success, failed, filename)

            # Определяем имя выходного файла
            # Используем формат из конфигурации для определения расширения
            output_extension = self.config.writer.format or "csv"  # type: ignore[attr-defined]
            output_file = self._get_output_filename(args, f"all_categories.{output_extension}")
            output_file_path = output_dir / output_file

            result = parser.run(
                output_file=str(output_file_path),
                progress_callback=progress_callback,
            )

            if result:
                logger.info("Парсинг успешно завершён")
                return 0
            logger.error("Парсинг завершён с ошибками")
            return 1

        except (FileNotFoundError, ValueError, OSError) as e:
            logger.error("Ошибка при загрузке городов или конфигурации: %s", e)
            return 1
        except (TypeError, KeyError, RuntimeError) as e:
            logger.error("Критическая ошибка параллельного парсинга: %s", e, exc_info=True)
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
            # Локальный импорт для избежания циклической зависимости
            from parser_2gis.cli.app import cli_app
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
            if not categories_mode and not urls and not has_cities:
                logger.error("Не указан источник URL. Используйте -i/--url или --cities")
                return 1

            if not categories_mode:
                output_path = getattr(args, "output_path", None)
                output_format = getattr(args, "format", None)

                if not output_path:
                    logger.error("Не указан путь к выходному файлу. Используйте -o/--output-path")
                    return 1

                if not output_format:
                    logger.error("Не указан формат выходного файла. Используйте -f/--format")
                    return 1

            # Запуск CLI приложения
            cli_app(urls, output_path, output_format, self.config)  # type: ignore[arg-type]
            return 0

        except KeyboardInterrupt:
            logger.info("Работа приложения прервана пользователем (KeyboardInterrupt).")
            return 0
        except (
            FileNotFoundError,
            PermissionError,
            ValueError,
            TimeoutError,
            ConnectionError,
            OSError,
        ) as e:
            logger.error("Ошибка операции ввода-вывода или валидации: %s", e)
            return 1
        except (sqlite3.Error, TypeError, RuntimeError) as e:
            logger.error("Критическая ошибка приложения: %s", e, exc_info=True)
            return 1
        finally:
            self._cleanup_resources()

    def _get_output_dir(self, output_path: str | None) -> Path:
        """Определяет директорию для результатов.

        Args:
            output_path: Путь к файлу или директории.

        Returns:
            Path объект директории.

        """
        from parser_2gis.constants.cache import DEFAULT_OUTPUT_DIR

        if output_path is None:
            return Path(DEFAULT_OUTPUT_DIR)

        output_path_obj = Path(output_path)
        # Если путь имеет расширение (например, .csv), это файл - возвращаем родительскую директорию
        if output_path_obj.suffix:
            return output_path_obj.parent if output_path_obj.parent != Path() else Path()
        # Если путь не имеет расширения, считаем его директорией
        return output_path_obj

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
        """Выполняет централизованную очистку ресурсов приложения.

        Освобождает ресурсы ChromeRemote, кэш базы данных и выполняет
        принудительную сборку мусора для предотвращения утечек памяти.

        Returns:
            None

        Raises:
            MemoryError: При критической нехватке памяти во время очистки.
            Exception: При непредвиденных ошибках очистки ресурсов.

        Example:
            >>> launcher = ApplicationLauncher(config, options)
            >>> try:
            ...     launcher.launch(args)
            ... finally:
            ...     launcher._cleanup_resources()

        Note:
            Метод вызывается автоматически в блоках finally методов
            _run_parallel_mode и _run_cli_mode.

        """
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
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError, ImportError) as e:
            logger.error("Непредвиденная ошибка при очистке ресурсов: %s", e, exc_info=True)

    def _cleanup_chrome_remote(self) -> None:
        """Очищает активные соединения ChromeRemote.

        Закрывает все активные экземпляры ChromeRemote через вызов метода stop().
        Кэширует список экземпляров перед итерацией для безопасности.

        Returns:
            None

        Raises:
            TypeError: При ошибке итерации _active_instances.
            AttributeError: Если ChromeRemote не имеет атрибута _active_instances.

        Example:
            >>> launcher = ApplicationLauncher(config, options)
            >>> launcher._cleanup_chrome_remote()

        """
        try:
            # Используем внедрённую зависимость или импортируем по умолчанию
            if self._chrome_factory is not None:
                chrome_instance = self._chrome_factory()
                if chrome_instance is None:
                    return
                chrome_class = type(chrome_instance)
            else:
                from parser_2gis.chrome.remote import ChromeRemote

                chrome_class = ChromeRemote

            if not hasattr(chrome_class, "_active_instances"):
                return

            chrome_class_type: type[Any] = chrome_class

            # ID:049: Кэшируем список экземпляров перед итерацией для безопасности
            try:
                chrome_instances = list(chrome_class_type._active_instances)
            except (TypeError, AttributeError) as list_error:
                logger.error("Ошибка создания копии списка _active_instances: %s", list_error)
                return

            chrome_instances_closed = 0
            chrome_errors = 0

            for instance in chrome_instances:
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
        """Очищает кэш базы данных CacheManager.

        Закрывает соединение с кэшем базы данных для освобождения ресурсов.
        Проверяет существование активного кэша перед созданием нового.

        Returns:
            None

        Raises:
            Exception: При ошибке закрытия кэша.

        Example:
            >>> launcher = ApplicationLauncher(config, options)
            >>> launcher._cleanup_cache()

        """
        try:
            from parser_2gis.utils.paths import cache_path

            # ID:050: Проверяем, существует ли уже активный кэш
            # чтобы не создавать новый CacheManager только для закрытия
            if self._cache_factory is not None:
                cache = self._cache_factory(cache_path())
            else:
                from parser_2gis.cache import CacheManager

                # Проверяем существование файла кэша перед созданием менеджера
                cache_file = cache_path() / "cache.db"
                if not cache_file.exists():
                    logger.debug("Файл кэша не найден, закрытие не требуется")
                    return
                cache = CacheManager(cache_path())

            cache.close()
            logger.info("Кэш базы данных успешно закрыт")
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError, ImportError) as e:
            logger.error("Ошибка при закрытии кэша: %s", e, exc_info=True)

    def _cleanup_gc(self) -> None:
        """Выполняет принудительный сборщик мусора.

        Вызывает gc.collect() для освобождения памяти.

        Returns:
            None

        Raises:
            Exception: При ошибке выполнения gc.collect().

        Example:
            >>> launcher = ApplicationLauncher(config, options)
            >>> launcher._cleanup_gc()

        """
        try:
            gc.collect()
            logger.debug("Сборщик мусора завершён")
        except (KeyboardInterrupt, SystemExit):
            raise
        except (RuntimeError, OSError) as e:
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


__all__ = [
    "ApplicationLauncher",
    "_get_signal_handler_cached",
    # ISSUE-045: Экспорт общих функций для устранения дублирования
    "_import_tui_main",
    "run_tui_application",
]
