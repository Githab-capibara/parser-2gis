"""Точка входа CLI приложения Parser2GIS.

Модуль предоставляет функцию main() для запуска приложения.
Минимальная логика: parse args → validate → run.
"""

from __future__ import annotations

import gc
import json
import sqlite3
import sys
import threading
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from parser_2gis.cache import CacheManager
from parser_2gis.chrome.options import ChromeOptions
from parser_2gis.chrome.remote import ChromeRemote
from parser_2gis.cli import cli_app
from parser_2gis.cli.arguments import parse_arguments
from parser_2gis.config import Configuration
from parser_2gis.constants import MAX_CITIES_COUNT, MAX_CITIES_FILE_SIZE, MMAP_CITIES_THRESHOLD
from parser_2gis.data.categories_93 import CATEGORIES_93
from parser_2gis.logger import log_parser_start, logger, setup_cli_logger
from parser_2gis.parallel.options import ParallelOptions
from parser_2gis.parser.options import ParserOptions
from parser_2gis.paths import cache_path, data_path
from parser_2gis.signal_handler import SignalHandler
from parser_2gis.utils.url_utils import generate_city_urls
from parser_2gis.version import version
from parser_2gis.writer.options import WriterOptions

# Опциональный импорт TUI модуля
try:
    from parser_2gis.tui_textual import Parser2GISTUI
    from parser_2gis.tui_textual import run_tui as run_new_tui_omsk
except ImportError:
    run_new_tui_omsk = None  # type: ignore[assignment]
    Parser2GISTUI = None  # type: ignore[assignment]
    logger.warning("TUI модуль (textual) недоступен. TUI функции будут недоступны")


# Stub функции для backward совместимости
def _tui_omsk_stub() -> None:
    """Stub функция для TUI когда модуль недоступен."""
    logger.error("TUI модуль (textual) недоступен. Установите: pip install textual")
    raise RuntimeError("TUI модуль недоступен")


def _tui_stub() -> None:
    """Stub функция для Parser2GISTUI когда модуль недоступен."""
    logger.error("TUI модуль (textual) недоступен. Установите: pip install textual")
    raise RuntimeError("TUI модуль недоступен")


Cache = CacheManager

# =============================================================================
# СИГНАЛЫ И ОЧИСТКА РЕСУРСОВ
# =============================================================================

_SIGNAL_HANDLER_INSTANCE: Optional[SignalHandler] = None
_SIGNAL_HANDLER_LOCK: threading.Lock = threading.Lock()


@lru_cache(maxsize=1)
def _get_signal_handler_cached() -> SignalHandler:
    """Кэшированная версия получения SignalHandler через lru_cache.

    Returns:
        Экземпляр SignalHandler для обработки сигналов.

    Raises:
        RuntimeError: Если обработчик сигналов не инициализирован.
    """
    with _SIGNAL_HANDLER_LOCK:
        if _SIGNAL_HANDLER_INSTANCE is None:
            raise RuntimeError(
                "SignalHandler не инициализирован. Вызовите _setup_signal_handlers()."
            )
        return _SIGNAL_HANDLER_INSTANCE


def _get_signal_handler() -> SignalHandler:
    """Получает глобальный экземпляр SignalHandler.

    Returns:
        Экземпляр SignalHandler для обработки сигналов.

    Raises:
        RuntimeError: Если обработчик сигналов не инициализирован.
    """
    return _get_signal_handler_cached()


def _setup_signal_handlers() -> None:
    """Устанавливает обработчики сигналов SIGINT и SIGTERM."""
    global _SIGNAL_HANDLER_INSTANCE
    with _SIGNAL_HANDLER_LOCK:
        _SIGNAL_HANDLER_INSTANCE = SignalHandler(cleanup_callback=cleanup_resources)
        _SIGNAL_HANDLER_INSTANCE.setup()
    logger.debug("Обработчики сигналов SIGINT и SIGTERM установлены через SignalHandler")


