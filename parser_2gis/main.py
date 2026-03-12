"""
Модуль точки входа CLI для Parser2GIS.

Парсит аргументы командной строки, инициализирует конфигурацию
и запускает CLI приложение.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pydantic

from .common import generate_city_urls, report_from_validation_error, unwrap_dot_dict
from .config import Configuration
from .data.categories_93 import CATEGORIES_93
from .logger import logger, log_parser_start, log_parser_finish, setup_cli_logger, get_tui_app
from .parallel_parser import ParallelCityParser
from .paths import data_path
from .version import version
from .cli import cli_app
from .tui import run_parallel_with_tui


class ArgumentHelpFormatter(argparse.HelpFormatter):
    """Форматировщик справки, добавляющий значения по умолчанию к описанию аргументов."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._default_config = Configuration().dict()

    def _get_default_value(self, dest: str) -> Any:
        if dest == "version":
            return argparse.SUPPRESS

        fields = dest.split(".")
        value = self._default_config
        try:
            for field in fields:
                value = value[field]
            return value
        except KeyError:
            return argparse.SUPPRESS

    def _get_help_string(self, action: argparse.Action) -> str | None:
        help_string = action.help
        if help_string:
            default_value = self._get_default_value(action.dest)
            if default_value != argparse.SUPPRESS:
                if isinstance(default_value, bool):
                    default_value = "yes" if default_value else "no"
                help_string += f" (по умолчанию: {default_value})"
        return help_string


def patch_argparse_translations() -> None:
    """Патчит gettext в argparse для перевода строк на русский язык."""
    custom_translations = {
        "usage: ": "Использование: ",
        "one of the arguments %s is required": "один из аргументов %s обязателен",
        "unrecognized arguments: %s": "нераспознанные аргументы: %s",
        "the following arguments are required: %s": "следующие аргументы обязательны: %s",
        "%(prog)s: error: %(message)s\n": "%(prog)s: ошибка: %(message)s\n",
        "invalid choice: %(value)r (choose from %(choices)s)": "неверная опция: %(value)r (выберите одну из %(choices)s)",
    }

    orig_gettext = argparse._  # type: ignore[attr-defined]

    def gettext(message: str) -> str:
        if message in custom_translations:
            return custom_translations[message]
        return orig_gettext(message)

    argparse._ = gettext  # type: ignore[attr-defined]

    # Заменяем хардкодную строку `argument` в классе ArgumentError
    # Этот баг был исправлен только 6 мая 2022 https://github.com/python/cpython/pull/17169
    def argument_error__str__(self: argparse.ArgumentError) -> str:
        if self.argument_name is None:
            format_str = "%(message)s"
        else:
            format_str = "аргумент %(argument_name)s: %(message)s"
        return format_str % dict(message=self.message, argument_name=self.argument_name)

    argparse.ArgumentError.__str__ = argument_error__str__  # type: ignore


