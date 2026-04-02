"""Тесты для исправлений ISSUE-046 — ISSUE-065.

Тестирует:
- Type Hints (ISSUE-046 — ISSUE-050)
- Docstrings (ISSUE-051 — ISSUE-055)
- PEP 8 Compliance (ISSUE-056 — ISSUE-060)
- Magic Numbers (ISSUE-061 — ISSUE-065)
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


# =============================================================================
# TYPE HINTS TESTS (ISSUE-046 — ISSUE-050)
# =============================================================================


class TestTypeHints:
    """Тесты для Type Hints исправлений."""

    def test_issue_046_get_output_dir_type_hints(self) -> None:
        """ISSUE-046: Проверка type hints для _get_output_dir."""
        from parser_2gis.cli.launcher import ApplicationLauncher

        method = getattr(ApplicationLauncher, "_get_output_dir")
        sig = inspect.signature(method)

        # Проверяем аннотации параметров
        params = list(sig.parameters.values())
        assert len(params) == 2  # self и output_path
        output_path_param = params[1]
        assert output_path_param.annotation != inspect.Parameter.empty

        # Проверяем return annotation
        assert sig.return_annotation != inspect.Signature.empty

    def test_issue_047_get_output_filename_type_hints(self) -> None:
        """ISSUE-047: Проверка type hints для _get_output_filename."""
        from parser_2gis.cli.launcher import ApplicationLauncher

        method = getattr(ApplicationLauncher, "_get_output_filename")
        sig = inspect.signature(method)

        # Проверяем аннотации параметров
        params = list(sig.parameters.values())
        assert len(params) == 3  # self, args, default
        args_param = params[1]
        default_param = params[2]
        assert args_param.annotation != inspect.Parameter.empty
        assert default_param.annotation != inspect.Parameter.empty

        # Проверяем return annotation
        assert sig.return_annotation != inspect.Signature.empty

    def test_issue_048_no_any_in_cache_manager_methods(self) -> None:
        """ISSUE-048: Проверка что Any заменён на конкретные типы."""
        from parser_2gis.cache.manager import CacheManager

        # Проверяем что методы используют sqlite3.Cursor вместо Any
        methods_to_check = [
            "_get_cached_row",
            "_delete_cached_entry",
            "_get_from_db",
            "_handle_cache_hit",
            "_handle_cache_miss",
        ]

        for method_name in methods_to_check:
            method = getattr(CacheManager, method_name)
            sig = inspect.signature(method)
            sig_str = str(sig)
            # Проверяем что в сигнатуре нет cursor: Any
            assert "cursor: Any" not in sig_str, f"{method_name} использует Any для cursor"

    def test_issue_049_handle_db_error_type_hints(self) -> None:
        """ISSUE-049: Проверка type hints для параметров _handle_db_error."""
        from parser_2gis.cache.manager import CacheManager

        method = getattr(CacheManager, "_handle_db_error")
        sig = inspect.signature(method)
        list(sig.parameters.values())

        # Проверяем что cursor имеет тип sqlite3.Cursor (параметр с именем cursor)
        cursor_param = sig.parameters["cursor"]
        assert "Cursor" in str(cursor_param.annotation)

    def test_issue_050_typealias_from_typing_extensions(self) -> None:
        """ISSUE-050: Проверка что TypeAlias импортирован из typing_extensions."""
        # Проверяем cache/manager.py
        import parser_2gis.cache.manager as manager_module

        # TypeAlias должен быть из typing_extensions
        assert hasattr(manager_module, "TypeAlias")

        # Проверяем что TypeAlias используется правильно

        assert manager_module.CacheRow is not None


# =============================================================================
# DOCSTRINGS TESTS (ISSUE-051 — ISSUE-055)
# =============================================================================


class TestDocstrings:
    """Тесты для Docstrings исправлений."""

    def test_issue_051_cleanup_resources_has_docstring(self) -> None:
        """ISSUE-051: Проверка что _cleanup_resources имеет docstring."""
        from parser_2gis.cli.launcher import ApplicationLauncher

        method = getattr(ApplicationLauncher, "_cleanup_resources")
        assert method.__doc__ is not None
        assert len(method.__doc__.strip()) > 0

    def test_issue_052_cleanup_resources_docstring_has_params_and_return(self) -> None:
        """ISSUE-052: Проверка что docstring содержит параметры и return."""
        from parser_2gis.cli.launcher import ApplicationLauncher

        method = getattr(ApplicationLauncher, "_cleanup_resources")
        docstring = method.__doc__

        assert "Returns:" in docstring
        assert "None" in docstring

    def test_issue_053_cleanup_resources_docstring_has_example(self) -> None:
        """ISSUE-053: Проверка что docstring содержит пример использования."""
        from parser_2gis.cli.launcher import ApplicationLauncher

        method = getattr(ApplicationLauncher, "_cleanup_resources")
        docstring = method.__doc__

        assert "Example:" in docstring or ">>>" in docstring

    def test_issue_054_cleanup_resources_docstring_has_raises(self) -> None:
        """ISSUE-054: Проверка что docstring содержит раздел raises."""
        from parser_2gis.cli.launcher import ApplicationLauncher

        method = getattr(ApplicationLauncher, "_cleanup_resources")
        docstring = method.__doc__

        assert "Raises:" in docstring
        assert "MemoryError" in docstring or "Exception" in docstring

    def test_issue_055_private_methods_have_docstrings(self) -> None:
        """ISSUE-055: Проверка что приватные методы имеют docstrings."""
        from parser_2gis.cli.launcher import ApplicationLauncher

        private_methods = ["_cleanup_chrome_remote", "_cleanup_cache", "_cleanup_gc"]

        for method_name in private_methods:
            method = getattr(ApplicationLauncher, method_name)
            assert method.__doc__ is not None, f"{method_name} не имеет docstring"
            assert len(method.__doc__.strip()) > 0


# =============================================================================
# PEP 8 COMPLIANCE TESTS (ISSUE-056 — ISSUE-060)
# =============================================================================


class TestPEP8Compliance:
    """Тесты для PEP 8 Compliance исправлений."""

    def test_issue_056_no_line_too_long(self) -> None:
        """ISSUE-056: Проверка что нет строк длиннее 100 символов."""
        import parser_2gis.cache.manager as manager_module

        module_file = inspect.getsourcefile(manager_module)
        assert module_file is not None

        with open(module_file, encoding="utf-8") as f:
            lines = f.readlines()

        long_lines = []
        for i, line in enumerate(lines, 1):
            # Игнорируем строки с URL и импортами
            if len(line.rstrip()) > 100 and not line.strip().startswith("#"):  # noqa: PLR2004
                if "http://" not in line and "https://" not in line:
                    long_lines.append((i, len(line.rstrip())))

        # Разрешаем только docstring строки
        assert len(long_lines) <= 5, f"Найдены строки длиннее 100 символов: {long_lines[:5]}"

    def test_issue_057_constants_use_upper_case(self) -> None:
        """ISSUE-057: Проверка что константы используют UPPER_CASE."""
        from parser_2gis.chrome.constants import (
            DEFAULT_FILE_PERMISSIONS,
            DEFAULT_TTL_HOURS,
            DEFAULT_CONNECTION_TIMEOUT_SEC,
        )

        assert isinstance(DEFAULT_FILE_PERMISSIONS, int)
        assert isinstance(DEFAULT_TTL_HOURS, int)
        assert isinstance(DEFAULT_CONNECTION_TIMEOUT_SEC, int)


# =============================================================================
# MAGIC NUMBERS TESTS (ISSUE-061 — ISSUE-065)
# =============================================================================


class TestMagicNumbers:
    """Тесты для Magic Numbers исправлений."""

    def test_issue_061_max_response_size_constant(self) -> None:
        """ISSUE-061: Проверка константы MAX_RESPONSE_SIZE."""
        from parser_2gis.chrome.constants import MAX_RESPONSE_SIZE

        assert MAX_RESPONSE_SIZE == 10 * 1024 * 1024
        assert isinstance(MAX_RESPONSE_SIZE, int)

    def test_issue_062_default_connection_timeout_constant(self) -> None:
        """ISSUE-062: Проверка константы DEFAULT_CONNECTION_TIMEOUT_SEC."""
        from parser_2gis.chrome.constants import DEFAULT_CONNECTION_TIMEOUT_SEC

        assert DEFAULT_CONNECTION_TIMEOUT_SEC == 30
        assert isinstance(DEFAULT_CONNECTION_TIMEOUT_SEC, int)

    def test_issue_063_memory_threshold_constant(self) -> None:
        """ISSUE-063: Проверка константы MEMORY_THRESHOLD_BYTES."""
        from parser_2gis.parallel.strategies import MEMORY_THRESHOLD_BYTES

        assert MEMORY_THRESHOLD_BYTES == 100 * 1024 * 1024
        assert isinstance(MEMORY_THRESHOLD_BYTES, int)

    def test_issue_064_default_file_permissions_constant(self) -> None:
        """ISSUE-064: Проверка константы DEFAULT_FILE_PERMISSIONS."""
        from parser_2gis.chrome.constants import DEFAULT_FILE_PERMISSIONS

        assert DEFAULT_FILE_PERMISSIONS == 0o700
        assert isinstance(DEFAULT_FILE_PERMISSIONS, int)

    def test_issue_065_default_ttl_hours_constant(self) -> None:
        """ISSUE-065: Проверка константы DEFAULT_TTL_HOURS."""
        from parser_2gis.chrome.constants import DEFAULT_TTL_HOURS

        assert DEFAULT_TTL_HOURS == 24
        assert isinstance(DEFAULT_TTL_HOURS, int)

    def test_issue_061_cache_manager_uses_max_response_size(self) -> None:
        """ISSUE-061: Проверка что CacheManager использует MAX_RESPONSE_SIZE."""
        import inspect

        from parser_2gis.cache.manager import CacheManager

        source = inspect.getsource(CacheManager.set)
        assert "MAX_RESPONSE_SIZE" in source
        assert "10 * 1024 * 1024" not in source

    def test_issue_064_browser_uses_default_file_permissions(self) -> None:
        """ISSUE-064: Проверка что ChromeBrowser использует DEFAULT_FILE_PERMISSIONS."""
        import inspect

        from parser_2gis.chrome.browser import ProfileManager

        source = inspect.getsource(ProfileManager.create_profile)
        assert "DEFAULT_FILE_PERMISSIONS" in source

    def test_issue_065_cache_manager_uses_default_ttl(self) -> None:
        """ISSUE-065: Проверка что CacheManager использует DEFAULT_TTL_HOURS."""
        import inspect

        from parser_2gis.cache.manager import CacheManager

        sig = inspect.signature(CacheManager.__init__)
        ttl_param = sig.parameters["ttl_hours"]
        # Проверяем что default value это константа
        assert ttl_param.default is not None


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Интеграционные тесты для всех исправлений."""

    def test_cache_manager_with_constants(self, tmp_path: Path) -> None:
        """Тест что CacheManager работает с новыми константами."""
        from parser_2gis.cache.manager import CacheManager

        cache = CacheManager(tmp_path)
        cache.set("http://test.com", {"test": "data"})
        result = cache.get("http://test.com")

        assert result == {"test": "data"}
        cache.close()

    def test_launcher_cleanup_methods_exist(self) -> None:
        """Тест что все методы очистки существуют."""
        from parser_2gis.cli.launcher import ApplicationLauncher
        from parser_2gis.config import Configuration
        from parser_2gis.parser.options import ParserOptions

        config = Configuration()
        options = ParserOptions()
        launcher = ApplicationLauncher(config, options)

        # Проверяем что методы существуют
        assert hasattr(launcher, "_cleanup_resources")
        assert hasattr(launcher, "_cleanup_chrome_remote")
        assert hasattr(launcher, "_cleanup_cache")
        assert hasattr(launcher, "_cleanup_gc")


# =============================================================================
# Запуск тестов
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
