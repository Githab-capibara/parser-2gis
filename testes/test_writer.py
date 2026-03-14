"""
Тесты для модуля writer.

Проверяют следующие возможности:
- CSVOptions валидация
- WriterOptions валидация
- CSVWriter
- JSONWriter
- XLSXWriter
- FileWriter
"""

import os
import tempfile

import pytest

from parser_2gis.writer import (CSVWriter, JSONWriter, XLSXWriter,
                                CSVOptions, WriterOptions, get_writer)


class TestCSVOptions:
    """Тесты для CSVOptions."""

    def test_csv_options_default(self):
        """Проверка значений по умолчанию."""
        options = CSVOptions()
        assert options.add_rubrics is True
        assert options.add_comments is True
        assert options.columns_per_entity == 3
        assert options.remove_empty_columns is True
        assert options.remove_duplicates is True
        assert options.join_char == '; '

    def test_csv_options_custom(self):
        """Проверка кастомных значений."""
        options = CSVOptions(
            add_rubrics=False,
            add_comments=False,
            columns_per_entity=5,
            remove_empty_columns=False,
            remove_duplicates=False,
            join_char=' | '
        )
        assert options.add_rubrics is False
        assert options.add_comments is False
        assert options.columns_per_entity == 5
        assert options.remove_empty_columns is False
        assert options.remove_duplicates is False
        assert options.join_char == ' | '

    def test_csv_options_invalid_columns(self):
        """Проверка валидации columns_per_entity."""
        with pytest.raises(Exception):
            CSVOptions(columns_per_entity=0)

        with pytest.raises(Exception):
            CSVOptions(columns_per_entity=6)

    def test_csv_options_valid_columns_range(self):
        """Проверка допустимого диапазона columns_per_entity."""
        for value in [1, 2, 3, 4, 5]:
            options = CSVOptions(columns_per_entity=value)
            assert options.columns_per_entity == value


class TestWriterOptions:
    """Тесты для WriterOptions."""

    def test_writer_options_default(self):
        """Проверка значений по умолчанию."""
        options = WriterOptions()
        assert options.encoding == 'utf-8-sig'
        assert options.verbose is True
        assert isinstance(options.csv, CSVOptions)

    def test_writer_options_custom(self):
        """Проверка кастомных значений."""
        options = WriterOptions(
            encoding='utf-8',
            verbose=False,
            csv=CSVOptions(add_rubrics=False)
        )
        assert options.encoding == 'utf-8'
        assert options.verbose is False
        assert options.csv.add_rubrics is False

    def test_writer_options_invalid_encoding(self):
        """Проверка валидации кодировки."""
        with pytest.raises(Exception):
            WriterOptions(encoding='invalid-encoding')

    def test_writer_options_valid_encodings(self):
        """Проверка различных допустимых кодировок."""
        valid_encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']
        for encoding in valid_encodings:
            options = WriterOptions(encoding=encoding)
            assert options.encoding == encoding


class TestCSVWriter:
    """Тесты для CSVWriter."""

    def test_csv_writer_creation(self):
        """Проверка создания CSVWriter."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            try:
                options = WriterOptions()
                writer = CSVWriter(f.name, options)
                assert writer is not None
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)


class TestJSONWriter:
    """Тесты для JSONWriter."""

    def test_json_writer_creation(self):
        """Проверка создания JSONWriter."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            try:
                options = WriterOptions()
                writer = JSONWriter(f.name, options)
                assert writer is not None
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)


class TestXLSXWriter:
    """Тесты для XLSXWriter."""

    def test_xlsx_writer_creation(self):
        """Проверка создания XLSXWriter."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            try:
                options = WriterOptions()
                writer = XLSXWriter(f.name, options)
                assert writer is not None
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)


class TestFileWriter:
    """Тесты для FileWriter."""

    def test_file_writer_is_base_class(self):
        """Проверка, что FileWriter - базовый класс."""
        from parser_2gis.writer.writers.file_writer import FileWriter
        from parser_2gis.writer.writers.csv_writer import CSVWriter

        assert issubclass(CSVWriter, FileWriter)
        assert issubclass(JSONWriter, FileWriter)
        assert issubclass(XLSXWriter, FileWriter)


class TestGetWriter:
    """Тесты для функции get_writer."""

    def test_get_writer_csv(self):
        """Проверка получения CSV writer."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            try:
                options = WriterOptions()
                writer = get_writer(f.name, 'csv', options)
                assert isinstance(writer, CSVWriter)
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)

    def test_get_writer_xlsx(self):
        """Проверка получения XLSX writer."""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            try:
                options = WriterOptions()
                writer = get_writer(f.name, 'xlsx', options)
                assert isinstance(writer, XLSXWriter)
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)

    def test_get_writer_json(self):
        """Проверка получения JSON writer."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            try:
                options = WriterOptions()
                writer = get_writer(f.name, 'json', options)
                assert isinstance(writer, JSONWriter)
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)

    def test_get_writer_unknown_extension(self):
        """Проверка получения writer с неизвестным расширением."""
        from parser_2gis.writer.exceptions import WriterUnknownFileFormat

        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            try:
                options = WriterOptions()
                with pytest.raises(WriterUnknownFileFormat):
                    get_writer(f.name, 'txt', options)
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)
