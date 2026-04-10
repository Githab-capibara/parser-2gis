"""
Тесты для модуля version.py и exceptions.py.

Проверяют:
- Версию пакета
- Конфигурационную версию
- Исключения
"""

import pytest

from parser_2gis import __version__
from parser_2gis.chrome.exceptions import (
    ChromeException,
    ChromePathNotFound,
    ChromeRuntimeException,
    ChromeUserAbortException,
)
from parser_2gis.parser.exceptions import ParserException
from parser_2gis.version import config_version, version
from parser_2gis.writer.exceptions import WriterUnknownFileFormat
from typing import Never


class TestVersion:
    """Тесты для версии."""

    def test_version_exists(self) -> None:
        """Проверка существования версии."""
        assert version is not None

    def test_version_is_string(self) -> None:
        """Проверка, что версия - строка."""
        assert isinstance(version, str)

    def test_version_format(self) -> None:
        """Проверка формата версии."""
        # Версия должна быть в формате X.Y.Z
        parts = version.split(".")
        assert len(parts) >= 2
        for part in parts:
            assert part.isdigit() or part.replace(".", "").isdigit()

    def test_version_from_init(self) -> None:
        """Проверка версии из __init__.py."""
        assert __version__ is not None
        assert __version__ == version

    def test_version_current(self) -> None:
        """Проверка текущей версии."""
        # Версия может обновляться, проверяем что она в формате X.Y.Z
        assert version is not None
        parts = version.split(".")
        assert len(parts) >= 2
        # Основная версия 2.x.x
        assert parts[0] == "2"


class TestConfigVersion:
    """Тесты для версии конфигурации."""

    def test_config_version_exists(self) -> None:
        """Проверка существования версии конфигурации."""
        assert config_version is not None

    def test_config_version_is_string(self) -> None:
        """Проверка, что версия конфигурации - строка."""
        assert isinstance(config_version, str)

    def test_config_version_format(self) -> None:
        """Проверка формата версии конфигурации."""
        # Версия должна быть в формате X.Y
        parts = config_version.split(".")
        assert len(parts) >= 1
        for part in parts:
            assert part.isdigit() or part.replace(".", "").isdigit()

    def test_config_version_current(self) -> None:
        """Проверка текущей версии конфигурации."""
        assert config_version == "0.1"


class TestChromeExceptions:
    """Тесты для исключений Chrome."""

    def test_chrome_exception_base(self) -> None:
        """Проверка базового исключения Chrome."""
        exc = ChromeException("Test error")
        # Новое сообщение включает контекстную информацию
        assert "Test error" in str(exc)
        assert "Функция:" in str(exc)
        assert "Строка:" in str(exc)
        assert "Файл:" in str(exc)
        assert isinstance(exc, Exception)

    def test_chrome_path_not_found(self) -> None:
        """Проверка исключения ChromePathNotFound."""
        path = "/usr/bin/google-chrome"
        exc = ChromePathNotFound(path)
        assert path in str(exc)
        assert isinstance(exc, ChromeException)
        assert isinstance(exc, Exception)

    def test_chrome_runtime_exception(self) -> None:
        """Проверка исключения ChromeRuntimeException."""
        exc = ChromeRuntimeException("Runtime error")
        # Новое сообщение включает контекстную информацию
        assert "Runtime error" in str(exc)
        assert "Функция:" in str(exc)
        assert "Строка:" in str(exc)
        assert isinstance(exc, ChromeException)
        assert isinstance(exc, Exception)

    def test_chrome_user_abort_exception(self) -> None:
        """Проверка исключения ChromeUserAbortException."""
        exc = ChromeUserAbortException("User aborted")
        # Новое сообщение включает контекстную информацию
        assert "User aborted" in str(exc)
        assert "Функция:" in str(exc)
        assert "Строка:" in str(exc)
        assert isinstance(exc, ChromeException)
        assert isinstance(exc, Exception)

    def test_chrome_exception_hierarchy(self) -> None:
        """Проверка иерархии исключений Chrome."""
        assert issubclass(ChromePathNotFound, ChromeException)
        assert issubclass(ChromeRuntimeException, ChromeException)
        assert issubclass(ChromeUserAbortException, ChromeException)
        assert issubclass(ChromeException, Exception)