def _cleanup_chrome_remote() -> tuple[int, int]:
    """Очищает активные соединения ChromeRemote.

    Returns:
        Кортеж (success_count, error_count) - количество успешных/неуспешных очисток.
    """
    success_count = 0
    error_count = 0

    if not hasattr(ChromeRemote, "_active_instances"):
        return success_count, error_count

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
            except (ValueError, TypeError) as e:
                logger.error("Ошибка типа при закрытии ChromeRemote: %s", e, exc_info=True)
                chrome_errors += 1

        logger.info(
            "Закрыто экземпляров ChromeRemote: %d, ошибок: %d",
            chrome_instances_closed,
            chrome_errors,
        )

        if chrome_errors > 0:
            error_count += chrome_errors
        else:
            success_count += 1

    except (TypeError, AttributeError) as e:
        logger.error("Ошибка итерации _active_instances: %s", e, exc_info=True)
        error_count += 1

    return success_count, error_count


def _cleanup_cache() -> tuple[int, int]:
    """Очищает кэш базы данных CacheManager.

    Returns:
        Кортеж (success_count, error_count) - количество успешных/неуспешных очисток.
    """
    success_count = 0
    error_count = 0

    try:
        cache = CacheManager(cache_path())
        cache.close()
        logger.info("Кэш базы данных успешно закрыт")
        success_count += 1
    except (AttributeError, RuntimeError, sqlite3.Error, OSError, ValueError, TypeError) as e:
        logger.error("Ошибка при закрытии кэша: %s", e, exc_info=True)
        error_count += 1

    return success_count, error_count


def _cleanup_gc() -> tuple[int, int]:
    """Выполняет принудительный сборщик мусора.

    Returns:
        Кортеж (success_count, error_count) - количество успешных/неуспешных очисток.
    """
    success_count = 0
    error_count = 0

    try:
        gc.collect()
        logger.debug("Сборщик мусора завершён")
        success_count += 1
    except (MemoryError, RuntimeError) as e:
        logger.error("Ошибка gc.collect(): %s", e, exc_info=True)
        error_count += 1

    return success_count, error_count


def cleanup_resources() -> None:
    """Выполняет централизованную очистку ресурсов приложения."""
    success_count = 0
    error_count = 0

    try:
        logger.debug("Очистка кэша ресурсов...")

        chrome_success, chrome_errors = _cleanup_chrome_remote()
        success_count += chrome_success
        error_count += chrome_errors

        cache_success, cache_errors = _cleanup_cache()
        success_count += cache_success
        error_count += cache_errors

        gc_success, gc_errors = _cleanup_gc()
        success_count += gc_success
        error_count += gc_errors

        logger.info(
            "Очистка ресурсов завершена. Успешно: %d, Ошибок: %d", success_count, error_count
        )

    except MemoryError as e:
        logger.critical(
            "Критическая ошибка: нехватка памяти при очистке ресурсов: %s", e, exc_info=True
        )
    except RuntimeError as e:
        logger.error("RuntimeError при очистке ресурсов: %s", e, exc_info=True)
    except KeyboardInterrupt:
        logger.warning("Очистка ресурсов прервана пользователем")
    except SystemExit as e:
        logger.error("Выход из системы при очистке ресурсов (код: %s)", e.code)
    except (ImportError, OSError, sqlite3.Error, ValueError, TypeError) as e:
        logger.error("Непредвиденная ошибка при очистке ресурсов: %s", e, exc_info=True)


# =============================================================================
# ЗАГРУЗКА ГОРОДОВ
# =============================================================================


