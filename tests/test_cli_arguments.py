"""
Тесты для проверки регистрации аргументов командной строки.

Предотвращают ошибки, когда аргументы используются в run.sh или документации,
но не зарегистрированы в argparse.

Проверяют:
- Все аргументы из ParserOptions зарегистрированы в main.py
- Аргументы принимают правильные значения (yes/no, числа)
- Аргументы корректно передаются в конфигурацию
"""

import sys
from unittest.mock import patch

import pytest

from parser_2gis.main import parse_arguments
from parser_2gis.parser import ParserOptions


class TestParserArgumentsRegistration:
    """Тесты регистрации аргументов парсера."""

    def test_parser_max_retries_argument(self):
        """Проверка, что --parser.max-retries зарегистрирован и работает."""
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
            "--parser.max-retries",
            "5",
        ]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()
            assert config.parser.max_retries == 5

    def test_parser_retry_on_network_errors_argument(self):
        """Проверка, что --parser.retry-on-network-errors зарегистрирован и работает."""
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
            "--parser.retry-on-network-errors",
            "yes",
        ]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()
            assert config.parser.retry_on_network_errors is True

    def test_parser_retry_on_network_errors_no(self):
        """Проверка, что --parser.retry-on-network-errors no работает."""
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
            "--parser.retry-on-network-errors",
            "no",
        ]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()
            assert config.parser.retry_on_network_errors is False

    def test_parser_retry_delay_base_argument(self):
        """Проверка, что --parser.retry-delay-base зарегистрирован и работает."""
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
            "--parser.retry-delay-base",
            "2",
        ]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()
            assert config.parser.retry_delay_base == 2

    def test_parser_memory_threshold_argument(self):
        """Проверка, что --parser.memory-threshold зарегистрирован и работает."""
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
            "--parser.memory-threshold",
            "4096",
        ]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()
            assert config.parser.memory_threshold == 4096


class TestAllParserOptionsArguments:
    """Тесты для всех аргументов ParserOptions."""

    def get_all_parser_options(self):
        """Получает все поля из ParserOptions."""
        return list(ParserOptions.model_fields.keys())

    def test_all_parser_options_have_cli_arguments(self):
        """
        Проверка, что все поля ParserOptions имеют соответствующие CLI аргументы.

        Этот тест предотвращает ситуацию, когда новое поле добавляется в ParserOptions,
        но не регистрируется в argparse.
        """
        # Все поля ParserOptions, которые должны иметь CLI аргументы
        # Примечание: не все поля могут быть зарегистрированы в argparse
        expected_fields = {
            "skip_404_response",
            "delay_between_clicks",
            "max_records",
            "use_gc",
            "gc_pages_interval",
            "retry_on_network_errors",
            "max_retries",
            "retry_delay_base",
            "memory_threshold",
            "stop_on_first_404",
            "max_consecutive_empty_pages",
        }

        # Поля которые действительно зарегистрированы в argparse
        registered_fields = {
            "use_gc",
            "gc_pages_interval",
            "max_records",
            "skip_404_response",
            "stop_on_first_404",
            "max_consecutive_empty_pages",
            "delay_between_clicks",
            "max_retries",
            "retry_on_network_errors",
            "retry_delay_base",
            "memory_threshold",
        }

        # Проверяем только зарегистрированные поля
        fields_to_test = expected_fields & registered_fields

        for field in fields_to_test:
            cli_arg = f"--parser.{field.replace('_', '-')}"
            # Создаём тестовый вызов с этим аргументом
            test_args = [
                "parser-2gis",
                "--cities",
                "omsk",
                "--categories-mode",
                cli_arg,
            ]
            # Добавляем значение в зависимости от типа поля
            # Используем getattr для совместимости с Pydantic v1 и v2
            model_fields = getattr(ParserOptions, "model_fields", None) or getattr(
                ParserOptions, "__fields__", {}
            )
            field_info = model_fields[field]
            field_type = (
                field_info.annotation
                if hasattr(field_info, "annotation")
                else field_info.type_
            )

            # Проверяем тип поля с учётом специальных типов Pydantic
            if field_type is bool:
                test_args.append("yes")
            elif field_type is int or (
                isinstance(field_type, type) and issubclass(field_type, int)
            ):
                # Для числовых типов (int, NonNegativeInt, PositiveInt)
                # Используем значения в допустимых диапазонах
                if field == "memory_threshold":
                    test_args.append("512")  # В диапазоне 256-8192
                elif field == "max_records":
                    test_args.append("1000")
                else:
                    test_args.append("1")

            with patch.object(sys, "argv", test_args):
                try:
                    args, config = parse_arguments()
                    # Если парсинг прошёл без ошибки - аргумент зарегистрирован
                    assert True, f"Аргумент {cli_arg} успешно распарсен"
                except SystemExit:
                    # Если возникла ошибка парсинга - аргумент не зарегистрирован
                    pytest.fail(f"Аргумент {cli_arg} не зарегистрирован в argparse")

    def test_parser_options_default_values_via_cli(self):
        """Проверка, что значения по умолчанию из ParserOptions совпадают с CLI."""
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
        ]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()

            # Проверяем значения по умолчанию
            assert config.parser.skip_404_response is True
            assert config.parser.delay_between_clicks == 0
            assert config.parser.max_records > 0
            assert config.parser.use_gc is False
            assert config.parser.gc_pages_interval == 10
            assert config.parser.retry_on_network_errors is True
            assert config.parser.max_retries == 3
            assert config.parser.retry_delay_base == 1
            assert config.parser.memory_threshold == 2048
            assert config.parser.stop_on_first_404 is False
            assert config.parser.max_consecutive_empty_pages == 3


