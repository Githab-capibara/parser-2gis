from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pydantic

from .common import GUI_ENABLED, generate_city_urls, report_from_validation_error, unwrap_dot_dict, url_query_encode
from .config import Configuration
from .paths import data_path
from .version import version
from .cli import cli_app

if TYPE_CHECKING:
    from .gui import gui_app


class ArgumentHelpFormatter(argparse.HelpFormatter):
    """Форматировщик справки, добавляющий значения по умолчанию к описанию аргументов."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._default_config = Configuration().dict()

    def _get_default_value(self, dest: str) -> Any:
        if dest == 'version':
            return argparse.SUPPRESS

        fields = dest.split('.')
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
                    default_value = 'yes' if default_value else 'no'
                help_string += f' (по умолчанию: {default_value})'
        return help_string


def patch_argparse_translations() -> None:
    """Патчит gettext в argparse для перевода строк на русский язык."""
    custom_translations = {
        'usage: ': 'Использование: ',
        'one of the arguments %s is required': 'один из аргументов %s обязателен',
        'unrecognized arguments: %s': 'нераспознанные аргументы: %s',
        'the following arguments are required: %s': 'следующие аргументы обязательны: %s',
        '%(prog)s: error: %(message)s\n': '%(prog)s: ошибка: %(message)s\n',
        'invalid choice: %(value)r (choose from %(choices)s)': 'неверная опция: %(value)r (выберите одну из %(choices)s)'
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
            format_str = '%(message)s'
        else:
            format_str = 'аргумент %(argument_name)s: %(message)s'
        return format_str % dict(message=self.message,
                                 argument_name=self.argument_name)

    argparse.ArgumentError.__str__ = argument_error__str__  # type: ignore


def parse_arguments() -> tuple[argparse.Namespace, Configuration]:
    """Парсит аргументы в зависимости от доступности GUI.

    Returns:
        Кортеж из аргументов командной строки и конфигурации.
    """
    patch_argparse_translations()  # Патчим переводы
    arg_parser = argparse.ArgumentParser('Parser2GIS', description='Парсер данных сайта 2GIS', add_help=False,
                                         formatter_class=ArgumentHelpFormatter, argument_default=argparse.SUPPRESS)

    if GUI_ENABLED:
        main_parser_name = 'Основные аргументы'
        main_parser_required = False
    else:
        main_parser_name = 'Обязательные аргументы'
        main_parser_required = True

    main_parser = arg_parser.add_argument_group(main_parser_name)
    main_parser.add_argument('-i', '--url', nargs='+', default=None, required=main_parser_required, help='URL с выдачей')
    main_parser.add_argument('--cities', nargs='+', default=None, metavar='CITY_CODE', help='Коды городов для парсинга (например: moscow spb kazan)')
    main_parser.add_argument('--query', default=None, help='Поисковый запрос для генерации URL по городам')
    main_parser.add_argument('--rubric', default=None, help='Код рубрики для фильтрации результатов')
    main_parser.add_argument('-o', '--output-path', metavar='PATH', default=None, required=main_parser_required, help='Путь до результирующего файла')
    main_parser.add_argument('-f', '--format', metavar='{csv,xlsx,json}', choices=['csv', 'xlsx', 'json'], default=None, required=main_parser_required, help='Формат результирующего файла')

    browser_parser = arg_parser.add_argument_group('Аргументы браузера')
    browser_parser.add_argument('--chrome.binary_path', metavar='PATH', help='Путь до исполняемого файла браузера. Если не указан, то определяется автоматически')
    browser_parser.add_argument('--chrome.disable-images', metavar='{yes,no}', help='Отключить изображения в браузере')
    browser_parser.add_argument('--chrome.headless', metavar='{yes/no}', help='Скрыть браузер')
    browser_parser.add_argument('--chrome.silent-browser', metavar='{yes/no}', help='Отключить отладочную информацию браузера')
    browser_parser.add_argument('--chrome.start-maximized', metavar='{yes/no}', help='Запустить окно браузера развёрнутым')
    browser_parser.add_argument('--chrome.memory-limit', metavar='{4096,5120,...}', help='Лимит оперативной памяти браузера (мегабайт)')

    csv_parser = arg_parser.add_argument_group('Аргументы CSV/XLSX')
    csv_parser.add_argument('--writer.csv.add-rubrics', metavar='{yes/no}', help='Добавить колонку "Рубрики"')
    csv_parser.add_argument('--writer.csv.add-comments', metavar='{yes/no}', help='Добавлять комментарии к ячейкам Телефон, E-Mail, и т.д.')
    csv_parser.add_argument('--writer.csv.columns-per-entity', metavar='{1,2,3,...}', help='Количество колонок для результата с несколькими возможными значениями: Телефон_1, Телефон_2, и т.д.')
    csv_parser.add_argument('--writer.csv.remove-empty-columns', metavar='{yes/no}', help='Удалить пустые колонки по завершению работы парсера')
    csv_parser.add_argument('--writer.csv.remove-duplicates', metavar='{yes/no}', help='Удалить повторяющиеся записи по завершению работы парсера')
    csv_parser.add_argument('--writer.csv.join_char', metavar='{; ,% ,...}', help='Разделитель для комплексных значений ячеек Рубрики, Часы работы')

    p_parser = arg_parser.add_argument_group('Аргументы парсера')
    p_parser.add_argument('--parser.use-gc', metavar='{yes/no}', help='Включить сборщик мусора - сдерживает быстрое заполнение RAM, уменьшает скорость парсинга')
    p_parser.add_argument('--parser.gc-pages-interval', metavar='{5,10,...}', help='Запуск сборщика мусора каждую N-ую страницу результатов (если сборщик включен)')
    p_parser.add_argument('--parser.max-records', metavar='{1000,2000,...}', help='Максимальное количество спарсенных записей с одного URL')
    p_parser.add_argument('--parser.skip-404-response', metavar='{yes/no}', help='Пропускать ссылки вернувшие сообщение "Точных совпадений нет / Не найдено"')
    p_parser.add_argument('--parser.delay_between_clicks', metavar='{0,100,...}', help='Задержка между кликами по записям (миллисекунд)')

    other_parser = arg_parser.add_argument_group('Прочие аргументы')
    other_parser.add_argument('--writer.verbose', metavar='{yes/no}', help='Отображать наименования позиций во время парсинга')
    other_parser.add_argument('--writer.encoding', metavar='{utf8,1251,...}', help='Кодировка результирующего файла')

    rest_parser = arg_parser.add_argument_group('Служебные аргументы')
    rest_parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {version}', help='Показать версию программы и выйти')
    rest_parser.add_argument('-h', '--help', action='help', help='Показать эту справку и выйти')

    args = arg_parser.parse_args()
    config_args = unwrap_dot_dict(vars(args))

    try:
        # Инициализируем конфигурацию аргументами командной строки
        config = Configuration(**config_args)
    except pydantic.ValidationError as e:
        errors = []
        errors_report = report_from_validation_error(e, config_args)
        for path, description in errors_report.items():
            arg = description['invalid_value']
            error_msg = description['error_message']
            errors.append(f'аргумент --{path} {arg} ({error_msg})')

        arg_parser.error(', '.join(errors))

    return args, config


def main() -> None:
    """Точка входа."""
    # Парсим аргументы командной строки
    args, command_line_config = parse_arguments()

    # Обрабатываем аргументы городов
    urls = list(args.url) if args.url else []

    # Если указаны города, генерируем URL
    if hasattr(args, 'cities') and args.cities:
        # Загружаем список городов
        cities_path = data_path() / 'cities.json'
        if not cities_path.is_file():
            raise FileNotFoundError(f'Файл {cities_path} не найден')

        with open(cities_path, 'r', encoding='utf-8') as f:
            all_cities = json.load(f)

        # Фильтруем города по указанным кодам
        selected_cities = [city for city in all_cities if city['code'] in args.cities]

        if not selected_cities:
            raise ValueError(f'Города с кодами {args.cities} не найдены')

        # Получаем запрос и рубрику
        query = args.query or 'Организации'
        rubric = {'code': args.rubric} if args.rubric else None

        # Генерируем URL
        generated_urls = generate_city_urls(selected_cities, query, rubric)
        urls.extend(generated_urls)

    # Определяем режим запуска: GUI или CLI
    # GUI запускается, если не указаны все обязательные аргументы (URL/cities, output-path, format)
    is_gui_mode = (
        (args.url is None and (not hasattr(args, 'cities') or not args.cities)) or
        args.output_path is None or
        args.format is None
    )

    if is_gui_mode:
        # Загружаем пользовательскую конфигурацию и объединяем с созданной из аргументов
        user_config = Configuration.load_config(auto_create=True)
        user_config.merge_with(command_line_config)
        config = user_config
        # Импортируем gui_app только при необходимости
        from .gui import gui_app
        app = gui_app
    else:
        config = command_line_config
        app = cli_app

    app(urls, args.output_path, args.format, config)