@lru_cache(maxsize=16)
def _load_cities_json(cities_path_str: str) -> list[dict[str, Any]]:
    """Загружает JSON файл с городами с оптимизированной загрузкой.

    Args:
        cities_path_str: Путь к файлу cities.json как строка.

    Returns:
        Список городов из JSON файла.

    Raises:
        FileNotFoundError: Если файл не найден.
        ValueError: Если файл повреждён или содержит некорректные данные.
        OSError: Если произошла ошибка операционной системы.
    """
    cities_path = Path(cities_path_str)

    if not cities_path.is_file():
        logger.error("Файл городов не найден: %s", cities_path)
        raise FileNotFoundError(f"Файл {cities_path} не найден")

    try:
        file_size = cities_path.stat().st_size
        if file_size == 0:
            logger.error("Файл городов пуст: %s", cities_path)
            raise ValueError(f"Файл {cities_path} пуст")

        if file_size > MAX_CITIES_FILE_SIZE:
            logger.error(
                "Файл городов слишком большой: %d байт (макс: %d байт)",
                file_size,
                MAX_CITIES_FILE_SIZE,
            )
            raise ValueError(
                f"Файл {cities_path} слишком большой ({file_size} > {MAX_CITIES_FILE_SIZE} байт)"
            )

        logger.debug("Размер файла городов: %d байт", file_size)
    except OSError as stat_error:
        logger.error("Ошибка получения информации о файле: %s", stat_error)
        raise OSError(f"Не удалось получить информацию о файле: {stat_error}") from stat_error

    all_cities: Optional[list[dict[str, Any]]] = None

    try:
        use_mmap = file_size > MMAP_CITIES_THRESHOLD

        if use_mmap:
            logger.info(
                "Файл городов большой (%.2f MB), используется mmap для чтения",
                file_size / (1024 * 1024),
            )
            import mmap as mmap_module

            with open(cities_path, "rb") as f:
                mmapped_file = mmap_module.mmap(f.fileno(), 0, access=mmap_module.ACCESS_READ)
                try:
                    json_data = mmapped_file.read().decode("utf-8")
                    all_cities = json.loads(json_data)
                finally:
                    mmapped_file.close()
        else:
            with open(cities_path, "r", encoding="utf-8") as f:
                all_cities = json.load(f)

        if not isinstance(all_cities, list):
            logger.error("Файл городов должен содержать список, а не %s", type(all_cities).__name__)
            raise ValueError(
                f"Файл городов должен содержать список, получен {type(all_cities).__name__}"
            )

        if len(all_cities) > MAX_CITIES_COUNT:
            logger.error("Слишком много городов: %d (макс: %d)", len(all_cities), MAX_CITIES_COUNT)
            raise ValueError(
                f"Слишком много городов в файле: {len(all_cities)} > {MAX_CITIES_COUNT}"
            )

        for i, city in enumerate(all_cities):
            if not isinstance(city, dict):
                logger.error("Город %d должен быть словарём, а не %s", i, type(city).__name__)
                raise ValueError(f"Город {i} должен быть словарём")

            # ИЗМЕНЕНО: проверяем name, code, domain вместо url
            if "name" not in city or "code" not in city or "domain" not in city:
                logger.error("Город %d должен содержать поля 'name', 'code' и 'domain'", i)
                raise ValueError(f"Город {i} должен содержать поля 'name', 'code' и 'domain'")

            if (
                not isinstance(city["name"], str)
                or not isinstance(city["code"], str)
                or not isinstance(city["domain"], str)
            ):
                logger.error("Поля 'name', 'code' и 'domain' города %d должны быть строками", i)
                raise ValueError(f"Поля 'name', 'code' и 'domain' города {i} должны быть строками")

            # Опционально: проверяем country_code если есть
            if "country_code" in city and not isinstance(city["country_code"], str):
                logger.error("Поле 'country_code' города %d должно быть строкой", i)
                raise ValueError(f"Поле 'country_code' города {i} должно быть строкой")

        logger.debug("Файл городов валидирован: %d городов", len(all_cities))
        return all_cities

    except json.JSONDecodeError as e:
        logger.error("Ошибка парсинга JSON в файле городов: %s", e)
        raise ValueError(f"Некорректный формат JSON в файле городов: {e}") from e
    except OSError as e:
        logger.error("Ошибка ОС при чтении файла городов: %s", e)
        raise OSError(f"Не удалось прочитать файл городов: {e}") from e


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def _get_output_dir(output_path: str | None) -> Path:
    """Определяет директорию для результатов на основе output_path.

    Args:
        output_path: Путь к файлу или директории (может быть None).

    Returns:
        Path объект директории.
    """
    if output_path is None:
        return Path("output")

    output_path_obj = Path(output_path)
    if output_path_obj.suffix and output_path_obj.parent.exists():
        return output_path_obj.parent
    return output_path_obj.parent if output_path_obj.parent != Path(".") else output_path_obj


