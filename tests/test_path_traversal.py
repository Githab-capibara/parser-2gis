"""Тесты для проверки защиты от path traversal атак в writer/factory.py."""

import tempfile
from pathlib import Path

import pytest

from parser_2gis.writer.factory import _validate_path_traversal, get_writer
from parser_2gis.writer.exceptions import WriterUnknownFileFormat


class TestPathTraversalValidation:
    """Тесты для функции _validate_path_traversal."""

    def test_empty_path_raises(self):
        """Пустой путь должен вызывать ValueError."""
        with pytest.raises(ValueError, match="не может быть пустым"):
            _validate_path_traversal("")

    def test_absolute_path_valid(self):
        """Абсолютный путь должен проходить валидацию."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "output.json"
            result = _validate_path_traversal(str(test_path))
            assert result.is_absolute()
            assert result.parent == Path(tmpdir)

    def test_normalized_absolute_path(self):
        """Нормализованный абсолютный путь должен работать."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "subdir" / "file.json"
            result = _validate_path_traversal(str(test_file))
            assert result.is_absolute()
            assert result.parts[-2:] == ("subdir", "file.json")

    def test_dollar_in_path_raises(self):
        """Путь с долларом должен вызывать ValueError."""
        with pytest.raises(ValueError):
            _validate_path_traversal("/data/$var/file.json")

    def test_mkdir_for_parent_creates_directory(self):
        """Валидация должна создавать родительскую директорию."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "newdir" / "nested" / "output.json"
            result = _validate_path_traversal(str(test_path))
            assert result.parent.exists()


class TestGetWriterPathValidation:
    """Тесты для функции get_writer с валидацией пути."""

    def test_malicious_path_handled(self):
        """Вредоносный путь должен обрабатываться безопасно."""
        result = get_writer("../../../etc/passwd", "json", None)
        assert result is not None

    def test_unknown_format_raises(self):
        """Неизвестный формат должен вызывать WriterUnknownFileFormat."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "output.xyz"
            with pytest.raises(WriterUnknownFileFormat):
                get_writer(str(test_path), "xyz", None)
