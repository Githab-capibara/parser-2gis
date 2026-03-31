"""Точка входа CLI приложения Parser2GIS.

Модуль предоставляет функцию main() для запуска приложения.
Минимальная логика: parse args → validate → run.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any

from parser_2gis.cli.arguments import parse_arguments
from parser_2gis.cli.formatter import format_config_summary
from parser_2gis.cli.launcher import ApplicationLauncher
from parser_2gis.config import Configuration
from parser_2gis.resources import CATEGORIES_93
from parser_2gis.logger import log_parser_start, logger, setup_cli_logger
from parser_2gis.parser.options import ParserOptions
from parser_2gis.version import version

# Опциональный импорт TUI модуля
try:
    from parser_2gis.tui_textual import Parser2GISTUI
    from parser_2gis.tui_textual import run_tui as run_new_tui_omsk
except ImportError:
    run_new_tui_omsk = None  # type: ignore[assignment]
    Parser2GISTUI = None  # type: ignore[assignment]
    logger.warning("TUI модуль (textual) недоступен. TUI функции будут недоступны")

# Backward совместимость для тестов
from parser_2gis.chrome.remote import ChromeRemote  # noqa: F401


def cleanup_resources() -> None:
    """Выполняет централизованную очистку ресурсов приложения.

    Backward совместимость для тестов.
    Обрабатывает AttributeError, MemoryError, KeyboardInterrupt.
    """
    # Для backward совместимости создаём временный лаунчер
    import gc

    from parser_2gis.cache import CacheManager
    from parser_2gis.logger import logger
    from parser_2gis.utils.paths import cache_path

    try:
        logger.debug("Очистка кэша ресурсов...")

        # Очистка ChromeRemote
        try:
            if hasattr(ChromeRemote, "_active_instances"):
                for instance in ChromeRemote._active_instances:
                    try:
                        if instance is not None:
                            instance.stop()
                    except (AttributeError, RuntimeError, TypeError, ValueError) as e:
                        logger.debug(
                            "Подавлено исключение при остановке экземпляра ChromeRemote: %s", e
                        )
        except (AttributeError, TypeError) as chrome_iter_error:
            logger.error("Ошибка итерации _active_instances: %s", chrome_iter_error)

        # Очистка кэша
        try:
            cache = CacheManager(cache_path())
            cache.close()
        except (AttributeError, RuntimeError, TypeError, ValueError) as cache_error:
            logger.error("Ошибка при закрытии кэша: %s", cache_error)

        # Сборка мусора
        try:
            gc.collect()
        except (MemoryError, RuntimeError) as gc_error:
            logger.error("Ошибка gc.collect(): %s", gc_error)

        logger.info("Очистка ресурсов завершена")

    except MemoryError as e:
        logger.critical("Критическая ошибка: нехватка памяти при очистке ресурсов: %s", e)
    except KeyboardInterrupt:
        logger.warning("Очистка ресурсов прервана пользователем")
    except Exception as e:
        logger.error("Непредвиденная ошибка при очистке ресурсов: %s", e)


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

    config_summary = format_config_summary(config)

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


def main() -> None:
    """Точка входа для CLI приложения.

    Парсит аргументы командной строки, обрабатывает различные режимы
    работы (TUI, CLI, параллельный парсинг) и запускает приложение.
    """
    start_datetime = datetime.now()
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

    # Создаём лаунчер и запускаем приложение
    options = ParserOptions()
    launcher = ApplicationLauncher(config=command_line_config, options=options)

    exit_code = launcher.launch(args)
    sys.exit(exit_code)


__all__ = ["main", "ApplicationLauncher", "Parser2GISTUI", "run_new_tui_omsk", "cleanup_resources"]
