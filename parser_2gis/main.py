"""
Модуль точки входа CLI для Parser2GIS.

Парсит аргументы командной строки, инициализирует конфигурацию
и запускает CLI приложение.
"""

from __future__ import annotations

import argparse
import gc
import ipaddress
import json
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, TypedDict
from urllib.parse import urlparse

import pydantic

from .cache import Cache
from .chrome.remote import ChromeRemote
from .common import generate_city_urls, report_from_validation_error, unwrap_dot_dict
from .config import Configuration
from .data.categories_93 import CATEGORIES_93
from .logger import log_parser_finish, log_parser_start, logger, setup_cli_logger
from .paths import data_path
from .pydantic_compat import get_model_dump
from .signal_handler import SignalHandler
from .version import version

# =============================================================================
# TYPE ALIASES И TYPEDDICT ДЛЯ УЛУЧШЕНИЯ ЧИТАЕМОСТИ
# =============================================================================


# Словарь города с обязательными ключами
class CityDict(TypedDict):
    """Словарь города для парсинга.

    Attributes:
        name: Название города (например, "Москва").
        url: URL для парсинга (например, "https://2gis.ru/moscow").
    """

    name: str
    url: str


# Словарь категории с обязательными ключами
class CategoryDict(TypedDict):
    """Словарь категории для парсинга.

    Attributes:
        id: Идентификатор категории (например, 93).
        name: Название категории (например, "Рестораны").
    """

    id: int
    name: str


# Type alias для списка городов
CitiesList = list[CityDict]


# Type alias для списка категорий
CategoriesList = list[CategoryDict]


# Type alias для результата валидации URL
UrlValidationResult = tuple[bool, str | None]


# Type alias для функции обработчика сигнала
SignalHandlerFunc = Callable[[int, Any], None]


# =============================================================================
# ОПЦИОНАЛЬНЫЕ ИМПОРТЫ (УПРОЩЁННАЯ ОБРАБОТКА)
# =============================================================================

# Критический импорт CLI модуля - обязателен для работы
try:
    from .cli import cli_app
except ImportError as e:
    logger.error("Не удалось импортировать CLI модуль: %s", e)
    logger.error("Убедитесь, что все зависимости установлены: pip install -e .")
    raise


# Опциональный импорт TUI модуля - создаём stub функцию если недоступен
def _tui_omsk_stub() -> None:
    """Stub функция для TUI когда модуль недоступен."""
    logger.error("TUI модуль (pytermgui) недоступен. Установите: pip install pytermgui")
    raise RuntimeError("TUI модуль недоступен")


try:
    from .tui_pytermgui import run_omsk_parallel as run_new_tui_omsk
except ImportError:
    # Модуль недоступен - используем stub функцию
    run_new_tui_omsk = _tui_omsk_stub
    logger.warning("TUI модуль (pytermgui) недоступен. Функция --tui-new-omsk будет недоступна")


def _validate_positive_int(value: int, min_val: int, max_val: int, arg_name: str) -> int:
    """Валидирует положительное целое число в заданном диапазоне.

    Args:
        value: Значение для валидации.
        min_val: Минимально допустимое значение (включительно).
        max_val: Максимально допустимое значение (включительно).
        arg_name: Имя аргумента для сообщения об ошибке.

    Returns:
        Валидированное значение.

    Raises:
        ValueError: Если значение выходит за пределы диапазона.

    Пример:
        >>> _validate_positive_int(5, 1, 100, "--parser.max-retries")
        5
        >>> _validate_positive_int(0, 1, 100, "--parser.max-retries")
        ValueError: --parser.max-retries должен быть от 1 до 100 (получено 0)
    """
    if not (min_val <= value <= max_val):
        raise ValueError(f"{arg_name} должен быть от {min_val} до {max_val} (получено {value})")
    return value


