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
from parser_2gis.cli.launcher import run_tui_application
from parser_2gis.config import Configuration
from parser_2gis.logger import log_parser_start, logger, setup_cli_logger
from parser_2gis.parser.options import ParserOptions
from parser_2gis.resources import CATEGORIES_93
from parser_2gis.version import version


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

    config_summary = format_config_summary(config, args)

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

    ISSUE-045: Использует общую функцию run_tui_application для устранения дублирования.
    """
    start_datetime = datetime.now()
    args, command_line_config = parse_arguments()

    # Обработка TUI интерфейсов - ISSUE-045: используем общую функцию
    if getattr(args, "tui_new_omsk", False):
        exit_code = run_tui_application(tui_type="omsk")
        if exit_code != 0:
            sys.exit(exit_code)
        return

    if getattr(args, "tui_new", False):
        exit_code = run_tui_application(tui_type="main")
        if exit_code != 0:
            sys.exit(exit_code)
        return

    setup_cli_logger(command_line_config.log)
    _log_startup_info(args, command_line_config, start_datetime)

    # Создаём лаунчер и запускаем приложение
    # Локальный импорт для избежания циклической зависимости
    from parser_2gis.cli.launcher import ApplicationLauncher

    options = ParserOptions()
    launcher = ApplicationLauncher(config=command_line_config, options=options)

    try:
        exit_code = launcher.launch(args)
    except (MemoryError, OSError, RuntimeError) as e:
        logger.critical("Критическая ошибка при запуске приложения: %s", e, exc_info=True)
        sys.exit(1)
    except (TypeError, ValueError) as e:
        logger.error("Ошибка конфигурации при запуске приложения: %s", e, exc_info=True)
        sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Приложение прервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error("Непредвиденная ошибка при запуске приложения: %s", e, exc_info=True)
        sys.exit(1)

    sys.exit(exit_code)


__all__ = ["main"]