def parse_arguments() -> tuple[argparse.Namespace, Configuration]:
    """Парсит аргументы командной строки.

    Returns:
        Кортеж из аргументов командной строки и конфигурации.
    """
    # Преобразуем аргументы в нижний регистр для поддержки верхнего регистра
    # Создаём копию sys.argv вместо модификации оригинального списка
    argv_copy = [arg.lower() if arg.startswith("-") else arg for arg in sys.argv]

    patch_argparse_translations()  # Патчим переводы
    arg_parser = argparse.ArgumentParser(
        "Parser2GIS",
        description="Парсер данных сайта 2GIS",
        add_help=False,
        formatter_class=ArgumentHelpFormatter,
        argument_default=argparse.SUPPRESS,
    )

    main_parser_name = "Обязательные аргументы"

    main_parser = arg_parser.add_argument_group(main_parser_name)
    # URL не обязателен, если указаны --cities с --categories-mode
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

    browser_parser = arg_parser.add_argument_group("Аргументы браузера")
    browser_parser.add_argument(
        "--chrome.binary_path",
        metavar="PATH",
        help="Путь до исполняемого файла браузера. Если не указан, то определяется автоматически",
    )
    browser_parser.add_argument(
        "--chrome.disable-images",
        metavar="{yes,no}",
        help="Отключить изображения в браузере",
    )
    browser_parser.add_argument(
        "--chrome.headless", metavar="{yes/no}", help="Скрыть браузер"
    )
    browser_parser.add_argument(
        "--chrome.silent-browser",
        metavar="{yes/no}",
        help="Отключить отладочную информацию браузера",
    )
    browser_parser.add_argument(
        "--chrome.start-maximized",
        metavar="{yes/no}",
        help="Запустить окно браузера развёрнутым",
    )
    browser_parser.add_argument(
        "--chrome.memory-limit",
        metavar="{4096,5120,...}",
        help="Лимит оперативной памяти браузера (мегабайт)",
    )

    csv_parser = arg_parser.add_argument_group("Аргументы CSV/XLSX")
    csv_parser.add_argument(
        "--writer.csv.add-rubrics",
        metavar="{yes/no}",
        help='Добавить колонку "Рубрики"',
    )
    csv_parser.add_argument(
        "--writer.csv.add-comments",
        metavar="{yes/no}",
        help="Добавлять комментарии к ячейкам Телефон, E-Mail, и т.д.",
    )
    csv_parser.add_argument(
        "--writer.csv.columns-per-entity",
        metavar="{1,2,3,...}",
        help="Количество колонок для результата с несколькими возможными значениями: Телефон_1, Телефон_2, и т.д.",
    )
    csv_parser.add_argument(
        "--writer.csv.remove-empty-columns",
        metavar="{yes/no}",
        help="Удалить пустые колонки по завершению работы парсера",
    )
    csv_parser.add_argument(
        "--writer.csv.remove-duplicates",
        metavar="{yes/no}",
        help="Удалить повторяющиеся записи по завершению работы парсера",
    )
    csv_parser.add_argument(
        "--writer.csv.join_char",
        metavar="{; ,% ,...}",
        help="Разделитель для комплексных значений ячеек Рубрики, Часы работы",
    )

    p_parser = arg_parser.add_argument_group("Аргументы парсера")
    p_parser.add_argument(
        "--parser.use-gc",
        metavar="{yes/no}",
        help="Включить сборщик мусора - сдерживает быстрое заполнение RAM, уменьшает скорость парсинга",
    )
    p_parser.add_argument(
        "--parser.gc-pages-interval",
        metavar="{5,10,...}",
        help="Запуск сборщика мусора каждую N-ую страницу результатов (если сборщик включен)",
    )
    p_parser.add_argument(
        "--parser.max-records",
        metavar="{1000,2000,...}",
        help="Максимальное количество спарсенных записей с одного URL",
    )
    p_parser.add_argument(
        "--parser.skip-404-response",
        metavar="{yes/no}",
        help='Пропускать ссылки вернувшие сообщение "Точных совпадений нет / Не найдено"',
    )
    p_parser.add_argument(
        "--parser.stop-on-first-404",
        metavar="{yes/no}",
        help="Останавливать парсинг немедленно при первом 404 ответе (по умолчанию: no)",
    )
    p_parser.add_argument(
        "--parser.max-consecutive-empty-pages",
        metavar="{2,3,5,...}",
        help="Максимальное количество подряд пустых страниц перед остановкой (по умолчанию: 3)",
    )
    p_parser.add_argument(
        "--parser.delay-between-clicks",
        metavar="{0,100,...}",
        help="Задержка между кликами по записям (миллисекунд)",
    )
    p_parser.add_argument(
        "--parallel-workers",
        type=int,
        default=10,
        help="Количество одновременных потоков для параллельного парсинга (по умолчанию: 10)",
    )

    other_parser = arg_parser.add_argument_group("Прочие аргументы")
    other_parser.add_argument(
        "--writer.verbose",
        metavar="{yes/no}",
        help="Отображать наименования позиций во время парсинга",
    )
    other_parser.add_argument(
        "--writer.encoding",
        metavar="{utf8,1251,...}",
        help="Кодировка результирующего файла",
    )

    rest_parser = arg_parser.add_argument_group("Служебные аргументы")
    rest_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {version}",
        help="Показать версию программы и выйти",
    )
    rest_parser.add_argument(
        "-h", "--help", action="help", help="Показать эту справку и выйти"
    )

    args = arg_parser.parse_args(argv_copy[1:])
    config_args = unwrap_dot_dict(vars(args))

    # Ручная валидация: требуется хотя бы один источник URL
    has_cities = hasattr(args, "cities") and args.cities is not None
    has_url_source = args.url is not None or has_cities
    if not has_url_source:
        arg_parser.error(
            "Требуется указать хотя бы один источник URL: -i/--url или --cities"
        )

    # Валидация: --categories-mode требует --cities
    categories_mode = getattr(args, "categories_mode", False)
    if categories_mode and not has_cities:
        arg_parser.error("--categories-mode требует указания --cities")

    try:
        # Инициализируем конфигурацию аргументами командной строки
        config = Configuration(**config_args)
    except pydantic.ValidationError as e:
        errors = []
        errors_report = report_from_validation_error(e, config_args)
        for path, description in errors_report.items():
            arg = description["invalid_value"]
            error_msg = description["error_message"]
            errors.append(f"аргумент --{path} {arg} ({error_msg})")

        arg_parser.error(", ".join(errors))

    return args, config