def _validate_url(url: str) -> UrlValidationResult:
    """Валидирует URL на корректность формата и безопасность.

    Args:
        url: URL для валидации.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если URL корректен и безопасен, False иначе.
        - error_message: Сообщение об ошибке или None если URL валиден.

    Примечание:
        Проверяет:
        - Схема (http или https)
        - Наличие сетевого расположения (netloc)
        - Общий формат URL
        - Блокировка localhost и внутренних IP адресов (127.x.x.x, 10.x.x.x, 192.168.x.x, 172.16-31.x.x)

    Исправление проблемы 10 (DNS rebinding защита):
        - Добавлена проверка hostname на соответствие IP после разрешения
        - Блокировка private IP диапазонов через socket.getaddrinfo
        - Проверка на localhost, loopback, private, link-local и multicast адреса
        - Предотвращение атак через домены указывающие на внутренние IP
    """
    try:
        result = urlparse(url)

        # Проверка схемы и netloc
        if not all([result.scheme in ("http", "https"), result.netloc]):
            return False, "URL должен начинаться с http:// или https:// и содержать домен"

        # Извлекаем хост для проверки на внутренние IP
        hostname = result.hostname
        if hostname is None:
            return False, "URL должен содержать домен"

        # Проверяем, не является ли хост localhost
        if hostname.lower() in ("localhost", "127.0.0.1"):
            return False, "Использование localhost запрещено"

        # Проверяем, не является ли хост IP адресом
        try:
            ip_addr = ipaddress.ip_address(hostname)
            # Проверяем на private и loopback адреса
            if ip_addr.is_private or ip_addr.is_loopback or ip_addr.is_link_local:
                return False, f"Использование внутренних IP адресов запрещено ({hostname})"
        except ValueError:
            # Это доменное имя, а не IP адрес - это нормально
            # НО требуется проверка на DNS rebinding атаку
            pass

        # Исправление 10: DNS rebinding защита
        # Разрешаем доменное имя и проверяем что оно не указывает на внутренний IP
        try:
            # Получаем все IP адреса для домена через socket.getaddrinfo
            # Это предотвращает DNS rebinding атаку когда злоумышленник использует
            # домен который резолвится во внутренний IP адрес
            addr_info_list = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)  # Только IPv4

            # Проверяем каждый полученный IP адрес
            for addr_info in addr_info_list:
                ip = addr_info[4][0]  # Извлекаем IP адрес из кортежа
                try:
                    ip_addr = ipaddress.ip_address(ip)

                    # Блокируем все категории опасных адресов:
                    # - is_private: 10.x.x.x, 172.16-31.x.x, 192.168.x.x
                    # - is_loopback: 127.x.x.x
                    # - is_link_local: 169.254.x.x (APIPA)
                    # - is_multicast: 224.0.0.0 - 239.255.255.255
                    if ip_addr.is_private or ip_addr.is_loopback or ip_addr.is_link_local or ip_addr.is_multicast:
                        return False, (
                            f"Домен {hostname} резолвится во внутренний IP ({ip}), " f"что запрещено (DNS rebinding защита)"
                        )

                except ValueError:
                    # Неверный формат IP - пропускаем
                    continue

        except socket.gaierror as dns_error:
            # Ошибка разрешения DNS
            return False, f"Не удалось разрешить DNS для {hostname}: {dns_error}"
        except socket.herror as host_error:
            # Ошибка хоста
            return False, f"Ошибка хоста для {hostname}: {host_error}"
        except OSError as os_error:
            # Другие ошибки сокета
            return False, f"Сетевая ошибка при проверке {hostname}: {os_error}"

        return True, None

    except (ValueError, TypeError) as e:
        # Ловим только ожидаемые исключения типизации/значений
        return False, f"Ошибка парсинга URL: {e}"


# Глобальный экземпляр обработчика сигналов
# Исправление проблемы 1.3: используем класс SignalHandler вместо глобальных переменных
_signal_handler_instance: Optional[SignalHandler] = None