def _log_startup_info(args: Any, config: Configuration, start_time: datetime) -> None:
    """Логирует подробную информацию о запуске парсера.

    Args:
        args: Аргументы командной строки.
        config: Конфигурация.
        start_time: Время запуска.
    """
    format_value = getattr(args, "format", None)
    format_str = format_value.upper() if format_value else "CSV (по умолчанию)"

    output_path_value = getattr(args, "output_path", None)
    output_path_str = str(output_path_value) if output_path_value else "output/ (по умолчанию)"

    config_summary = {
        "chrome": {
            "Headless": "Да" if config.chrome.headless else "Нет",
            "Без изображений": "Да" if config.chrome.disable_images else "Нет",
            "Максимизирован": "Да" if config.chrome.start_maximized else "Нет",
        },
        "parser": {
            "Макс. записей": str(config.parser.max_records),
            "Задержка (мс)": str(config.parser.delay_between_clicks),
            "GC включен": "Да" if config.parser.use_gc else "Нет",
        },
        "writer": {
            "Формат": format_str,
            "Кодировка": config.writer.encoding,
            "Удалить дубликаты": "Да" if config.writer.csv.remove_duplicates else "Нет",
        },
    }

    urls_count = len(args.url) if args.url else 0
    if hasattr(args, "cities") and args.cities:
        if getattr(args, "categories_mode", False):
            urls_count = len(args.cities) * len(CATEGORIES_93)
        else:
            urls_count = len(args.cities)

    log_parser_start(
        version=version,
        urls_count=urls_count,
        output_path=output_path_str,
        format=format_str,
        config_summary=config_summary,
    )

    logger.info("Время запуска: %s", start_time.strftime("%Y-%m-%d %H:%M:%S"))


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================