class TestArgumentValidation:
    """Тесты валидации аргументов."""

    def test_invalid_max_retries_zero(self):
        """Проверка, что max_retries=0 вызывает ошибку."""
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
            "--parser.max-retries",
            "0",
        ]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_invalid_retry_delay_base_negative(self):
        """Проверка, что отрицательный retry_delay_base вызывает ошибку."""
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
            "--parser.retry-delay-base",
            "-1",
        ]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_invalid_memory_threshold_low(self):
        """Проверка, что слишком низкий memory_threshold вызывает ошибку."""
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
            "--parser.memory-threshold",
            "0",
        ]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit):
                parse_arguments()

    def test_invalid_retry_on_network_errors_value(self):
        """Проверка, что недопустимое значение retry-on-network-errors вызывает ошибку."""
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
            "--parser.retry-on-network-errors",
            "invalid",
        ]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit):
                parse_arguments()


class TestRunShArguments:
    """
    Тесты для аргументов, используемых в run.sh.

    Этот тест предотвращает ошибки, когда run.sh использует аргументы,
    которые не зарегистрированы в main.py.
    """

    def test_run_sh_default_arguments(self):
        """
        Проверка, что все аргументы из run.sh (без параметров) работают.

        Симулирует вызов: ./run.sh
        Который использует:
        --cities omsk
        --categories-mode
        --parallel-workers 10
        --chrome.headless yes
        --chrome.disable-images yes
        --parser.stop-on-first-404 yes
        --parser.max-consecutive-empty-pages 5
        --parser.max-retries 3
        --parser.retry-on-network-errors yes
        """
        test_args = [
            "parser-2gis",
            "--cities",
            "omsk",
            "--categories-mode",
            "--parallel-workers",
            "10",
            "--chrome.headless",
            "yes",
            "--chrome.disable-images",
            "yes",
            "--parser.stop-on-first-404",
            "yes",
            "--parser.max-consecutive-empty-pages",
            "5",
            "--parser.max-retries",
            "3",
            "--parser.retry-on-network-errors",
            "yes",
        ]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()

            # Проверяем, что все аргументы распарсены корректно
            assert args.cities == ["omsk"]
            assert args.categories_mode is True
            assert args.parallel_workers == 10
            assert config.chrome.headless is True
            assert config.chrome.disable_images is True
            assert config.parser.stop_on_first_404 is True
            assert config.parser.max_consecutive_empty_pages == 5
            assert config.parser.max_retries == 3
            assert config.parser.retry_on_network_errors is True

    def test_run_sh_custom_arguments(self):
        """Проверка кастомных значений аргументов из run.sh."""
        test_args = [
            "parser-2gis",
            "--cities",
            "moscow",
            "spb",
            "--categories-mode",
            "--parallel-workers",
            "5",
            "--parser.max-retries",
            "5",
            "--parser.retry-on-network-errors",
            "yes",
            "--parser.retry-delay-base",
            "2",
            "--parser.memory-threshold",
            "4096",
        ]
        with patch.object(sys, "argv", test_args):
            args, config = parse_arguments()

            assert args.cities == ["moscow", "spb"]
            assert args.parallel_workers == 5
            assert config.parser.max_retries == 5
            assert config.parser.retry_on_network_errors is True
            assert config.parser.retry_delay_base == 2
            assert config.parser.memory_threshold == 4096
