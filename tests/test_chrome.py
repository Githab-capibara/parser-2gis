"""
Тесты для модуля chrome.

Проверяют следующие возможности:
- ChromeOptions валидация
- ChromeRemote
- ChromeException и наследники
"""

import pathlib
import pytest

from parser_2gis.chrome import ChromeOptions, ChromeRemote
from parser_2gis.chrome.exceptions import (
    ChromeException,
    ChromePathNotFound,
    ChromeRuntimeException,
    ChromeUserAbortException,
)


class TestChromeOptions:
    """Тесты для ChromeOptions."""

    def test_chrome_options_default(self):
        """Проверка значений по умолчанию."""
        options = ChromeOptions()
        assert options.binary_path is None
        assert options.start_maximized is False
        assert options.headless is False
        assert options.disable_images is True
        assert options.silent_browser is True
        assert options.memory_limit > 0

    def test_chrome_options_custom(self):
        """Проверка кастомных значений."""
        custom_path = pathlib.Path("/usr/bin/google-chrome")
        options = ChromeOptions(
            binary_path=custom_path,
            start_maximized=True,
            headless=True,
            disable_images=False,
            silent_browser=False,
            memory_limit=512,
        )
        assert options.binary_path == custom_path
        assert options.start_maximized is True
        assert options.headless is True
        assert options.disable_images is False
        assert options.silent_browser is False
        assert options.memory_limit == 512

    def test_chrome_options_invalid_memory(self):
        """Проверка валидации memory_limit."""
        with pytest.raises(Exception):
            ChromeOptions(memory_limit=0)

        with pytest.raises(Exception):
            ChromeOptions(memory_limit=-1)

    def test_chrome_options_valid_memory(self):
        """Проверка допустимых значений memory_limit."""
        for value in [1, 100, 512, 1024, 2048]:
            options = ChromeOptions(memory_limit=value)
            assert options.memory_limit == value

    def test_chrome_options_binary_path_string(self):
        """Проверка binary_path как строка."""
        options = ChromeOptions(binary_path=pathlib.Path("/usr/bin/chrome"))
        assert isinstance(options.binary_path, pathlib.Path)

    def test_chrome_options_memory_limit_default(self):
        """Проверка memory_limit по умолчанию."""
        options = ChromeOptions()
        assert options.memory_limit > 0
        assert isinstance(options.memory_limit, int)


class TestChromeExceptions:
    """Тесты для исключений Chrome."""

    def test_chrome_exception_creation(self):
        """Проверка создания ChromeException."""
        exc = ChromeException("Test error")
        # Проверяем что базовый текст входит в сообщение исключения
        assert "Test error" in str(exc)

    def test_chrome_exception_inheritance(self):
        """Проверка наследования ChromeException."""
        exc = ChromeException("Test error")
        assert isinstance(exc, Exception)

    def test_chrome_path_not_found(self):
        """Проверка ChromePathNotFound."""
        exc = ChromePathNotFound("/usr/bin/chrome")
        assert "/usr/bin/chrome" in str(exc)
        assert isinstance(exc, ChromeException)

    def test_chrome_runtime_exception(self):
        """Проверка ChromeRuntimeException."""
        exc = ChromeRuntimeException("Runtime error")
        # Проверяем что базовый текст входит в сообщение исключения
        assert "Runtime error" in str(exc)
        assert isinstance(exc, ChromeException)

    def test_chrome_user_abort_exception(self):
        """Проверка ChromeUserAbortException."""
        exc = ChromeUserAbortException("User aborted")
        # Проверяем что базовый текст входит в сообщение исключения
        assert "User aborted" in str(exc)
        assert isinstance(exc, ChromeException)


class TestChromeRemote:
    """Тесты для ChromeRemote."""

    def test_chrome_remote_creation(self):
        """Проверка создания ChromeRemote."""
        options = ChromeOptions()
        chrome = ChromeRemote(options, response_patterns=[])
        assert chrome is not None

    def test_chrome_remote_with_custom_options(self):
        """Проверка ChromeRemote с кастомными настройками."""
        options = ChromeOptions(headless=True, disable_images=True, memory_limit=256)
        chrome = ChromeRemote(options, response_patterns=[])
        assert chrome is not None

    def test_chrome_remote_with_binary_path(self):
        """Проверка ChromeRemote с путём к бинарнику."""
        options = ChromeOptions(binary_path=pathlib.Path("/usr/bin/chrome"))
        chrome = ChromeRemote(options, response_patterns=[])
        assert chrome is not None


class TestChromeDefaultMemoryLimit:
    """Тесты для default_memory_limit."""

    def test_default_memory_limit_positive(self):
        """Проверка, что memory_limit положительное."""
        from parser_2gis.chrome.options import default_memory_limit

        limit = default_memory_limit()
        assert limit > 0

    def test_default_memory_limit_integer(self):
        """Проверка, что memory_limit целое число."""
        from parser_2gis.chrome.options import default_memory_limit

        limit = default_memory_limit()
        assert isinstance(limit, int)

    def test_default_memory_limit_reasonable(self):
        """Проверка, что memory_limit разумное (не слишком большое)."""
        from parser_2gis.chrome.options import default_memory_limit

        limit = default_memory_limit()
        # Ожидаем, что лимит будет в разумных пределах (1-64 GB в MB)
        assert 100 <= limit <= 64000


class TestChromeOptionsValidation:
    """Тесты для валидации ChromeOptions."""

    def test_all_fields_optional(self):
        """Проверка, что все поля необязательны."""
        options = ChromeOptions()
        assert isinstance(options, ChromeOptions)

    def test_partial_update(self):
        """Проверка частичного обновления."""
        options = ChromeOptions(headless=True)
        assert options.headless is True
        # Остальные поля должны быть по умолчанию
        assert options.start_maximized is False
        assert options.disable_images is True

    def test_boolean_fields(self):
        """Проверка булевых полей."""
        for headless in [True, False]:
            for start_maximized in [True, False]:
                for disable_images in [True, False]:
                    options = ChromeOptions(
                        headless=headless,
                        start_maximized=start_maximized,
                        disable_images=disable_images,
                    )
                    assert options.headless == headless
                    assert options.start_maximized == start_maximized
                    assert options.disable_images == disable_images
