"""Тесты для ISSUE-005: CSVWriter стратегии форматирования.

Проверяет:
- PhoneFormatter - форматирование телефонов
- SanitizeFormatter - санитизация данных
- TypeFormatter - форматирование типов
- ContactFormatter - форматирование контактов
- CompositeFormatter - композитное форматирование
- CSVWriter - использование стратегий

"""

from __future__ import annotations

import pathlib
from unittest.mock import MagicMock

import pytest

from parser_2gis.writer.writers.csv_formatter import (
    BaseFormatter,
    CompositeFormatter,
    ContactFormatter,
    PhoneFormatter,
    SanitizeFormatter,
    TypeFormatter,
)
from parser_2gis.writer.writers.csv_writer import CSVWriter


class TestPhoneFormatter:
    """Тесты для PhoneFormatter."""

    def test_format_russian_number(self) -> None:
        """Тестирует форматирование российского номера."""
        formatter = PhoneFormatter()
        result = formatter.format("+7 (495) 123-45-67")

        assert result == "84951234567"

    def test_format_without_plus(self) -> None:
        """Тестирует форматирование без плюса."""
        formatter = PhoneFormatter()
        result = formatter.format("7 (495) 123-45-67")

        assert result == "74951234567"

    def test_format_with_spaces(self) -> None:
        """Тестирует форматирование с пробелами."""
        formatter = PhoneFormatter()
        result = formatter.format("8 999 123 45 67")

        assert result == "89991234567"

    def test_format_with_dashes(self) -> None:
        """Тестирует форматирование с дефисами."""
        formatter = PhoneFormatter()
        result = formatter.format("8-999-123-45-67")

        assert result == "89991234567"

    def test_format_already_formatted(self) -> None:
        """Тестирует форматирование уже отформатированного номера."""
        formatter = PhoneFormatter()
        result = formatter.format("89991234567")

        assert result == "89991234567"

    def test_format_with_letters(self) -> None:
        """Тестирует форматирование с буквами."""
        formatter = PhoneFormatter()
        result = formatter.format("+7 (495) 123-45-67 доб. 123")

        # PhoneFormatter удаляет все нецифровые символы кроме +
        # "доб. 123" будет преобразовано в "123"
        assert result == "84951234567123"


class TestSanitizeFormatter:
    """Тесты для SanitizeFormatter."""

    def test_sanitize_quotes(self) -> None:
        """Тестирует экранирование кавычек."""
        formatter = SanitizeFormatter()
        result = formatter.format('Test "quoted" value')

        assert '""' in result

    def test_sanitize_newlines(self) -> None:
        """Тестирует замену новых строк."""
        formatter = SanitizeFormatter()
        result = formatter.format("Line 1\nLine 2")

        assert "\n" not in result
        assert " " in result

    def test_sanitize_carriage_return(self) -> None:
        """Тестирует удаление carriage return."""
        formatter = SanitizeFormatter()
        result = formatter.format("Line 1\r\nLine 2")

        assert "\r" not in result

    def test_sanitize_tabs(self) -> None:
        """Тестирует замену табов."""
        formatter = SanitizeFormatter()
        result = formatter.format("Col1\tCol2")

        assert "\t" not in result

    def test_sanitize_null_bytes(self) -> None:
        """Тестирует удаление null-символов."""
        formatter = SanitizeFormatter()
        result = formatter.format("Test\x00value")

        assert "\x00" not in result

    def test_sanitize_csv_injection_equals(self) -> None:
        """Тестирует защиту от CSV injection с =."""
        formatter = SanitizeFormatter()
        result = formatter.format("=SUM(A1:A10)")

        assert result.startswith("'")

    def test_sanitize_csv_injection_plus(self) -> None:
        """Тестирует защиту от CSV injection с +."""
        formatter = SanitizeFormatter()
        result = formatter.format("+123")

        assert result.startswith("'")

    def test_sanitize_csv_injection_minus(self) -> None:
        """Тестирует защиту от CSV injection с -."""
        formatter = SanitizeFormatter()
        result = formatter.format("-123")

        assert result.startswith("'")

    def test_sanitize_csv_injection_at(self) -> None:
        """Тестирует защиту от CSV injection с @."""
        formatter = SanitizeFormatter()
        result = formatter.format("@test")

        assert result.startswith("'")

    def test_sanitize_safe_value(self) -> None:
        """Тестирует санитизацию безопасного значения."""
        formatter = SanitizeFormatter()
        result = formatter.format("Normal text")

        assert result == "Normal text"

    def test_sanitize_non_string(self) -> None:
        """Тестирует санитизацию нестрокового значения."""
        formatter = SanitizeFormatter()
        result = formatter.format(123)  # type: ignore[arg-type]

        assert result == "123"


class TestTypeFormatter:
    """Тесты для TypeFormatter."""

    def test_format_parking(self) -> None:
        """Тестирует форматирование parking."""
        formatter = TypeFormatter()
        result = formatter.format("parking")

        assert result == "Парковка"

    def test_format_street(self) -> None:
        """Тестирует форматирование street."""
        formatter = TypeFormatter()
        result = formatter.format("street")

        assert result == "Улица"

    def test_format_road(self) -> None:
        """Тестирует форматирование road."""
        formatter = TypeFormatter()
        result = formatter.format("road")

        assert result == "Дорога"

    def test_format_crossroad(self) -> None:
        """Тестирует форматирование crossroad."""
        formatter = TypeFormatter()
        result = formatter.format("crossroad")

        assert result == "Перекрёсток"

    def test_format_station(self) -> None:
        """Тестирует форматирование station."""
        formatter = TypeFormatter()
        result = formatter.format("station")

        assert result == "Остановка"

    def test_format_unknown_type(self) -> None:
        """Тестирует форматирование неизвестного типа."""
        formatter = TypeFormatter()
        result = formatter.format("unknown_type")

        assert result == "unknown_type"


