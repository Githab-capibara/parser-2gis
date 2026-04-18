"""Тесты для проверки SQL-инъекций в cache validator."""

import pytest

from parser_2gis.cache.validator import CacheDataValidator


class TestSQLInjectionPatterns:
    """Тесты для метода _check_sql_injection_patterns."""

    @pytest.fixture(autouse=True)
    def setup_validator(self) -> None:
        """Создаёт экземпляр CacheDataValidator."""
        self.validator = CacheDataValidator()

    def test_union_select_detected(self) -> None:
        """UNION SELECT должен быть обнаружен."""
        assert not self.validator._check_sql_injection_patterns("SELECT * FROM users UNION SELECT password FROM admins")
        assert not self.validator._check_sql_injection_patterns("1 UNION ALL SELECT NULL--")

    def test_or_1_equals_1_detected(self) -> None:
        """OR 1=1 должен быть обнаружен."""
        assert not self.validator._check_sql_injection_patterns("admin OR 1=1")
        assert not self.validator._check_sql_injection_patterns("1 OR 1=1")

    def test_and_1_equals_1_detected(self) -> None:
        """AND 1=1 должен быть обнаружен."""
        assert not self.validator._check_sql_injection_patterns("1 AND 1=1")

    def test_sql_comments_detected(self) -> None:
        """SQL комментарии должны быть обнаружены."""
        assert not self.validator._check_sql_injection_patterns("admin--")
        assert not self.validator._check_sql_injection_patterns("admin; DROP TABLE users--")

    def test_insert_into_detected(self) -> None:
        """INSERT INTO должен быть обнаружен."""
        assert not self.validator._check_sql_injection_patterns("INSERT INTO users VALUES ('hacker')")

    def test_delete_from_detected(self) -> None:
        """DELETE FROM должен быть обнаружен."""
        assert not self.validator._check_sql_injection_patterns("DELETE FROM users WHERE 1=1")

    def test_drop_table_detected(self) -> None:
        """DROP TABLE должен быть обнаружен."""
        assert not self.validator._check_sql_injection_patterns("DROP TABLE users")

    def test_safe_string_passes(self) -> None:
        """Безопасные строки должны проходить проверку."""
        assert self.validator._check_sql_injection_patterns("Normal text content")
        assert self.validator._check_sql_injection_patterns("Just some regular data")

    def test_case_insensitive_detection(self) -> None:
        """Проверка должна быть регистронезависимой."""
        assert not self.validator._check_sql_injection_patterns("union select")
        assert not self.validator._check_sql_injection_patterns("UNION SELECT")
        assert not self.validator._check_sql_injection_patterns("Or 1=1")


class TestCacheDataValidation:
    """Тесты для метода validate с SQL паттернами."""

    @pytest.fixture(autouse=True)
    def setup_validator(self) -> None:
        """Создаёт экземпляр CacheDataValidator."""
        self.validator = CacheDataValidator()

    def test_sql_injection_in_dict_value_rejected(self) -> None:
        """SQL инъекция в значении словаря должна быть отклонена."""
        malicious_data = {"query": "SELECT * FROM users UNION SELECT password FROM admins"}
        assert not self.validator.validate(malicious_data)

    def test_sql_injection_in_list_rejected(self) -> None:
        """SQL инъекция во вложенном словаре списка должна быть отклонена."""
        malicious_data = {"items": [{"query": "DROP TABLE users"}]}
        assert not self.validator.validate(malicious_data)

    def test_nested_sql_injection_rejected(self) -> None:
        """Вложенная SQL инъекция должна быть отклонена."""
        malicious_data = {"level1": {"level2": {"query": "1 OR 1=1"}}}
        assert not self.validator.validate(malicious_data)

    def test_normal_data_passes(self) -> None:
        """Нормальные данные должны проходить валидацию."""
        normal_data = {
            "name": "Test Company",
            "address": "123 Main St",
            "phone": "+7 495 123-45-67",
            "items": ["item1", "item2"],
            "metadata": {"key": "value"},
        }
        assert self.validator.validate(normal_data)

    def test_unicode_homoglyph_accepted(self) -> None:
        """Unicode омоглифы должны обрабатываться корректно."""
        data = {"key": "\u0410"}  # Cyrillic A
        result = self.validator.validate(data)
        assert result

    def test_proto_pollution_blocked(self) -> None:
        """Prototype pollution должен блокироваться."""
        malicious_data = {"__proto__": {"admin": True}}
        assert not self.validator.validate(malicious_data)

    def test_constructor_pollution_blocked(self) -> None:
        """Constructor pollution должен блокироваться."""
        malicious_data = {"constructor": {"prototype": {"admin": True}}}
        assert not self.validator.validate(malicious_data)
