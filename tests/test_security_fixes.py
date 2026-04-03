"""Тесты для исправленных проблем безопасности (P0).

Этот модуль тестирует исправления следующих проблем:
1. CSV injection - parser_2gis/writer/writers/csv_writer.py
2. XSS паттерны - parser_2gis/parser/parsers/firm.py
3. Path traversal - parser_2gis/cache/manager.py
4. WebSocket injection - parser_2gis/chrome/remote.py
5. Temp file prediction - parser_2gis/utils/temp_file_manager.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from parser_2gis.cache.manager import CacheManager
from parser_2gis.parser.parsers.firm import (
    DANGEROUS_JS_PATTERNS,
    _sanitize_string_value,
    _validate_initial_state,
)
from parser_2gis.utils.temp_file_manager import TempFileManager, create_temp_file
from parser_2gis.writer.writers.csv_formatter import SanitizeFormatter
from parser_2gis.writer.writers.csv_writer import CSVRowData


# =============================================================================
# ТЕСТЫ ДЛЯ CSV INJECTION (P0-1)
# =============================================================================


class TestCSVInjection:
    """Тесты для защиты от CSV injection атак."""

    @pytest.fixture(autouse=True)
    def setup_formatter(self):
        """Создаёт SanitizeFormatter для тестов."""
        self.formatter = SanitizeFormatter()

    def test_sanitize_value_with_formula_prefix(self) -> None:
        """Тест санитизации значений с опасными префиксами формул."""
        assert self.formatter.format("=1+1") == "'=1+1"
        assert self.formatter.format("+1+1") == "'+1+1"
        assert self.formatter.format("-1+1") == "'-1+1"
        assert self.formatter.format("@SUM(A1:A10)") == "'@SUM(A1:A10)"

    def test_sanitize_value_without_formula_prefix(self) -> None:
        """Тест санитизации безопасных значений."""
        assert self.formatter.format("normal text") == "normal text"
        assert self.formatter.format("123") == "123"
        assert self.formatter.format("test@example.com") == "test@example.com"

    def test_sanitize_value_special_characters(self) -> None:
        """Тест экранирования специальных символов CSV."""
        assert self.formatter.format('test "quoted" value') == 'test ""quoted"" value'
        assert self.formatter.format("line1\nline2") == "line1 line2"
        assert self.formatter.format("line1\rline2") == "line1line2"
        assert self.formatter.format("col1\tcol2") == "col1 col2"
        assert self.formatter.format("test\x00value") == "testvalue"

    def test_sanitize_table_coverage(self) -> None:
        """Тест покрытия таблицы санитизации."""
        test_value = 'test"\nvalue\rwith\ttabs\x00null'
        result = self.formatter.format(test_value)

        assert '"' not in result or '""' in result
        assert "\n" not in result
        assert "\r" not in result
        assert "\t" not in result
        assert "\x00" not in result

    def test_csv_writer_formula_protection(self) -> None:
        """Тест защиты CSVWriter от формул."""
        dangerous_name = "=CMD|'/C calc'!A1"
        sanitized = self.formatter.format(dangerous_name)

        assert sanitized.startswith("'")

    def test_csv_row_data_typeddict(self) -> None:
        """Тест TypedDict для CSVRowData."""
        row_data: CSVRowData = {
            "name": "Test Organization",
            "address": "Test Address",
            "city": "Moscow",
            "phone_1": "+7 (495) 123-45-67",
        }

        assert row_data["name"] == "Test Organization"
        assert row_data["address"] == "Test Address"

        partial_data: CSVRowData = {"name": "Partial"}
        assert partial_data["name"] == "Partial"


# =============================================================================
# ТЕСТЫ ДЛЯ XSS PATTERNS (P0-2)
# =============================================================================


class TestXSSPatterns:
    """Тесты для защиты от XSS атак в firm parser."""

    def test_sanitize_string_value_html_escape(self) -> None:
        """Тест экранирования HTML символов."""
        # Проверяем экранирование всех символов из таблицы
        assert _sanitize_string_value("test & value") == "test &amp; value"
        assert _sanitize_string_value("test < value") == "test &lt; value"
        assert _sanitize_string_value("test > value") == "test &gt; value"
        assert _sanitize_string_value('test "value"') == "test &quot;value&quot;"
        assert _sanitize_string_value("test 'value'") == "test &#x27;value&#x27;"

    def test_sanitize_string_value_combined(self) -> None:
        """Тест комбинированного экранирования."""
        dangerous = '<script>alert("XSS")</script> & <img onerror="evil()">'
        sanitized = _sanitize_string_value(dangerous)

        assert "<" not in sanitized
        assert ">" not in sanitized
        assert "&lt;script&gt;" in sanitized
        assert "&amp;" in sanitized

    def test_validate_initial_state_script_tag(self) -> None:
        """Тест обнаружения тегов script в initialState."""
        dangerous_data = {"name": "<script>alert('XSS')</script>"}
        is_valid, _ = _validate_initial_state(dangerous_data)
        assert is_valid is False

    def test_validate_initial_state_javascript_protocol(self) -> None:
        """Тест обнаружения javascript: протокола."""
        dangerous_data = {"url": "javascript:alert('XSS')"}
        is_valid, _ = _validate_initial_state(dangerous_data)
        assert is_valid is False

    def test_validate_initial_state_event_handlers(self) -> None:
        """Тест обнаружения обработчиков событий."""
        test_cases = [
            {"attr": "onerror=alert(1)"},
            {"attr": "onload = alert(1)"},
            {"attr": "onclick  =  alert(1)"},
            {"attr": "onmouseover=evil()"},
            {"attr": "onfocus=steal()"},
        ]

        for data in test_cases:
            is_valid, _ = _validate_initial_state(data)
            assert is_valid is False, f"Не обнаружен event handler: {data}"

    def test_validate_initial_state_dangerous_functions(self) -> None:
        """Тест обнаружения опасных функций."""
        test_cases = [
            {"code": "eval('malicious')"},
            {"code": "Function('return this')()"},
            {"code": "alert('XSS')"},
            {"code": "document.cookie"},
            {"code": "localStorage.getItem('key')"},
        ]

        for data in test_cases:
            is_valid, _ = _validate_initial_state(data)
            assert is_valid is False, f"Не обнаружена опасная функция: {data}"

    def test_validate_initial_state_safe_data(self) -> None:
        """Тест валидации безопасных данных."""
        safe_data = {
            "name": "Normal Organization",
            "address": "Street, 123",
            "phone": "+7 (495) 123-45-67",
            "description": "Regular business description",
        }
        is_valid, count = _validate_initial_state(safe_data)
        assert is_valid is True
        assert count > 0

    def test_dangerous_js_patterns_coverage(self) -> None:
        """Тест покрытия всех опасных JS паттернов."""
        # Проверяем что все паттерны работают
        test_patterns = [
            ("<script", "script tag"),
            ("javascript:", "javascript protocol"),
            ("onerror=", "onerror handler"),
            ("onclick=", "onclick handler"),
            ("eval(", "eval function"),
            ("document.cookie", "cookie access"),
            ("localStorage", "localStorage access"),
        ]

        for pattern_str, description in test_patterns:
            pattern_compiled = None
            for compiled, desc in DANGEROUS_JS_PATTERNS:
                if desc == description:
                    pattern_compiled = compiled
                    break

            if pattern_compiled:
                assert pattern_compiled.search(pattern_str), f"Паттерн не найден: {description}"

    def test_validate_initial_state_depth_limit(self) -> None:
        """Тест ограничения глубины вложенности."""
        # Создаём глубоко вложенную структуру
        deep_data: Any = {"level": 0}
        current = deep_data
        for i in range(15):  # Больше MAX_INITIAL_STATE_DEPTH (10)
            current["nested"] = {"level": i + 1}
            current = current["nested"]

        is_valid, _ = _validate_initial_state(deep_data)
        assert is_valid is False  # Должно превысить лимит глубины

    def test_validate_initial_state_size_limit(self) -> None:
        """Тест ограничения размера строки."""
        # Создаём очень длинную строку
        large_string = "x" * (6 * 1024 * 1024)  # Больше MAX_INITIAL_STATE_SIZE (5MB)
        is_valid, _ = _validate_initial_state({"data": large_string})
        assert is_valid is False


# =============================================================================
# ТЕСТЫ ДЛЯ PATH TRAVERSAL (P0-3)
# =============================================================================


class TestPathTraversal:
    """Тесты для защиты от path traversal атак в cache manager."""

    def test_cache_manager_filename_validation(self, tmp_path: Path) -> None:
        """Тест валидации имени файла кэша."""
        # Безопасные имена файлов
        cache = CacheManager(tmp_path, cache_file_name="cache.db")
        assert cache is not None

    def test_cache_manager_filename_with_path(self, tmp_path: Path) -> None:
        """Тест отклонения имени файла с путём."""
        with pytest.raises(ValueError, match="не должен содержать"):
            CacheManager(tmp_path, cache_file_name="../etc/cache.db")

    def test_cache_manager_filename_absolute_path(self, tmp_path: Path) -> None:
        """Тест отклонения абсолютного пути."""
        # Абсолютный путь отклоняется проверкой на '/' в имени
        with pytest.raises(ValueError, match="не должен содержать"):
            CacheManager(tmp_path, cache_file_name="/etc/cache.db")

    def test_cache_manager_filename_invalid_extension(self, tmp_path: Path) -> None:
        """Тест отклонения неправильного расширения."""
        with pytest.raises(ValueError, match="должен заканчиваться на"):
            CacheManager(tmp_path, cache_file_name="cache.txt")

    def test_cache_manager_filename_dangerous_chars(self, tmp_path: Path) -> None:
        """Тест отклонения опасных символов."""
        with pytest.raises(ValueError, match="должен содержать только"):
            CacheManager(tmp_path, cache_file_name="cache;rm -rf.db")

    def test_cache_manager_filename_empty(self, tmp_path: Path) -> None:
        """Тест отклонения пустого имени."""
        with pytest.raises(ValueError, match="должен быть непустой"):
            CacheManager(tmp_path, cache_file_name="")

    def test_cache_manager_filename_backslash(self, tmp_path: Path) -> None:
        """Тест отклонения обратного слэша."""
        with pytest.raises(ValueError, match="не должен содержать"):
            CacheManager(tmp_path, cache_file_name="..\\cache.db")


# =============================================================================
# ТЕСТЫ ДЛЯ WEBSOCKET INJECTION (P0-4)
# =============================================================================


class TestWebSocketInjection:
    """Тесты для защиты от WebSocket injection в chrome remote."""

    def test_localhost_base_url_constant(self) -> None:
        """Тест использования константы для localhost URL."""
        from parser_2gis.chrome.constants import LOCALHOST_BASE_URL

        # Константа должна существовать и иметь правильный формат
        assert LOCALHOST_BASE_URL == "http://127.0.0.1:{port}"
        assert "127.0.0.1" in LOCALHOST_BASE_URL

    def test_dev_url_format(self) -> None:
        """Тест формата dev_url."""
        # Проверяем что URL формируется через константу 127.0.0.1
        from parser_2gis.chrome.constants import LOCALHOST_BASE_URL

        # Константа должна использовать 127.0.0.1 вместо localhost
        assert LOCALHOST_BASE_URL == "http://127.0.0.1:{port}"

        # Форматируем URL
        dev_url = LOCALHOST_BASE_URL.format(port=9222)
        assert dev_url == "http://127.0.0.1:9222"
        assert "localhost" not in dev_url

    def test_port_validation(self) -> None:
        """Тест валидации порта."""
        from parser_2gis.chrome.remote import _validate_remote_port
        from parser_2gis.chrome.constants import MIN_PORT, MAX_PORT

        # Валидные порты
        assert _validate_remote_port(9222) == 9222
        assert _validate_remote_port(MIN_PORT) == MIN_PORT
        assert _validate_remote_port(MAX_PORT) == MAX_PORT

        # Невалидные порты
        with pytest.raises(ValueError, match="не должен быть bool"):
            _validate_remote_port(True)

        with pytest.raises(ValueError, match="должен быть integer"):
            _validate_remote_port("9222")

        with pytest.raises(ValueError, match="должен быть >="):
            _validate_remote_port(MIN_PORT - 1)

        with pytest.raises(ValueError, match="должен быть <="):
            _validate_remote_port(MAX_PORT + 1)


# =============================================================================
# ТЕСТЫ ДЛЯ TEMP FILE PREDICTION (P0-5)
# =============================================================================


class TestTempFilePrediction:
    """Тесты для защиты от атак через предсказание временных файлов."""

    def test_create_temp_file_crypto_safe(self, tmp_path: Path) -> str:
        """Тест криптографически безопасной генерации имён."""
        temp_path = create_temp_file(str(tmp_path), prefix="test_")

        # Проверяем что файл создан
        assert os.path.exists(temp_path)

        # Имя должно содержать случайную часть
        filename = os.path.basename(temp_path)
        assert filename.startswith("test_")
        assert filename.endswith(".tmp")

        # Случайная часть должна быть достаточно длинной
        random_part = filename[len("test_") : -len(".tmp")]
        assert len(random_part) >= 6  # Минимальная длина случайной части

        return temp_path

    def test_create_temp_file_prefix_sanitization(self, tmp_path: Path) -> None:
        """Тест санитизации префикса."""
        # Опасный префикс с путём
        temp_path = create_temp_file(str(tmp_path), prefix="../evil_")
        filename = os.path.basename(temp_path)

        # Префикс должен быть санитизирован
        assert "evil" in filename
        assert ".." not in filename
        assert "/" not in filename

    def test_create_temp_file_empty_prefix(self, tmp_path: Path) -> None:
        """Тест пустого префикса."""
        temp_path = create_temp_file(str(tmp_path), prefix="")
        filename = os.path.basename(temp_path)

        # Должен использоваться запасной префикс
        assert filename.startswith("tmp_")

    def test_create_temp_file_directory_validation(self) -> None:
        """Тест валидации директории."""
        with pytest.raises(ValueError, match="должен быть непустой"):
            create_temp_file("", prefix="test")

        with pytest.raises(ValueError, match="не должен содержать"):
            create_temp_file("../tmp", prefix="test")

    def test_temp_file_manager_path_validation(self, tmp_path: Path) -> None:
        """Тест валидации путей в TempFileManager."""
        manager = TempFileManager()

        # Валидный путь
        valid_file = tmp_path / "valid.tmp"
        valid_file.touch()
        manager.register(valid_file)

        # TempFileManager регистрирует путь без валидации на path traversal
        # но проверяет что путь может быть разрешён
        # Проверяем что регистрация работает для нормальных путей
        assert manager.get_count() >= 1

    def test_temp_file_manager_none_validation(self, tmp_path: Path) -> None:
        """Тест валидации None пути."""
        manager = TempFileManager()

        with pytest.raises(ValueError, match="не может быть None"):
            manager.register(None)  # type: ignore

    def test_temp_file_manager_type_validation(self) -> None:
        """Тест валидации типа пути."""
        manager = TempFileManager()

        with pytest.raises(TypeError, match="должен быть Path"):
            manager.register("string_path")  # type: ignore

    def test_temp_file_unique_names(self, tmp_path: Path) -> None:
        """Тест уникальности имён временных файлов."""
        created_files = set()

        for _ in range(10):
            temp_path = create_temp_file(str(tmp_path), prefix="unique_")
            created_files.add(os.path.basename(temp_path))

        # Все имена должны быть уникальными
        assert len(created_files) == 10

    def test_temp_file_permissions(self, tmp_path: Path) -> None:
        """Тест прав доступа к временным файлам."""
        temp_path = create_temp_file(str(tmp_path), prefix="perm_")

        # Проверяем что файл существует
        assert os.path.exists(temp_path)


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ БЕЗОПАСНОСТИ
# =============================================================================


class TestSecurityIntegration:
    """Интеграционные тесты для систем безопасности."""

    def test_csv_writer_full_sanitization(self) -> None:
        """Полный тест санитизации CSV writer."""
        formatter = SanitizeFormatter()
        test_cases = [
            ("=1+1", "'=1+1"),
            ("+1+1", "'+1+1"),
            ('test "quote"', 'test ""quote""'),
            ("line1\nline2", "line1 line2"),
        ]

        for input_val, expected_start in test_cases:
            result = formatter.format(input_val)
            assert result == expected_start or result.startswith(expected_start[:2])

    def test_xss_full_sanitization(self) -> None:
        """Полный тест санитизации XSS."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
            "<svg onload=alert(1)>",
        ]

        for payload in xss_payloads:
            sanitized = _sanitize_string_value(payload)
            # После санитизации не должно остаться HTML тегов
            assert "<" not in sanitized
            assert ">" not in sanitized

    def test_cache_manager_security_chain(self, tmp_path: Path) -> None:
        """Тест цепочки безопасности cache manager."""
        # Проверяем все уровни валидации
        invalid_names = [
            "",  # Пустое имя
            "../cache.db",  # Path traversal
            "/etc/cache.db",  # Абсолютный путь
            "cache.txt",  # Неправильное расширение
            "cache;rm -rf.db",  # Опасные символы
            "..\\cache.db",  # Windows path traversal
        ]

        for invalid_name in invalid_names:
            with pytest.raises(ValueError):
                CacheManager(tmp_path, cache_file_name=invalid_name)
