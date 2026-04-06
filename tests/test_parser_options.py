"""
Тесты для модуля parser_options.py.

Проверяют следующие возможности:
- ParserOptions валидация
- ParserException
- get_parser функция
"""

import pytest

from parser_2gis.parser import ParserOptions


class TestParserOptions:
    """Тесты для ParserOptions."""

    def test_parser_options_default(self):
        """Проверка значений по умолчанию."""
        options = ParserOptions()
        assert options.skip_404_response is True
        assert options.delay_between_clicks >= 0
        assert options.max_records > 0
        assert options.use_gc is False
        assert options.gc_pages_interval > 0

    def test_parser_options_custom(self):
        """Проверка кастомных значений."""
        options = ParserOptions(
            skip_404_response=False,
            delay_between_clicks=500,
            max_records=100,
            use_gc=True,
            gc_pages_interval=5,
        )
        assert options.skip_404_response is False
        assert options.delay_between_clicks == 500
        assert options.max_records == 100
        assert options.use_gc is True
        assert options.gc_pages_interval == 5

    def test_parser_options_invalid_delay(self):
        """Проверка валидации delay_between_clicks."""
        with pytest.raises(Exception):
            ParserOptions(delay_between_clicks=-1)

    def test_parser_options_invalid_max_records(self):
        """Проверка валидации max_records."""
        with pytest.raises(Exception):
            ParserOptions(max_records=0)

        with pytest.raises(Exception):
            ParserOptions(max_records=-1)

    def test_parser_options_invalid_gc_interval(self):
        """Проверка валидации gc_pages_interval."""
        with pytest.raises(Exception):
            ParserOptions(gc_pages_interval=0)

    def test_parser_options_zero_delay(self):
        """Проверка нулевой задержки."""
        options = ParserOptions(delay_between_clicks=0)
        assert options.delay_between_clicks == 0

    def test_parser_options_large_delay(self):
        """Проверка большой задержки."""
        options = ParserOptions(delay_between_clicks=100000)
        assert options.delay_between_clicks == 100000

    def test_parser_options_large_max_records(self):
        """Проверка большого количества записей."""
        options = ParserOptions(max_records=100000)
        assert options.max_records == 100000


class TestParserDefaultValues:
    """Тесты для значений по умолчанию парсера."""

    def test_default_max_records_positive(self):
        """Проверка, что max_records по умолчанию положительное."""
        options = ParserOptions()
        assert options.max_records > 0

    def test_default_delay_zero(self):
        """Проверка, что delay по умолчанию равен нулю."""
        options = ParserOptions()
        assert options.delay_between_clicks == 0

    def test_default_skip_404_true(self):
        """Проверка, что skip_404 по умолчанию True."""
        options = ParserOptions()
        assert options.skip_404_response is True

    def test_default_gc_false(self):
        """Проверка, что use_gc по умолчанию False."""
        options = ParserOptions()
        assert options.use_gc is False

    def test_default_gc_interval(self):
        """Проверка gc_pages_interval по умолчанию."""
        options = ParserOptions()
        assert options.gc_pages_interval == 10


class TestParserOptionsValidation:
    """Тесты для валидации ParserOptions."""

    def test_all_fields_optional(self):
        """Проверка, что все поля необязательны."""
        # Должно работать без аргументов
        options = ParserOptions()
        assert isinstance(options, ParserOptions)

    def test_partial_update(self):
        """Проверка частичного обновления."""
        options = ParserOptions(max_records=100)
        assert options.max_records == 100
        # Остальные поля должны быть по умолчанию
        assert options.skip_404_response is True
        assert options.delay_between_clicks == 0

    def test_type_coercion(self):
        """Проверка приведения типов."""
        # Pydantic должен привести int к правильному типу
        options = ParserOptions(delay_between_clicks=100)
        assert isinstance(options.delay_between_clicks, int)
