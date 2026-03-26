"""Парсинг аргументов командной строки.

Модуль предоставляет функцию parse_arguments для разбора и валидации
аргументов командной строки приложения Parser2GIS.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from parser_2gis.cli.formatter import ArgumentHelpFormatter, patch_argparse_translations
from parser_2gis.cli.validator import ArgumentValidator
from parser_2gis.config import Configuration
from parser_2gis.utils import unwrap_dot_dict


def _normalize_argv(argv: list[str]) -> list[str]:
    """Нормализует аргументы командной строки: приводит флаги к нижнему регистру.

    Args:
        argv: Исходный список аргументов.

    Returns:
        Нормализованный список аргументов.

    Примечание:
        - Флаги (начинающиеся с -) приводятся к нижнему регистру
        - Значения флагов yes/no/true/false приводятся к нижнему регистру
        - URL, пути и другие значения не изменяются

    Raises:
        TypeError: Если argv не список/кортеж или содержит не строки.
    """
    if not isinstance(argv, (list, tuple)):
        raise TypeError(f"argv must be list or tuple, got {type(argv).__name__}")
    if not all(isinstance(arg, str) for arg in argv):
        raise TypeError("All argv elements must be strings")

    argv_copy = []
    for i, arg in enumerate(argv):
        if arg.startswith("-"):
            argv_copy.append(arg.lower())
        elif i > 0 and argv[i - 1].startswith("-"):
            if arg.lower() in ("yes", "no", "true", "false"):
                argv_copy.append(arg.lower())
            else:
                argv_copy.append(arg)
        else:
            argv_copy.append(arg)
    return argv_copy


def _create_argument_parser() -> argparse.ArgumentParser:
    """Создаёт и настраивает парсер аргументов командной строки.

    Returns:
        Настроенный экземпляр ArgumentParser со всеми группами аргументов.

    Примечание:
        Функция выделяет логику создания парсера из parse_arguments
        для уменьшения цикломатической сложности и улучшения читаемости.
    """
    patch_argparse_translations()
    arg_parser = argparse.ArgumentParser(
        prog="Parser2GIS",
        description="Парсер данных сайта 2GIS",
        add_help=False,
        formatter_class=ArgumentHelpFormatter,
        argument_default=argparse.SUPPRESS,
    )

    # Группа: Обязательные аргументы
    main_parser = arg_parser.add_argument_group("Обязательные аргументы")
    main_parser.add_argument(
        "-i", "--url", nargs="+", default=None, required=False, help="URL с выдачей"
    )
    main_parser.add_argument(
        "--cities",
        nargs="+",
        default=None,
        metavar="CITY_CODE",
        help="Коды городов для парсинга (например: moscow spb kazan)",
    )
    main_parser.add_argument(
        "--query", default=None, help="Поисковый запрос для генерации URL по городам"
    )
    main_parser.add_argument(
        "--rubric", default=None, help="Код рубрики для фильтрации результатов"
    )
    main_parser.add_argument(
        "--categories-mode",
        action="store_true",
        default=None,
        help="Режим парсинга по 93 категориям (только с --cities)",
    )
    main_parser.add_argument(
        "-o",
        "--output-path",
        metavar="PATH",
        default=None,
        required=False,
        help="Путь до результирующего файла",
    )
    main_parser.add_argument(
        "-f",
        "--format",
        metavar="{csv,xlsx,json}",
        choices=["csv", "xlsx", "json"],
        default=None,
        required=False,
        help="Формат результирующего файла",
    )

    # Группа: Аргументы браузера
    browser_parser = arg_parser.add_argument_group("Аргументы браузера")
    browser_parser.add_argument(
        "--chrome.binary_path", metavar="PATH", help="Путь до исполняемого файла браузера"
    )
    browser_parser.add_argument(
        "--chrome.disable-images", metavar="{yes,no}", help="Отключить изображения"
    )
    browser_parser.add_argument("--chrome.headless", metavar="{yes/no}", help="Скрыть браузер")
    browser_parser.add_argument(
        "--chrome.silent-browser",
        metavar="{yes/no}",
        help="Отключить отладочную информацию браузера",
    )
    browser_parser.add_argument(
        "--chrome.start-maximized", metavar="{yes/no}", help="Запустить развёрнутым"
    )
    browser_parser.add_argument(
        "--chrome.memory-limit", metavar="{4096,5120,...}", help="Лимит памяти браузера (МБ)"
    )
    browser_parser.add_argument(
        "--chrome.startup-delay",
        type=float,
        metavar="{0,1,2,...}",
        help="Задержка запуска браузера (секунды)",
    )

    # Группа: Аргументы CSV/XLSX
    csv_parser = arg_parser.add_argument_group("Аргументы CSV/XLSX")
    csv_parser.add_argument(
        "--writer.csv.add-rubrics", metavar="{yes/no}", help='Добавить колонку "Рубрики"'
    )
    csv_parser.add_argument(
        "--writer.csv.add-comments", metavar="{yes/no}", help="Добавлять комментарии к ячейкам"
    )
    csv_parser.add_argument(
        "--writer.csv.columns-per-entity",
        metavar="{1,2,3,...}",
        help="Количество колонок для множественных значений",
    )
    csv_parser.add_argument(
        "--writer.csv.remove-empty-columns", metavar="{yes/no}", help="Удалить пустые колонки"
    )
    csv_parser.add_argument(
        "--writer.csv.remove-duplicates", metavar="{yes/no}", help="Удалить дубликаты записей"
    )
    csv_parser.add_argument(
        "--writer.csv.join_char", metavar="{; ,% ,...}", help="Разделитель для комплексных значений"
    )

    # Группа: Аргументы парсера
    p_parser = arg_parser.add_argument_group("Аргументы парсера")
    p_parser.add_argument("--parser.use-gc", metavar="{yes/no}", help="Включить сборщик мусора")
    p_parser.add_argument(
        "--parser.gc-pages-interval",
        type=int,
        metavar="{5,10,...}",
        help="Запуск GC каждую N-ую страницу",
    )
    p_parser.add_argument(
        "--parser.max-records", type=int, metavar="{1000,2000,...}", help="Максимум записей с URL"
    )
    p_parser.add_argument(
        "--parser.skip-404-response", metavar="{yes/no}", help="Пропускать 404 ответы"
    )
    p_parser.add_argument(
        "--parser.stop-on-first-404", metavar="{yes/no}", help="Останавливать при первом 404"
    )
    p_parser.add_argument(
        "--parser.max-consecutive-empty-pages",
        type=int,
        metavar="{2,3,5,...}",
        help="Максимум пустых страниц подряд",
    )
    p_parser.add_argument(
        "--parser.delay-between-clicks",
        type=int,
        metavar="{0,100,...}",
        help="Задержка между кликами (мс)",
    )
    p_parser.add_argument(
        "--parser.max-retries", type=int, metavar="{1,2,3,...}", help="Максимум повторных попыток"
    )
    p_parser.add_argument(
        "--parser.retry-on-network-errors", metavar="{yes/no}", help="Повтор при ошибках сети"
    )
    p_parser.add_argument(
        "--parser.retry-delay-base",
        type=int,
        metavar="{1,2,3,...}",
        help="Базовая задержка повтора (сек)",
    )
    p_parser.add_argument(
        "--parser.memory-threshold",
        type=int,
        metavar="{512,1024,2048,...}",
        help="Порог памяти (МБ)",
    )
    p_parser.add_argument(
        "--parser.timeout", type=int, metavar="{1,2,3,...}", help="Таймаут на URL (сек)"
    )
    p_parser.add_argument(
        "--parser.max-workers", type=int, metavar="{1,2,3,...}", help="Максимум работников"
    )
    p_parser.add_argument(
        "--parallel.max-workers", type=int, default=10, help="Потоков для параллельного парсинга"
    )

    # Группа: Прочие аргументы
    other_parser = arg_parser.add_argument_group("Прочие аргументы")
    other_parser.add_argument(
        "--writer.verbose", metavar="{yes/no}", help="Отображать позиции при парсинге"
    )
    other_parser.add_argument(
        "--writer.encoding", metavar="{utf8,1251,...}", help="Кодировка файла"
    )
    other_parser.add_argument(
        "--tui-new",
        "--tui",
        action="store_true",
        dest="tui_new",
        default=False,
        help="Запустить TUI интерфейс",
    )
    other_parser.add_argument(
        "--tui-new-omsk", action="store_true", default=False, help="TUI с парсингом Омска"
    )

    # Группа: Служебные аргументы
    rest_parser = arg_parser.add_argument_group("Служебные аргументы")
    rest_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__import__('parser_2gis.version', fromlist=['version']).version}",
        help="Показать версию",
    )
    rest_parser.add_argument("-h", "--help", action="help", help="Показать справку")

    return arg_parser


def parse_arguments(argv: Optional[list[str]] = None) -> tuple[argparse.Namespace, Configuration]:
    """Парсит аргументы командной строки.

    Args:
        argv: Список аргументов (по умолчанию sys.argv[1:]).

    Returns:
        Кортеж из аргументов и конфигурации.

    Raises:
        SystemExit: При отсутствии обязательных аргументов.

    Примечание:
        Функция координирует этапы:
        1. _normalize_argv() - нормализация аргументов
        2. _create_argument_parser() - создание парсера
        3. ArgumentValidator.validate_numeric_arguments() - валидация чисел
        4. ArgumentValidator.validate_url_sources() - валидация URL
        5. ArgumentValidator.handle_configuration_validation() - конфигурация
    """
    if argv is None:
        argv = sys.argv[1:]

    argv_copy = _normalize_argv(argv)
    arg_parser = _create_argument_parser()
    args = arg_parser.parse_args(argv_copy)

    validator = ArgumentValidator()
    validator.validate_numeric_arguments(args, arg_parser)
    validator.validate_url_sources(args, arg_parser)
    validator.validate_cli_paths(args)

    config_args = unwrap_dot_dict(vars(args))
    config = validator.handle_configuration_validation(config_args, arg_parser)

    return args, config


__all__ = ["parse_arguments", "_normalize_argv", "_create_argument_parser"]
