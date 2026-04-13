"""Тесты для CacheDataValidator."""

import pytest

from parser_2gis.cache.validator import CacheDataValidator


class TestCacheDataValidatorConstruction:
    """Тесты конструирования CacheDataValidator."""

    def test_default_construction(self) -> None:
        """CacheDataValidator создаётся без ошибок."""
        validator = CacheDataValidator()
        assert validator is not None
        assert validator.max_depth > 0
        assert validator.max_string_length > 0


class TestCacheDataValidatorValidate:
    """Тесты метода validate."""

    @pytest.mark.parametrize(
        "data,expected",
        [
            pytest.param(None, True, id="none"),
            pytest.param(True, True, id="bool_true"),
            pytest.param(False, True, id="bool_false"),
            pytest.param(42, True, id="int"),
            pytest.param(3.14, True, id="float"),
            pytest.param("hello", True, id="simple_string"),
            pytest.param({}, True, id="empty_dict"),
            pytest.param({"key": "value"}, True, id="simple_dict"),
            pytest.param([], True, id="empty_list"),
            pytest.param([1, 2, 3], True, id="simple_list"),
            pytest.param(float("nan"), False, id="nan"),
            pytest.param(float("inf"), False, id="inf"),
            pytest.param({"__proto__": "attack"}, False, id="prototype_pollution"),
            pytest.param({"constructor": "attack"}, False, id="constructor_pollution"),
        ],
    )
    def test_validate(self, data, expected) -> None:
        """Валидация различных типов данных."""
        validator = CacheDataValidator()
        result = validator.validate(data)
        assert result is expected

    def test_validate_deep_dict_exceeds_depth(self) -> None:
        """Валидация глубоко вложенных данных превышает лимит."""
        validator = CacheDataValidator()
        # Создаём структуру с глубиной больше max_depth
        deep_data = {"level": 0}
        current = deep_data
        for i in range(validator.max_depth + 2):
            current["nested"] = {"level": i + 1}
            current = current["nested"]
        result = validator.validate(deep_data)
        assert result is False

    def test_validate_long_string_exceeds_limit(self) -> None:
        """Валидация длинной строки превышает лимит."""
        validator = CacheDataValidator()
        long_string = "a" * (validator.max_string_length + 1)
        result = validator.validate(long_string)
        assert result is False
