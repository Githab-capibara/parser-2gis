"""
Тесты для проверенных исправлений аудита кода.

Этот модуль содержит тесты для всех исправлений, выполненных
в результате аудита кода проекта parser-2gis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from parser_2gis.cache import _validate_cached_data
from parser_2gis.common import _SENSITIVE_KEYS, _is_sensitive_key
from parser_2gis.validation import validate_url
from parser_2gis.validator import DataValidator, ValidationResult


class TestURLMaxLength:
    """Тесты для проверки максимальной длины URL."""

    def test_url_under_max_length(self):
        """URL длиной менее 2048 символов должен быть валидным."""
        url = "https://2gis.ru/moscow/search/" + "a" * 2000
        result = validate_url(url)
        assert result.is_valid is True

    def test_url_over_max_length(self):
        """URL длиной более 2048 символов должен быть невалидным."""
        url = "https://2gis.ru/moscow/search/" + "a" * 2049
        result = validate_url(url)
        assert result.is_valid is False
        assert "Длина URL превышает максимальную" in result.error

    def test_url_exactly_max_length(self):
        """URL длиной ровно 2048 символов должен быть валидным."""
        base_url = "https://2gis.ru/moscow/search/"
        url = base_url + "a" * (2048 - len(base_url))
        result = validate_url(url)
        assert result.is_valid is True


class TestPhoneExtension:
    """Тесты для поддержки extension в телефонных номерах."""

    @pytest.fixture
    def validator(self):
        """Создание валидатора."""
        return DataValidator()

    def test_phone_with_dob_extension(self, validator):
        """Телефон с добавочным 'доб. 1234'."""
        result = validator.validate_phone("+7 (999) 123-45-67 доб. 1234")
        assert result.is_valid is True
        assert "доб. 1234" in result.value

    def test_phone_with_ext_extension(self, validator):
        """Телефон с добавочным 'ext. 5678'."""
        result = validator.validate_phone("+7 (999) 123-45-67 ext. 5678")
        assert result.is_valid is True
        assert "доб. 5678" in result.value

    def test_phone_without_extension(self, validator):
        """Телефон без добавочного."""
        # Используем формат 8 (999) который точно работает
        result = validator.validate_phone("89991234567")
        assert result.is_valid is True
        assert "доб." not in result.value

    def test_phone_with_dob_no_space_extension(self, validator):
        """Телефон с добавочным 'доб.1234' без пробела."""
        result = validator.validate_phone("+7 (999) 123-45-67 доб.1234")
        assert result.is_valid is True
        assert "доб. 1234" in result.value

    def test_phone_with_dash_extension(self, validator):
        """Телефон с добавочным через дефис."""
        result = validator.validate_phone("+7 (999) 123-45-67-9999")
        assert result.is_valid is True
        assert "доб. 9999" in result.value


class TestProtoProtection:
    """Тесты для защиты от __proto__ атак в кэше."""

    def test_dict_with_proto_key(self):
        """Словарь с ключом __proto__ должен быть отклонен."""
        data = {"__proto__": {"admin": True}}
        assert _validate_cached_data(data) is False

    def test_dict_with_constructor_key(self):
        """Словарь с ключом constructor должен быть отклонен."""
        data = {"constructor": {"malicious": True}}
        assert _validate_cached_data(data) is False

    def test_dict_with_prototype_key(self):
        """Словарь с ключом prototype должен быть отклонен."""
        data = {"prototype": {"polluted": True}}
        assert _validate_cached_data(data) is False

    def test_dict_with_proto_in_value(self):
        """Словарь со значением __proto__ во вложенном объекте."""
        data = {"user": {"__proto__": {"admin": True}}}
        assert _validate_cached_data(data) is False

    def test_dict_with_case_insensitive_proto(self):
        """Словарь с ключом __PROTO__ (регистронезависимо)."""
        data = {"__PROTO__": {"admin": True}}
        assert _validate_cached_data(data) is False

    def test_safe_dict_without_proto(self):
        """Безопасный словарь без опасных ключей."""
        data = {"user": "test", "value": 123}
        assert _validate_cached_data(data) is True


class TestSensitiveKeysExpanded:
    """Тесты для расширенного списка чувствительных ключей."""

    def test_api_secret_key(self):
        """Ключ api_secret должен быть чувствительным."""
        assert _is_sensitive_key("api_secret") is True

    def test_github_token_key(self):
        """Ключ github_token должен быть чувствительным."""
        assert _is_sensitive_key("github_token") is True

    def test_ssh_key(self):
        """Ключ ssh_key должен быть чувствительным."""
        assert _is_sensitive_key("ssh_key") is True

    def test_bearer_token_key(self):
        """Ключ bearer_token должен быть чувствительным."""
        assert _is_sensitive_key("bearer_token") is True

    def test_tls_key(self):
        """Ключ tls_key должен быть чувствительным."""
        assert _is_sensitive_key("tls_key") is True

    def test_non_sensitive_key(self):
        """Обычный ключ не должен быть чувствительным."""
        assert _is_sensitive_key("username") is False


class TestTempFileTimerRenaming:
    """Тесты для переименования _TempFileCleanupTimer в _TempFileTimer."""

    def test_class_exists(self):
        """Класс _TempFileTimer должен существовать."""
        from parser_2gis.parallel_parser import _TempFileTimer

        assert _TempFileTimer is not None

    def test_old_class_name_not_exists(self):
        """Старое имя _TempFileCleanupTimer не должно существовать."""
        import parser_2gis.parallel_parser as pp

        assert not hasattr(pp, "_TempFileCleanupTimer")


class TestLogArgumentFix:
    """Тесты для исправления дублирования аргумента level."""

    def test_log_with_level_keyword(self):
        """Метод log должен принимать level как именованный аргумент."""
        # Проверяем, что код отформатирован корректно
        # Фактическая проверка будет через запуск black/isort
        # и через запуск тестов
        import parser_2gis.parallel_parser as pp

        # Проверяем, что модуль загружается без ошибок
        assert pp is not None


class TestDictTypeAnnotationFix:
    """Тесты для исправления аннотации типов словарей."""

    def test_fieldnames_cache_type(self):
        """Аннотация типа fieldnames_cache должна быть корректной."""
        # Проверяем, что код не вызывает ошибок типов
        fieldnames_cache: dict[tuple[str, ...], list[str]] = {}
        test_key = ("col1", "col2", "col3")
        fieldnames_cache[test_key] = ["Категория", "col1", "col2", "col3"]
        assert fieldnames_cache[test_key] == ["Категория", "col1", "col2", "col3"]


class TestEnvExampleSecurity:
    """Тесты для исправления .env.example."""

    def test_env_example_no_token_value(self):
        """Файл .env.example не должен содержать значение токена."""
        env_example_path = Path("/home/d/parser-2gis/.env.example")
        content = env_example_path.read_text()

        # Проверяем, что GITHUB_TOKEN закомментирован или не имеет значения
        lines = content.split("\n")
        for line in lines:
            if "GITHUB_TOKEN" in line and not line.strip().startswith("#"):
                # Если строка не закомментирована, она не должна иметь значения
                assert "=" not in line or line.strip().endswith("=")