class TestContactFormatter:
    """Тесты для ContactFormatter."""

    def test_format_without_comment(self) -> None:
        """Тестирует форматирование без комментария."""
        formatter = ContactFormatter(add_comments=False)
        result = formatter.format("test@example.com")

        assert result == "test@example.com"

    def test_format_with_comment_disabled(self) -> None:
        """Тестирует форматирование с отключенным комментарием."""
        formatter = ContactFormatter(add_comments=False)
        result = formatter.format("test@example.com", "work")

        assert result == "test@example.com"

    def test_format_with_comment_enabled(self) -> None:
        """Тестирует форматирование с включенным комментарием."""
        formatter = ContactFormatter(add_comments=True)
        result = formatter.format("test@example.com", "work")

        assert result == "test@example.com (work)"

    def test_format_with_empty_comment(self) -> None:
        """Тестирует форматирование с пустым комментарием."""
        formatter = ContactFormatter(add_comments=True)
        result = formatter.format("test@example.com", "")

        assert result == "test@example.com"


class TestCompositeFormatter:
    """Тесты для CompositeFormatter."""

    def test_composite_phone_and_sanitize(self) -> None:
        """Тестирует композитное форматирование телефона и санитизации."""
        formatter = CompositeFormatter(PhoneFormatter(), SanitizeFormatter())
        result = formatter.format("+7 (495) 123-45-67")

        assert result == "84951234567"

    def test_composite_single_formatter(self) -> None:
        """Тестирует композит с одним форматировщиком."""
        formatter = CompositeFormatter(PhoneFormatter())
        result = formatter.format("+7 (495) 123-45-67")

        assert result == "84951234567"

    def test_composite_empty_formatter_list(self) -> None:
        """Тестирует композит без форматировщиков."""
        formatter = CompositeFormatter()
        result = formatter.format("test value")

        assert result == "test value"


class TestBaseFormatter:
    """Тесты для BaseFormatter."""

    def test_base_formatter_abstract(self) -> None:
        """Тестирует что BaseFormatter абстрактный."""
        with pytest.raises(TypeError):
            BaseFormatter()  # type: ignore[abstract]


class TestCSVWriterWithStrategies:
    """Тесты для CSVWriter с использованием стратегий."""

    @pytest.fixture
    def mock_options(self) -> MagicMock:
        """Создаёт фиктивные опции."""
        options = MagicMock()
        options.csv.columns_per_entity = 3
        options.csv.add_rubrics = True
        options.csv.add_comments = False
        options.csv.remove_empty_columns = False
        options.csv.remove_duplicates = False
        options.csv.join_char = ", "
        options.encoding = "utf-8"
        options.verbose = False
        return options

    @pytest.fixture
    def temp_csv_file(self, tmp_path: pathlib.Path) -> pathlib.Path:
        """Создаёт временный CSV файл."""
        return tmp_path / "test.csv"

    def test_csv_writer_initializes_formatters(self, mock_options: MagicMock, temp_csv_file: pathlib.Path) -> None:
        """Тестирует инициализацию форматировщиков в CSVWriter."""
        writer = CSVWriter(file_path=str(temp_csv_file), options=mock_options)

        assert hasattr(writer, "_phone_formatter")
        assert hasattr(writer, "_sanitize_formatter")
        assert hasattr(writer, "_type_formatter")
        assert hasattr(writer, "_contact_formatter")

        assert isinstance(writer._phone_formatter, PhoneFormatter)
        assert isinstance(writer._sanitize_formatter, SanitizeFormatter)
        assert isinstance(writer._type_formatter, TypeFormatter)
        assert isinstance(writer._contact_formatter, ContactFormatter)

    def test_csv_writer_type_names_uses_formatter(self, mock_options: MagicMock, temp_csv_file: pathlib.Path) -> None:
        """Тестирует что _type_names использует TypeFormatter."""
        writer = CSVWriter(file_path=str(temp_csv_file), options=mock_options)

        type_names = writer._type_names

        assert type_names["parking"] == "Парковка"
        assert type_names["street"] == "Улица"

    def test_csv_writer_sanitize_in_extract_raw(self, mock_options: MagicMock, temp_csv_file: pathlib.Path) -> None:
        """Тестирует санитизацию в _extract_raw."""
        writer = CSVWriter(file_path=str(temp_csv_file), options=mock_options)

        # Проверяем что санитизация работает
        test_value = "=SUM(A1:A10)"
        sanitized = writer._sanitize_formatter.format(test_value)

        assert sanitized.startswith("'")


class TestCSVFormatterIntegration:
    """Интеграционные тесты для стратегий форматирования."""

    def test_full_phone_formatting_pipeline(self) -> None:
        """Тестирует полный пайплайн форматирования телефона."""
        # Создаём композитный форматировщик
        formatter = CompositeFormatter(PhoneFormatter(), SanitizeFormatter())

        # Тестируем различные форматы ввода
        test_cases = [
            ("+7 (495) 123-45-67", "84951234567"),
            ("8-999-123-45-67", "89991234567"),
            ("+74951234567", "84951234567"),
        ]

        for input_val, expected in test_cases:
            result = formatter.format(input_val)
            assert result == expected

    def test_csv_injection_protection_pipeline(self) -> None:
        """Тестирует защиту от CSV injection."""
        formatter = SanitizeFormatter()

        # Опасные значения
        dangerous_values = ["=SUM(A1:A10)", "+123", "-123", "@test", '="1+1"']

        for value in dangerous_values:
            result = formatter.format(value)
            assert result.startswith("'"), f"CSV injection не предотвращён для {value}"