def main() -> None:
    """Точка входа для CLI приложения.

    Парсит аргументы командной строки, обрабатывает различные режимы
    работы (TUI, CLI, параллельный парсинг) и запускает приложение.
    """
    start_datetime = datetime.now()
    _setup_signal_handlers()
    args, command_line_config = parse_arguments()

    # Обработка TUI интерфейсов
    if getattr(args, "tui_new_omsk", False):
        if run_new_tui_omsk is None:
            logger.error("TUI модуль (textual) недоступен")
            sys.exit(1)
        run_new_tui_omsk()
        return

    if getattr(args, "tui_new", False):
        if Parser2GISTUI is None:
            logger.error("TUI модуль (textual) недоступен")
            sys.exit(1)
        app = Parser2GISTUI()
        app.run()
        return

    setup_cli_logger(command_line_config.log)
    _log_startup_info(args, command_line_config, start_datetime)

    urls = args.url or []
    categories_mode = getattr(args, "categories_mode", False)
    has_cities = hasattr(args, "cities") and args.cities is not None

    if has_cities:
        cities_path = data_path() / "cities.json"
        try:
            all_cities = _load_cities_json(str(cities_path))
        except (FileNotFoundError, ValueError, OSError):
            raise

        selected_cities = [city for city in all_cities if city["code"] in args.cities]

        if not selected_cities:
            available_cities = [c["code"] for c in all_cities]
            logger.error(
                "Города с кодами %s не найдены. Доступные города: %s",
                args.cities,
                available_cities[:10],
            )
            raise ValueError(f"Города с кодами {args.cities} не найдены")

        if categories_mode:
            output_dir = _get_output_dir(args.output_path)

            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error("Ошибка при создании директории output: %s", e)
                raise

            logger.info("Запуск параллельного парсинга по %d категориям", len(CATEGORIES_93))
            logger.info("Города: %s", [c["name"] for c in selected_cities])
            logger.info("Количество потоков: %d", command_line_config.parallel.max_workers)

            # Импортируем ParallelCityParser для запуска параллельного парсинга
            from parser_2gis.parallel import ParallelCityParser

            # Создаём конфигурацию для параллельного парсера
            config = Configuration(
                parallel=ParallelOptions(
                    max_workers=command_line_config.parallel.max_workers, use_temp_file_cleanup=True
                ),
                chrome=ChromeOptions(
                    headless=command_line_config.chrome.headless == "yes",
                    disable_images=command_line_config.chrome.disable_images == "yes",
                ),
                parser=ParserOptions(
                    max_records=command_line_config.parser.max_records,
                    delay_ms=command_line_config.parser.delay_between_clicks,
                    retry_on_network_errors=command_line_config.parser.retry_on_network_errors
                    == "yes",
                ),
                writer=WriterOptions(format="csv", encoding="utf-8-sig", deduplicate=True),
            )

            # Создаём и запускаем парсер
            parser = ParallelCityParser(
                cities=selected_cities,
                categories=CATEGORIES_93,
                output_dir=str(output_dir),
                config=config,
                max_workers=command_line_config.parallel.max_workers,
                timeout_per_url=1800,  # 30 минут для парсинга одной категории
            )

            def progress_callback(success: int, failed: int, filename: str) -> None:
                """Callback для обновления прогресса."""
                logger.info("Прогресс: успешно=%d, ошибок=%d, файл=%s", success, failed, filename)

            # Используем имя файла из аргументов или по умолчанию
            if args.output_path:
                output_path_obj = Path(args.output_path)
                if output_path_obj.suffix:
                    # Если указан файл с расширением, используем его
                    output_file = output_path_obj.name
                    # Пересоздаём output_dir для корректного пути
                    output_dir = output_path_obj.parent
                    if output_dir == Path("."):
                        output_dir = Path("output")
                    output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    # Если указана директория, используем имя по умолчанию
                    output_file = "omsk_all_categories.csv"
            else:
                output_file = "omsk_all_categories.csv"

            # Полный путь к выходному файлу
            output_file_path = output_dir / output_file

            result = parser.run(
                output_file=str(output_file_path), progress_callback=progress_callback
            )

            if result:
                logger.info("Парсинг успешно завершён")
                sys.exit(0)
            else:
                logger.error("Парсинг завершён с ошибками")
                sys.exit(1)

        query = args.query or "Организации"
        rubric = {"code": args.rubric} if args.rubric else None
        generated_urls = generate_city_urls(selected_cities, query, rubric)
        urls.extend(generated_urls)

    if not categories_mode:
        if not urls and not has_cities:
            logger.error("Не указан источник URL. Используйте -i/--url или --cities")
            sys.exit(1)

        output_path = getattr(args, "output_path", None)
        output_format = getattr(args, "format", None)

        if not output_path:
            logger.error("Не указан путь к выходному файлу. Используйте -o/--output-path")
            sys.exit(1)

        if not output_format:
            logger.error("Не указан формат выходного файла. Используйте -f/--format")
            sys.exit(1)

        try:
            cli_app(urls, output_path, output_format, command_line_config)
        except KeyboardInterrupt:
            logger.info("Работа приложения прервана пользователем (KeyboardInterrupt).")
            sys.exit(0)
        except FileNotFoundError as e:
            logger.error("Файл не найден: %s", e)
            sys.exit(1)
        except PermissionError as e:
            logger.error("Ошибка доступа к файлу: %s", e)
            sys.exit(1)
        except ValueError as e:
            logger.error("Ошибка валидации данных: %s", e)
            sys.exit(1)
        except TimeoutError as e:
            logger.error("Превышено время ожидания операции: %s", e)
            sys.exit(1)
        except ConnectionError as e:
            logger.error("Ошибка соединения: %s", e)
            sys.exit(1)
        except OSError as e:
            logger.error("Ошибка операционной системы: %s", e)
            sys.exit(1)
        except (sqlite3.Error, TypeError, RuntimeError) as e:
            logger.error("Критическая ошибка приложения: %s", e, exc_info=True)
            sys.exit(1)
        finally:
            logger.debug("Выполнение блока finally для очистки ресурсов...")
            try:
                cleanup_resources()
            except (sqlite3.Error, TypeError, RuntimeError) as cleanup_error:
                logger.error("Ошибка при очистке ресурсов в finally: %s", cleanup_error)
            logger.debug("Очистка ресурсов в блоке finally завершена")


__all__ = [
    "main",
    "cleanup_resources",
    "_get_signal_handler",
    "_get_signal_handler_cached",
    "_setup_signal_handlers",
    "Parser2GISTUI",
    "_tui_omsk_stub",
    "_tui_stub",
    "run_new_tui_omsk",
]