def main() -> None:
    """Точка входа."""
    # Запоминаем время старта
    start_time = time.time()
    start_datetime = datetime.now()

    # Парсим аргументы командной строки
    args, command_line_config = parse_arguments()

    # Настраиваем логгер
    setup_cli_logger(command_line_config.log)

    # Логируем запуск парсера с подробной информацией
    _log_startup_info(args, command_line_config, start_datetime)

    # Обрабатываем аргументы городов
    urls = args.url or []

    # Проверяем режим парсинга по категориям
    categories_mode = getattr(args, "categories_mode", False)

    # Выносим проверку наличия городов в переменную для избежания дублирования
    has_cities = hasattr(args, "cities") and args.cities is not None

    # Если указаны города, генерируем URL
    if has_cities:
        # Загружаем список городов
        cities_path = data_path() / "cities.json"
        if not cities_path.is_file():
            raise FileNotFoundError(f"Файл {cities_path} не найден")

        with open(cities_path, "r", encoding="utf-8") as f:
            all_cities = json.load(f)

        # Фильтруем города по указанным кодам
        selected_cities = [city for city in all_cities if city["code"] in args.cities]

        if not selected_cities:
            raise ValueError(f"Города с кодами {args.cities} не найдены")

        if categories_mode:
            # Режим парсинга по 93 категориям
            # Используем output_path как директорию (если указан) или 'output' по умолчанию
            output_path_value = getattr(args, 'output_path', None)
            if output_path_value is not None:
                # Если указан путь к файлу, используем его директорию
                output_path_obj = Path(output_path_value)
                if output_path_obj.suffix:  # Это файл, а не директория
                    output_dir = output_path_obj.parent
                else:
                    output_dir = output_path_obj
            else:
                output_dir = Path("output")

            output_dir.mkdir(parents=True, exist_ok=True)

            logger.info(
                "Запуск параллельного парсинга по %d категориям", len(CATEGORIES_93)
            )
            logger.info("Города: %s", [c["name"] for c in selected_cities])
            logger.info("Количество потоков: %d", getattr(args, "parallel_workers", 3))

            # Создаём и запускаем параллельный парсер с TUI
            # Приводим тип categories к list[dict] для совместимости с ParallelCityParser
            categories_list: list[dict] = CATEGORIES_93  # type: ignore[assignment]
            
            # Используем TUI интерфейс вместо обычного логирования
            logger.info("🎨 Запуск TUI интерфейса...")
            
            output_file = str(output_dir / "merged_result.csv")
            result = run_parallel_with_tui(
                cities=selected_cities,
                categories=categories_list,
                output_dir=str(output_dir),
                config=command_line_config,
                max_workers=getattr(args, "parallel_workers", 3),
                output_file=output_file,
                version=version,
            )

            # Вычисляем длительность
            duration = time.time() - start_time
            duration_str = f"{duration:.2f} сек."

            if result:
                logger.info("Параллельный парсинг завершён успешно!")
                logger.info("Результаты сохранены в папку: %s", output_dir.absolute())
                log_parser_finish(
                    success=True,
                    stats={
                        "Городов": len(selected_cities),
                        "Категорий": len(CATEGORIES_93),
                        "Всего URL": len(selected_cities) * len(CATEGORIES_93),
                    },
                    duration=duration_str,
                )
            else:
                logger.error("Параллельный парсинг завершён с ошибками")
                log_parser_finish(success=False, duration=duration_str)

            return
        else:
            # Обычный режим - генерируем URL по городам
            query = args.query or "Организации"
            rubric = {"code": args.rubric} if args.rubric else None

            # Генерируем URL
            generated_urls = generate_city_urls(selected_cities, query, rubric)
            urls.extend(generated_urls)

    # Проверяем, что указаны обязательные параметры
    # В режиме categories_mode парсинг уже завершён выше, пропускаем проверки
    if not categories_mode:
        # Обычный режим - требуем все обязательные параметры
        if not urls and not has_cities:
            logger.error("Не указан источник URL. Используйте -i/--url или --cities")
            sys.exit(1)

        if not args.output_path:
            logger.error(
                "Не указан путь к выходному файлу. Используйте -o/--output-path"
            )
            sys.exit(1)

        if not args.format:
            logger.error("Не указан формат выходного файла. Используйте -f/--format")
            sys.exit(1)

        try:
            cli_app(urls, args.output_path, args.format, command_line_config)
        except KeyboardInterrupt:
            logger.info("Работа приложения прервана пользователем.")
        except Exception as e:
            logger.error("Критическая ошибка приложения: %s", e, exc_info=True)
            raise


def _log_startup_info(args: argparse.Namespace, config: Configuration, start_time: datetime) -> None:
    """
    Логирует подробную информацию о запуске парсера.

    Args:
        args: Аргументы командной строки.
        config: Конфигурация.
        start_time: Время запуска.
    """
    # Получаем формат, обрабатывая случай None (для categories-mode)
    format_value = getattr(args, "format", None)
    format_str = format_value.upper() if format_value else "CSV (по умолчанию)"

    # Получаем output_path, обрабатывая случай None
    output_path_value = getattr(args, "output_path", None)
    output_path_str = str(output_path_value) if output_path_value else "output/ (по умолчанию)"

    # Формируем сводку конфигурации
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
            "Удалить дубликаты": "Да" if config.writer.csv_remove_duplicates else "Нет",
        },
    }

    # Получаем количество URL
    urls_count = len(args.url) if args.url else 0
    if hasattr(args, "cities") and args.cities:
        if getattr(args, "categories_mode", False):
            urls_count = len(args.cities) * len(CATEGORIES_93)
        else:
            urls_count = len(args.cities)

    # Логируем запуск
    log_parser_start(
        version=version,
        urls_count=urls_count,
        output_path=output_path_str,
        format=format_str,
        config_summary=config_summary,
    )

    logger.info("Время запуска: %s", start_time.strftime("%Y-%m-%d %H:%M:%S"))