class TestParserException:
    """Тесты для исключения ParserException."""

    def test_parser_exception_creation(self) -> None:
        """Проверка создания исключения."""
        exc = ParserException("Parser error")
        # Новое сообщение включает контекстную информацию
        assert "Parser error" in str(exc)
        assert "Функция:" in str(exc)
        assert "Строка:" in str(exc)
        assert isinstance(exc, Exception)

    def test_parser_exception_with_args(self) -> None:
        """Проверка исключения с аргументами."""
        # Новый конструктор поддерживает только одно сообщение
        exc = ParserException("Error with details")
        assert "Error with details" in str(exc)
        assert exc is not None


class TestWriterException:
    """Тесты для исключения WriterException."""

    def test_writer_unknown_file_format(self) -> None:
        """Проверка исключения WriterUnknownFileFormat."""
        exc = WriterUnknownFileFormat(".txt")
        assert ".txt" in str(exc)
        assert isinstance(exc, Exception)

    def test_writer_unknown_file_format_with_path(self) -> None:
        """Проверка исключения с путём."""
        exc = WriterUnknownFileFormat("/path/to/file.xyz")
        assert ".xyz" in str(exc) or "/path/to/file.xyz" in str(exc)
        assert isinstance(exc, Exception)


class TestExceptionUsage:
    """Тесты для использования исключений."""

    def test_raise_chrome_exception(self) -> Never:
        """Проверка выбрасывания ChromeException."""
        with pytest.raises(ChromeException):
            raise ChromeException("Test")

    def test_raise_parser_exception(self) -> Never:
        """Проверка выбрасывания ParserException."""
        with pytest.raises(ParserException):
            raise ParserException("Test")

    def test_raise_writer_exception(self) -> Never:
        """Проверка выбрасывания WriterUnknownFileFormat."""
        with pytest.raises(WriterUnknownFileFormat):
            raise WriterUnknownFileFormat(".unknown")

    def test_catch_chrome_subclass_as_chrome(self) -> Never:
        """Проверка перехвата подкласса как ChromeException."""
        with pytest.raises(ChromeException):
            raise ChromePathNotFound("/path")

    def test_exception_inheritance_chain(self) -> None:
        """Проверка цепочки наследования."""
        exc = ChromePathNotFound("/path")
        assert isinstance(exc, ChromeException)
        assert isinstance(exc, Exception)
        assert isinstance(exc, BaseException)


class TestExceptionMessages:
    """Тесты для сообщений исключений."""

    def test_chrome_exception_message(self) -> None:
        """Проверка сообщения ChromeException."""
        messages = ["Error 1", "Error 2", "Some error message"]
        for msg in messages:
            exc = ChromeException(msg)
            # Новое сообщение включает контекстную информацию
            assert msg in str(exc)
            assert "Функция:" in str(exc)
            assert "Строка:" in str(exc)

    def test_parser_exception_message(self) -> None:
        """Проверка сообщения ParserException."""
        messages = ["Error 1", "Error 2", "Some error message"]
        for msg in messages:
            exc = ParserException(msg)
            # Новое сообщение включает контекстную информацию
            assert msg in str(exc)
            assert "Функция:" in str(exc)
            assert "Строка:" in str(exc)

    def test_chrome_path_not_found_message(self) -> None:
        """Проверка сообщения ChromePathNotFound."""
        paths = ["/usr/bin/chrome", "C:\\Chrome\\chrome.exe", "~/chrome"]
        for path in paths:
            exc = ChromePathNotFound(path)
            assert path in str(exc)