def _get_signal_handler() -> SignalHandler:
    """
    Получает глобальный экземпляр SignalHandler.

    Returns:
        Экземпляр SignalHandler для обработки сигналов.

    Raises:
        RuntimeError: Если обработчик сигналов не инициализирован.
    """
    if _signal_handler_instance is None:
        raise RuntimeError("SignalHandler не инициализирован. Вызовите _setup_signal_handlers().")
    return _signal_handler_instance


def _setup_signal_handlers() -> None:
    """
    Устанавливает обработчики сигналов SIGINT и SIGTERM.

    Примечание:
        - SIGINT (Ctrl+C) - прерывание пользователем
        - SIGTERM - сигнал завершения от системы
        - Используется класс SignalHandler для инкапсуляции состояния
    """
    global _signal_handler_instance
    _signal_handler_instance = SignalHandler(cleanup_callback=cleanup_resources)
    _signal_handler_instance.setup()
    logger.debug("Обработчики сигналов SIGINT и SIGTERM установлены через SignalHandler")


def cleanup_resources() -> None:
    """Выполняет централизованную очистку ресурсов приложения.

    Примечание:
        - Закрывает активные соединения с браузером
        - Освобождает файловые дескрипторы
        - Очищает временные файлы
        - Сбрасывает кэши и буферы

    Важно:
        Функция безопасна - не вызывает исключений даже при частичных ошибках.
        Все ошибки логируются для последующего анализа.
    """
    try:
        # Очистка кэша Chrome
        logger.debug("Очистка кэша ресурсов...")

        # Закрытие активных соединений
        if hasattr(ChromeRemote, "_active_instances"):
            for instance in ChromeRemote._active_instances:
                try:
                    instance.close()
                except Exception as e:
                    logger.debug("Ошибка при закрытии соединения: %s", e)

        # Очистка кэша базы данных
        if hasattr(Cache, "close_all"):
            try:
                Cache.close_all()
            except Exception as e:
                logger.debug("Ошибка при закрытии кэша: %s", e)

        # Принудительный сборщик мусора
        gc.collect()

        logger.debug("Ресурсы успешно очищены")
    except ImportError as e:
        # Модули могут быть недоступны при раннем завершении
        logger.debug("Не удалось импортировать модули для очистки: %s", e)
    except Exception as e:
        # Ловим все исключения чтобы не прерывать очистку
        logger.debug("Ошибка при очистке ресурсов: %s", e)


def _load_cities_json(cities_path: Path) -> list[dict[str, Any]]:
    """Загружает JSON файл с городами с корректной обработкой ошибок.

    Args:
        cities_path: Путь к файлу cities.json.

    Returns:
        Список городов из JSON файла.

    Raises:
        FileNotFoundError: Если файл не найден.
        ValueError: Если файл повреждён или содержит некорректные данные.
        OSError: Если произошла ошибка операционной системы.
    """
    if not cities_path.is_file():
        logger.error("Файл городов не найден: %s", cities_path)
        raise FileNotFoundError(f"Файл {cities_path} не найден")

    try:
        # Используем контекстный менеджер для гарантии закрытия файла
        with open(cities_path, "r", encoding="utf-8") as f:
            all_cities = json.load(f)
        return all_cities
    except json.JSONDecodeError as e:
        logger.error("Ошибка парсинга JSON в файле городов: %s", e)
        raise ValueError(f"Некорректный формат JSON в файле городов: {e}")
    except OSError as e:
        logger.error("Ошибка ОС при чтении файла городов: %s", e)
        raise OSError(f"Не удалось прочитать файл городов: {e}")


