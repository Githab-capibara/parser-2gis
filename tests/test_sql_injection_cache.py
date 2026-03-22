"""Тесты для проверки SQL-инъекций и Unicode нормализации в cache.py."""

import unicodedata

from parser_2gis.cache import (
    _check_sql_injection_patterns,
    _normalize_unicode,
    _validate_cached_data,
)


class TestUnicodeNormalization:
    """Тесты для функции _normalize_unicode."""

    def test_nfc_normalization(self):
        """Unicode должен нормализовываться в форму NFC."""
        e_acute = "e\u0301"

        result = _normalize_unicode(e_acute)
        assert unicodedata.normalize("NFC", e_acute) == result

    def test_homoglyph_normalization(self):
        """Омоглифы должны нормализовываться."""
        latin_a = "A"
        cyrillic_a = "\u0410"

        normalized_latin = _normalize_unicode(latin_a)
        normalized_cyrillic = _normalize_unicode(cyrillic_a)

        assert normalized_latin != normalized_cyrillic


class TestSQLInjectionPatterns:
    """Тесты для функции _check_sql_injection_patterns."""

    def test_union_select_detected(self):
        """UNION SELECT должен быть обнаружен."""
        assert not _check_sql_injection_patterns(
            "SELECT * FROM users UNION SELECT password FROM admins"
        )
        assert not _check_sql_injection_patterns("1 UNION ALL SELECT NULL--")

    def test_or_1_equals_1_detected(self):
        """OR 1=1 должен быть обнаружен."""
        assert not _check_sql_injection_patterns("admin OR 1=1")
        assert not _check_sql_injection_patterns("1 OR 1=1")

    def test_and_1_equals_1_detected(self):
        """AND 1=1 должен быть обнаружен."""
        assert not _check_sql_injection_patterns("1 AND 1=1")

    def test_sql_comments_detected(self):
        """SQL комментарии должны быть обнаружены."""
        assert not _check_sql_injection_patterns("admin--")
        assert not _check_sql_injection_patterns("admin; DROP TABLE users--")

    def test_insert_into_detected(self):
        """INSERT INTO должен быть обнаружен."""
        assert not _check_sql_injection_patterns("INSERT INTO users VALUES ('hacker')")

    def test_delete_from_detected(self):
        """DELETE FROM должен быть обнаружен."""
        assert not _check_sql_injection_patterns("DELETE FROM users WHERE 1=1")

    def test_drop_table_detected(self):
        """DROP TABLE должен быть обнаружен."""
        assert not _check_sql_injection_patterns("DROP TABLE users")

    def test_safe_string_passes(self):
        """Безопасные строки должны проходить проверку."""
        assert _check_sql_injection_patterns("Normal text content")
        assert _check_sql_injection_patterns("Just some regular data")

    def test_case_insensitive_detection(self):
        """Проверка должна быть регистронезависимой."""
        assert not _check_sql_injection_patterns("union select")
        assert not _check_sql_injection_patterns("UNION SELECT")
        assert not _check_sql_injection_patterns("Or 1=1")


class TestCacheDataValidation:
    """Тесты для функции _validate_cached_data с SQL паттернами."""

    def test_sql_injection_in_dict_value_rejected(self):
        """SQL инъекция в значении словаря должна быть отклонена."""
        malicious_data = {"query": "SELECT * FROM users UNION SELECT password FROM admins"}
        assert not _validate_cached_data(malicious_data)

    def test_sql_injection_in_list_rejected(self):
        """SQL инъекция во вложенном словаре списка должна быть отклонена."""
        malicious_data = {"items": [{"query": "DROP TABLE users"}]}
        assert not _validate_cached_data(malicious_data)

    def test_nested_sql_injection_rejected(self):
        """Вложенная SQL инъекция должна быть отклонена."""
        malicious_data = {"level1": {"level2": {"query": "1 OR 1=1"}}}
        assert not _validate_cached_data(malicious_data)

    def test_normal_data_passes(self):
        """Нормальные данные должны проходить валидацию."""
        normal_data = {
            "name": "Test Company",
            "address": "123 Main St",
            "phone": "+7 495 123-45-67",
            "items": ["item1", "item2"],
            "metadata": {"key": "value"},
        }
        assert _validate_cached_data(normal_data)

    def test_unicode_homoglyph_rejected(self):
        """Unicode омоглифы должны обрабатываться корректно."""
        data = {
            "key": "\u0410"  # Cyrillic A
        }
        result = _validate_cached_data(data)
        assert result

    def test_proto_pollution_blocked(self):
        """Prototype pollution должен блокироваться."""
        malicious_data = {"__proto__": {"admin": True}}
        assert not _validate_cached_data(malicious_data)

    def test_constructor_pollution_blocked(self):
        """Constructor pollution должен блокироваться."""
        malicious_data = {"constructor": {"prototype": {"admin": True}}}
        assert not _validate_cached_data(malicious_data)
