"""Валидатор аргументов командной строки.

Модуль предоставляет класс ArgumentValidator для комплексной валидации
аргументов командной строки перед использованием в приложении.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

import pydantic

from parser_2gis.config import Configuration
from parser_2gis.utils import report_from_validation_error
from parser_2gis.utils.path_utils import validate_path_safety
from parser_2gis.validation import validate_positive_int, validate_url


@dataclass
class ValidationArgument:
    """Конфигурация для валидации CLI аргумента.

    Attributes:
        args: Аргументы командной строки.
        arg_parser: Парсер аргументов для вывода ошибок.
        attr_name: Имя атрибута для проверки.
        min_val: Минимально допустимое значение.
        max_val: Максимально допустимое значение.
        error_name: Имя аргумента для сообщения об ошибке.
        convert_to_int: Конвертировать значение в int перед валидацией.
    """

    args: argparse.Namespace
    arg_parser: argparse.ArgumentParser
    attr_name: str
    min_val: int
    max_val: float
    error_name: str
    convert_to_int: bool = False


class ArgumentValidator:
    """Класс для валидации аргументов командной строки.

    Предоставляет методы для валидации:
    - Числовых аргументов (диапазоны значений)
    - URL адресов
    - Путей к файлам
    - Источников URL
    - Конфигурации приложения

    Example:
        >>> validator = ArgumentValidator()
        >>> validator.validate_numeric_arguments(args, parser)
        >>> validator.validate_urls(args, parser)
    """

    def validate_cli_argument(
        self,
        args: argparse.Namespace,
        arg_parser: argparse.ArgumentParser,
        attr_name: str,
        min_val: int,
        max_val: float,
        error_name: str,
        convert_to_int: bool = False,
    ) -> None:
        """Валидирует CLI аргумент и выводит ошибку при некорректном значении.

        Args:
            args: Аргументы командной строки.
            arg_parser: Парсер аргументов для вывода ошибок.
            attr_name: Имя атрибута для проверки.
            min_val: Минимально допустимое значение.
            max_val: Максимально допустимое значение.
            error_name: Имя аргумента для сообщения об ошибке.
            convert_to_int: Конвертировать значение в int перед валидацией.

        Примечание:
            Функция безопасно проверяет наличие атрибута и его значение.
            При ошибке валидации вызывает arg_parser.error().
        """
        # Группировка параметров в dataclass для удобства
        validation_config = ValidationArgument(
            args=args,
            arg_parser=arg_parser,
            attr_name=attr_name,
            min_val=min_val,
            max_val=max_val,
            error_name=error_name,
            convert_to_int=convert_to_int,
        )

        if (
            hasattr(validation_config.args, validation_config.attr_name)
            and getattr(validation_config.args, validation_config.attr_name) is not None
        ):
            try:
                value = getattr(validation_config.args, validation_config.attr_name)
                if validation_config.convert_to_int:
                    value = int(value)
                max_val_int = (
                    int(validation_config.max_val)
                    if validation_config.max_val != float("inf")
                    else None
                )
                if max_val_int is not None:
                    validate_positive_int(
                        value, validation_config.min_val, max_val_int, validation_config.error_name
                    )
                else:
                    if value >= validation_config.min_val:
                        return
                    raise ValueError(
                        f"{validation_config.error_name} должен быть не менее {validation_config.min_val} (получено {value})"
                    )
            except ValueError as e:
                validation_config.arg_parser.error(str(e))

    def validate_urls(self, args: argparse.Namespace, arg_parser: argparse.ArgumentParser) -> None:
        """Валидирует URL из аргументов командной строки.

        Args:
            args: Аргументы командной строки.
            arg_parser: Парсер аргументов для вывода ошибок.

        Raises:
            SystemExit: При обнаружении некорректных URL.

        Примечание:
            Использует validate_url из validation.py для проверки каждого URL.
            При ошибке выводит список всех некорректных URL.
        """
        if args.url:
            url_errors = []
            for url in args.url:
                result = validate_url(url)
                if not result.is_valid:
                    url_errors.append(f"{url} ({result.error})")

            if url_errors:
                arg_parser.error(f"Некорректный формат URL: {'; '.join(url_errors)}.")

    def validate_numeric_arguments(
        self, args: argparse.Namespace, arg_parser: argparse.ArgumentParser
    ) -> None:
        """Валидирует числовые CLI аргументы.

        Args:
            args: Аргументы командной строки.
            arg_parser: Парсер для вывода ошибок.

        Примечание:
            Валидирует: parser.max_retries, timeout, max_workers,
            chrome.startup_delay, memory_limit, и другие числовые параметры.
        """
        self.validate_cli_argument(
            args, arg_parser, "parser.max_retries", 1, float("inf"), "--parser.max-retries"
        )
        self.validate_cli_argument(
            args, arg_parser, "parser.timeout", 1, float("inf"), "--parser.timeout"
        )
        self.validate_cli_argument(
            args, arg_parser, "parser.max_workers", 1, float("inf"), "--parser.max-workers"
        )
        self.validate_cli_argument(
            args,
            arg_parser,
            "chrome.startup_delay",
            0,
            float("inf"),
            "--chrome.startup-delay",
            convert_to_int=True,
        )
        self.validate_cli_argument(
            args,
            arg_parser,
            "parser.gc_pages_interval",
            1,
            float("inf"),
            "--parser.gc-pages-interval",
        )
        self.validate_cli_argument(
            args, arg_parser, "parser.max_records", 1, float("inf"), "--parser.max-records"
        )
        self.validate_cli_argument(
            args,
            arg_parser,
            "parser.max_consecutive_empty_pages",
            1,
            float("inf"),
            "--parser.max-consecutive-empty-pages",
        )
        self.validate_cli_argument(
            args,
            arg_parser,
            "parser.delay_between_clicks",
            0,
            float("inf"),
            "--parser.delay-between-clicks",
        )
        self.validate_cli_argument(
            args,
            arg_parser,
            "parser.retry_delay_base",
            1,
            float("inf"),
            "--parser.retry-delay-base",
        )
        self.validate_cli_argument(
            args,
            arg_parser,
            "parser.memory_threshold",
            256,
            float("inf"),
            "--parser.memory-threshold",
        )
        self.validate_cli_argument(
            args, arg_parser, "chrome.memory_limit", 256, float("inf"), "--chrome.memory-limit"
        )
        self.validate_cli_argument(
            args,
            arg_parser,
            "writer.csv.columns_per_entity",
            1,
            float("inf"),
            "--writer.csv.columns-per-entity",
        )

    def validate_url_sources(
        self, args: argparse.Namespace, arg_parser: argparse.ArgumentParser
    ) -> None:
        """Валидирует источники URL (URL, cities, categories-mode).

        Args:
            args: Аргументы командной строки.
            arg_parser: Парсер для вывода ошибок.

        Примечание:
            - Проверяет наличие хотя бы одного источника URL (кроме TUI)
            - Проверяет что --categories-mode требует --cities
            - Валидирует формат URL
        """
        is_tui_mode = getattr(args, "tui_new", False) or getattr(args, "tui_new_omsk", False)

        if not is_tui_mode:
            has_cities = hasattr(args, "cities") and args.cities is not None
            has_url_source = args.url is not None or has_cities

            if not has_url_source:
                arg_parser.error("Требуется указать источник URL: -i/--url или --cities")

            categories_mode = getattr(args, "categories_mode", False)
            if categories_mode and not has_cities:
                arg_parser.error("--categories-mode требует указания --cities")

        self.validate_urls(args, arg_parser)

    def validate_cli_paths(self, args: argparse.Namespace) -> None:
        """Валидирует все пути из CLI аргументов на безопасность.

        Комплексная валидация всех путей перед использованием:
        1. output_path - путь к выходному файлу
        2. chrome.binary_path - путь к браузеру
        3. log.file_path - путь к файлу логов

        Args:
            args: Аргументы командной строки.

        Raises:
            ValueError: При обнаружении небезопасного пути.
            OSError: При ошибке работы с файловой системой.
        """
        # Валидируем output_path
        output_path = getattr(args, "output_path", None)
        if output_path:
            validate_path_safety(str(output_path), "Путь к выходному файлу")

        # Валидируем chrome.binary_path если указан
        chrome_binary = getattr(args, "chrome.binary_path", None)
        if chrome_binary:
            validate_path_safety(str(chrome_binary), "Путь к браузеру")

        # Валидируем log.file_path если указан
        log_config = getattr(args, "log", None)
        if log_config and hasattr(log_config, "file_path") and log_config.file_path:
            validate_path_safety(str(log_config.file_path), "Путь к файлу логов")

    def handle_configuration_validation(
        self, config_args: dict[str, Any], arg_parser: argparse.ArgumentParser
    ) -> Configuration:
        """Инициализирует конфигурацию и обрабатывает ошибки валидации.

        Args:
            config_args: Словарь аргументов для инициализации Configuration.
            arg_parser: Парсер аргументов для вывода ошибок.

        Returns:
            Экземпляр Configuration.

        Raises:
            SystemExit: При ошибке валидации конфигурации.

        Примечание:
            Формирует понятное сообщение об ошибках валидации.
            Использует report_from_validation_error для детализации ошибок.
        """
        try:
            return Configuration(**config_args)
        except pydantic.ValidationError as e:
            errors = []
            errors_report = report_from_validation_error(e, config_args)
            for path, description in errors_report.items():
                arg = description["invalid_value"]
                error_msg = description["error_message"]
                errors.append(f"аргумент --{path} {arg} ({error_msg})")

            arg_parser.error(", ".join(errors))
            # Недостижимый код, но нужен для type checker
            raise


__all__ = ["ArgumentValidator"]