class ArgumentHelpFormatter(argparse.HelpFormatter):
    """Форматировщик справки, добавляющий значения по умолчанию к описанию аргументов."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._default_config = get_model_dump(Configuration())

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


def parse_arguments(argv: Optional[list[str]] = None) -> tuple[argparse.Namespace, Configuration]:
    """Парсит аргументы командной строки.

    Args:
        argv: Список аргументов для парсинга (по умолчанию sys.argv[1:]).
              Используется для тестирования.

    Returns:
        Кортеж из аргументов командной строки и конфигурации.

    Raises:
        SystemExit: При отсутствии обязательных аргументов.
    """
    # Преобразуем флаги в нижний регистр для поддержки верхнего регистра
    # Создаём копию argv вместо модификации оригинального списка
    # Приводим к нижнему регистру только флаги (начинающиеся с -), не значения
    if argv is None:
        argv = sys.argv[1:]
        # Для sys.argv используем [1:] так как первый элемент это имя программы

    argv_copy = []
    for i, arg in enumerate(argv):
        if arg.startswith("-"):
            # Это флаг - приводим к нижнему регистру
            argv_copy.append(arg.lower())
        elif i > 0 and argv[i - 1].startswith("-"):
            # Это значение флага - приводим к нижнему регистру только если это похоже на yes/no
            # Не трогаем URL, пути и другие значения
            if arg.lower() in ("yes", "no", "true", "false"):
                argv_copy.append(arg.lower())
            else:
                argv_copy.append(arg)
        else:
            # Это позиционный аргумент или значение - не трогаем
            argv_copy.append(arg)

    patch_argparse_translations()  # Патчим переводы
    arg_parser = argparse.ArgumentParser(
        prog="Parser2GIS",
        description="Парсер данных сайта 2GIS",
        add_help=False,
        formatter_class=ArgumentHelpFormatter,
        argument_default=argparse.SUPPRESS,
    )

    main_parser_name = "Обязательные аргументы"

    main_parser = arg_parser.add_argument_group(main_parser_name)
    # URL не обязателен, если указаны --cities с --categories-mode
    main_parser.add_argument("-i", "--url", nargs="+", default=None, required=False, help="URL с выдачей")
    main_parser.add_argument(
        "--cities",
        nargs="+",
        default=None,
        metavar="CITY_CODE",
        help="Коды городов для парсинга (например: moscow spb kazan)",
    )
    main_parser.add_argument("--query", default=None, help="Поисковый запрос для генерации URL по городам")
    main_parser.add_argument("--rubric", default=None, help="Код рубрики для фильтрации результатов")
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
    browser_parser.add_argument("--chrome.headless", metavar="{yes/no}", help="Скрыть браузер")
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
    browser_parser.add_argument(
        "--chrome.startup-delay",
        type=float,
        metavar="{0,1,2,...}",
        help="Задержка запуска браузера в секундах (по умолчанию: 0)",
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
        type=int,
        metavar="{5,10,...}",
        help="Запуск сборщика мусора каждую N-ую страницу результатов (если сборщик включен)",
    )
    p_parser.add_argument(
        "--parser.max-records",
        type=int,
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
        type=int,
        metavar="{2,3,5,...}",
        help="Максимальное количество подряд пустых страниц перед остановкой (по умолчанию: 3)",
    )
    p_parser.add_argument(
        "--parser.delay-between-clicks",
        type=int,
        metavar="{0,100,...}",
        help="Задержка между кликами по записям (миллисекунд)",
    )
    p_parser.add_argument(
        "--parser.max-retries",
        type=int,
        metavar="{1,2,3,...}",
        help="Максимальное количество повторных попыток при ошибках сети (по умолчанию: 3)",
    )
    p_parser.add_argument(
        "--parser.retry-on-network-errors",
        metavar="{yes/no}",
        help="Выполнять повторные попытки при ошибках сети: 502, 503, 504, TimeoutError (по умолчанию: yes)",
    )
    p_parser.add_argument(
        "--parser.retry-delay-base",
        type=int,
        metavar="{1,2,3,...}",
        help="Базовая задержка между повторными попытками в секундах (по умолчанию: 1)",
    )
    p_parser.add_argument(
        "--parser.memory-threshold",
        type=int,
        metavar="{512,1024,2048,...}",
        help="Порог использования памяти в МБ для автоматической очистки (по умолчанию: 2048)",
    )
    p_parser.add_argument(
        "--parser.timeout",
        type=int,
        metavar="{1,2,3,...}",
        help="Таймаут на один URL в секундах (по умолчанию: 300)",
    )
    p_parser.add_argument(
        "--parser.max-workers",
        type=int,
        metavar="{1,2,3,...}",
        help="Максимальное количество одновременных работников (по умолчанию: 10)",
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
    other_parser.add_argument(
        "--tui-new",
        "--tui",  # Алиас для совместимости
        action="store_true",
        dest="tui_new",
        default=False,
        help="Запустить новый TUI интерфейс на pytermgui (алиас: --tui)",
    )
    other_parser.add_argument(
        "--tui-new-omsk",
        action="store_true",
        default=False,
        help="Запустить новый TUI интерфейс с автоматическим парсингом Омска (10 потоков, 93 категории)",
    )

    rest_parser = arg_parser.add_argument_group("Служебные аргументы")
    rest_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {version}",
        help="Показать версию программы и выйти",
    )
    rest_parser.add_argument("-h", "--help", action="help", help="Показать эту справку и выйти")

    args = arg_parser.parse_args(argv_copy)
    config_args = unwrap_dot_dict(vars(args))

    # Валидация числовых CLI аргументов перед инициализацией конфигурации
    # ПРИОРИТЕТ 1: Валидация аргументов парсера
    if hasattr(args, "parser.max_retries") and getattr(args, "parser.max_retries") is not None:
        try:
            _validate_positive_int(getattr(args, "parser.max_retries"), 1, 100, "--parser.max-retries")
        except ValueError as e:
            arg_parser.error(str(e))

    if hasattr(args, "parser.timeout") and getattr(args, "parser.timeout") is not None:
        try:
            _validate_positive_int(getattr(args, "parser.timeout"), 1, 3600, "--parser.timeout")
        except ValueError as e:
            arg_parser.error(str(e))

    if hasattr(args, "parser.max_workers") and getattr(args, "parser.max_workers") is not None:
        try:
            _validate_positive_int(getattr(args, "parser.max_workers"), 1, 50, "--parser.max-workers")
        except ValueError as e:
            arg_parser.error(str(e))

    # ПРИОРИТЕТ 2: Валидация аргументов Chrome
    if hasattr(args, "chrome.startup_delay") and getattr(args, "chrome.startup_delay") is not None:
        try:
            _validate_positive_int(int(getattr(args, "chrome.startup_delay")), 0, 60, "--chrome.startup-delay")
        except ValueError as e:
            arg_parser.error(str(e))

    # ПРИОРИТЕТ 3: Валидация других числовых аргументов
    if hasattr(args, "parser.gc_pages_interval") and getattr(args, "parser.gc_pages_interval") is not None:
        try:
            _validate_positive_int(getattr(args, "parser.gc_pages_interval"), 1, 1000, "--parser.gc-pages-interval")
        except ValueError as e:
            arg_parser.error(str(e))

    if hasattr(args, "parser.max_records") and getattr(args, "parser.max_records") is not None:
        try:
            _validate_positive_int(getattr(args, "parser.max_records"), 1, 1000000, "--parser.max-records")
        except ValueError as e:
            arg_parser.error(str(e))

    if hasattr(args, "parser.max_consecutive_empty_pages") and getattr(args, "parser.max_consecutive_empty_pages") is not None:
        try:
            _validate_positive_int(
                getattr(args, "parser.max_consecutive_empty_pages"), 1, 100, "--parser.max-consecutive-empty-pages"
            )
        except ValueError as e:
            arg_parser.error(str(e))

    if hasattr(args, "parser.delay_between_clicks") and getattr(args, "parser.delay_between_clicks") is not None:
        try:
            _validate_positive_int(getattr(args, "parser.delay_between_clicks"), 0, 10000, "--parser.delay-between-clicks")
        except ValueError as e:
            arg_parser.error(str(e))

    if hasattr(args, "parser.retry_delay_base") and getattr(args, "parser.retry_delay_base") is not None:
        try:
            _validate_positive_int(getattr(args, "parser.retry_delay_base"), 1, 60, "--parser.retry-delay-base")
        except ValueError as e:
            arg_parser.error(str(e))

    if hasattr(args, "parser.memory_threshold") and getattr(args, "parser.memory_threshold") is not None:
        try:
            _validate_positive_int(getattr(args, "parser.memory_threshold"), 256, 8192, "--parser.memory-threshold")
        except ValueError as e:
            arg_parser.error(str(e))

    if hasattr(args, "chrome.memory_limit") and getattr(args, "chrome.memory_limit") is not None:
        try:
            _validate_positive_int(getattr(args, "chrome.memory_limit"), 256, 16384, "--chrome.memory-limit")
        except ValueError as e:
            arg_parser.error(str(e))

    if hasattr(args, "writer.csv.columns_per_entity") and getattr(args, "writer.csv.columns_per_entity") is not None:
        try:
            _validate_positive_int(getattr(args, "writer.csv.columns_per_entity"), 1, 20, "--writer.csv.columns-per-entity")
        except ValueError as e:
            arg_parser.error(str(e))

    # Пропускаем валидацию URL для TUI режимов - там выбор происходит в интерфейсе
    is_tui_mode = getattr(args, "tui_new", False) or getattr(args, "tui_new_omsk", False)

    # Ручная валидация: требуется хотя бы один источник URL (кроме TUI режимов)
    if not is_tui_mode:
        has_cities = hasattr(args, "cities") and args.cities is not None
        has_url_source = args.url is not None or has_cities
        if not has_url_source:
            arg_parser.error("Требуется указать хотя бы один источник URL: -i/--url или --cities")

        # Валидация: --categories-mode требует --cities
        categories_mode = getattr(args, "categories_mode", False)
        if categories_mode and not has_cities:
            arg_parser.error("--categories-mode требует указания --cities")

    # Валидация URL если они указаны
    if args.url:
        invalid_urls = []
        url_errors = []
        for url in args.url:
            is_valid, error_msg = _validate_url(url)
            if not is_valid:
                invalid_urls.append(url)
                url_errors.append(f"{url} ({error_msg})")

        if invalid_urls:
            arg_parser.error(f"Некорректный формат URL: {'; '.join(url_errors)}.")

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
    # Если указан путь с расширением файла, используем его директорию
    # Если путь не существует или не имеет расширения, используем как директорию
    if output_path_obj.suffix and output_path_obj.parent.exists():
        return output_path_obj.parent
    # Если путь не существует, возвращаем родителя или сам путь если нет родителя
    return output_path_obj.parent if output_path_obj.parent != Path(".") else output_path_obj


def main() -> None:
    """Точка входа для CLI приложения.

    Парсит аргументы командной строки, обрабатывает различные режимы
    работы (TUI, CLI, параллельный парсинг) и запускает приложение.

    Примечание:
        Использует контекстный менеджер и signal handlers для гарантированной
        очистки ресурсов при KeyboardInterrupt и других исключениях.
    """
    # Запоминаем время старта
    start_time = time.time()
    start_datetime = datetime.now()

    # ВАЖНО: Устанавливаем обработчики сигналов для безопасной очистки ресурсов
    _setup_signal_handlers()

    # Парсим аргументы командной строки
    args, command_line_config = parse_arguments()

    # Обработка TUI интерфейсов
    if getattr(args, "tui_new_omsk", False):
        # Запуск нового TUI с автоматическим парсингом Омска
        if run_new_tui_omsk is None:
            logger.error("Новый TUI модуль (pytermgui) недоступен")
            sys.exit(1)
        run_new_tui_omsk()
        return

    if getattr(args, "tui_new", False):
        # Запуск нового TUI без автоматического парсинга
        from .tui_pytermgui import Parser2GISTUI

        app = Parser2GISTUI()
        app.run()
        return

    # Настраиваем логгер
    setup_cli_logger(command_line_config.log)

    # Логируем запуск парсера с подробной информацией
    _log_startup_info(args, command_line_config, start_datetime)

    # Обрабатываем аргументы городов
    urls = args.url or []

    # Проверяем режим парсинга по категориям и наличие городов
    categories_mode = getattr(args, "categories_mode", False)
    has_cities = hasattr(args, "cities") and args.cities is not None

    # Если указаны города, генерируем URL
    if has_cities:
        # Загружаем список городов с использованием контекстного менеджера
        cities_path = data_path() / "cities.json"
        try:
            all_cities = _load_cities_json(cities_path)
        except (FileNotFoundError, ValueError, OSError):
            # Ошибки уже залогированы в _load_cities_json
            raise

        # Фильтруем города по указанным кодам
        selected_cities = [city for city in all_cities if city["code"] in args.cities]

        if not selected_cities:
            available_cities = [c["code"] for c in all_cities]
            logger.error(
                "Города с кодами %s не найдены. Доступные города: %s",
                args.cities,
                available_cities[:10],  # Показываем первые 10 для краткости
            )
            raise ValueError(f"Города с кодами {args.cities} не найдены")

        if categories_mode:
            # Режим парсинга по 93 категориям
            # Определяем директорию для результатов
            output_dir = _get_output_dir(args.output_path)

            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error("Ошибка при создании директории output: %s", e)
                raise

            logger.info("Запуск параллельного парсинга по %d категориям", len(CATEGORIES_93))
            logger.info("Города: %s", [c["name"] for c in selected_cities])
            logger.info("Количество потоков: %d", getattr(args, "parallel_workers", 3))

            # Создаём и запускаем параллельный парсер с TUI
            # Приводим тип categories к list[dict] для совместимости с ParallelCityParser
            categories_list: list[dict] = CATEGORIES_93  # type: ignore[assignment]

            # Используем новый TUI интерфейс
            logger.info("🎨 Запуск TUI интерфейса...")

            output_file = str(output_dir / "merged_result.csv")

            # Запускаем новый TUI с параллельным парсингом
            from .tui_pytermgui.run_parallel import (
                run_parallel_with_tui as run_parallel_new_tui,
            )

            result = run_parallel_new_tui(
                cities=selected_cities,
                categories=categories_list,
                output_dir=str(output_dir),
                config=command_line_config,
                max_workers=getattr(args, "parallel_workers", 3),
                timeout_per_url=300,
                output_file=output_file,
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

        # Получаем output_path и format с проверкой на None
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
            # ВАЖНО: Signal handler уже вызвал cleanup_resources, но дублируем в finally
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
        except Exception as e:
            logger.error("Критическая ошибка приложения: %s", e, exc_info=True)
            sys.exit(1)
        finally:
            # ВАЖНО: Гарантированная очистка ресурсов при любом завершении
            # Выполняется даже при KeyboardInterrupt или sys.exit()
            # Signal handler уже мог вызвать cleanup_resources, но повторный вызов безопасен
            logger.debug("Выполнение блока finally для очистки ресурсов...")
            try:
                cleanup_resources()
            except Exception as cleanup_error:
                logger.error("Ошибка при очистке ресурсов в finally: %s", cleanup_error)
            logger.debug("Очистка ресурсов в блоке finally завершена")


def _log_startup_info(args: argparse.Namespace, config: Configuration, start_time: datetime) -> None:
    """
    Логирует подробную информацию о запуске парсера.

    Args:
        args: Аргументы командной строки.
        config: Конфигурация.
        start_time: Время запуска.
    """
    # Получаем формат и output_path с обработкой None
    format_value = getattr(args, "format", None)
    format_str = format_value.upper() if format_value else "CSV (по умолчанию)"

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
            "Удалить дубликаты": "Да" if config.writer.csv.remove_duplicates else "Нет",
        },
    }

    # Получаем количество URL с защитой от None
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
