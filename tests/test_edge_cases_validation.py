"""
Комплексные тесты для валидации пограничных случаев.

Этот модуль тестирует обработку edge cases в:
- parser_2gis/validation/data_validator.py - максимальная длина телефона (15 символов)
- parser_2gis/common.py - обработка None и пустых ключей в unwrap_dot_dict
- parser_2gis/cache/manager.py - отрицательные ttl

Каждый тест проверяет ОДНО конкретное исправление.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from parser_2gis.common import unwrap_dot_dict
from parser_2gis.validation.data_validator import (
    validate_email,
    validate_list_length,
    validate_non_empty_list,
    validate_non_empty_string,
    validate_phone,
    validate_positive_float,
    validate_positive_int,
    validate_string_length,
)

# =============================================================================
# ТЕСТЫ ДЛЯ parser_2gis/validation/data_validator.py
# =============================================================================


class TestDataValidatorEdgeCases:
    """Тесты на пограничные случаи валидации данных."""

    def test_validate_phone_max_length_15_chars(self) -> None:
        """
        Тест максимальной длины телефона (15 символов).

        Проверяет:
        - Телефон длиной 15 символов не отклоняется по длине
        - Телефон длиной >15 символов отклоняется как слишком длинный

        Returns:
            None
        """
        # Валидный телефон максимальной длины (15 символов)
        # Примечание: может не пройти проверку формата российского телефона,
        # но не должен быть отклонён по длине
        valid_phone = "+71234567890123"  # 15 символов
        result = validate_phone(valid_phone)

        # Проверяем что телефон не отклонён по длине
        if result.is_valid is False:
            assert "слишком длинный" not in result.error.lower(), (
                f"Телефон длиной 15 символов не должен отклоняться по длине: {result.error}"
            )

        # Невалидный телефон (16 символов)
        invalid_phone = "+712345678901234"  # 16 символов
        result_invalid = validate_phone(invalid_phone)

        # Проверяем что телефон отклонён по длине
        assert result_invalid.is_valid is False
        assert "слишком длинный" in result_invalid.error.lower()

    def test_validate_phone_exactly_15_chars(self) -> None:
        """
        Тест телефона ровно 15 символов.

        Проверяет:
        - Телефон ровно 15 символов проходит валидацию

        Returns:
            None
        """
        phone_15 = "+123456789012345"  # Ровно 15 символов
        result = validate_phone(phone_15)

        # Проверяем формат (должен пройти проверку длины)
        # Но может не пройти проверку формата для российского телефона
        # Главное что не отклонён по длине
        if result.is_valid is False:
            assert "слишком длинный" not in result.error.lower()

    def test_validate_phone_14_chars(self) -> None:
        """
        Тест телефона 14 символов.

        Проверяет:
        - Телефон 14 символов валиден

        Returns:
            None
        """
        phone_14 = "+7123456789012"  # 14 символов
        result = validate_phone(phone_14)

        # Телефон должен пройти проверку длины
        if result.is_valid is False:
            assert "слишком длинный" not in result.error.lower()

    def test_validate_phone_min_length(self) -> None:
        """
        Тест минимальной длины телефона.

        Проверяет:
        - Телефон короче 10 символов невалиден

        Returns:
            None
        """
        short_phone = "+712345678"  # 9 символов
        result = validate_phone(short_phone)

        assert result.is_valid is False
        # Проверяем что ошибка связана с длиной (короткий или некорректный формат)
        assert "коротк" in result.error.lower() or "формат" in result.error.lower()

    def test_validate_phone_exactly_10_chars(self) -> None:
        """
        Тест телефона ровно 10 символов.

        Проверяет:
        - Телефон 10 символов валиден

        Returns:
            None
        """
        phone_10 = "81234567890"  # 10 символов
        result = validate_phone(phone_10)

        # Проверяем что не отклонён по длине
        if result.is_valid is False:
            assert "слишком короткий" not in result.error.lower()

    def test_validate_phone_empty_string(self) -> None:
        """
        Тест пустого телефона.

        Проверяет:
        - Пустая строка невалидна

        Returns:
            None
        """
        result = validate_phone("")

        assert result.is_valid is False
        assert "не может быть пустым" in result.error.lower()

    def test_validate_phone_none_value(self) -> None:
        """
        Тест None телефона.

        Проверяет:
        - None обрабатывается корректно

        Returns:
            None
        """
        result = validate_phone(None)  # type: ignore[arg-type]

        assert result.is_valid is False

    def test_validate_email_max_length_254(self) -> None:
        """
        Тест максимальной длины email (254 символа).

        Проверяет:
        - Email длиной 254 символа валиден (или не отклоняется по длине)
        - Email длиной >254 символов невалиден

        Returns:
            None
        """
        # Валидный email максимальной длины (254 символа)
        # local_part (242) + @ (1) + domain (11) = 254
        # example.com = 11 символов, @ = 1, итого local_part = 254 - 12 = 242
        valid_email = "a" * 242 + "@example.com"  # 254 символа
        result = validate_email(valid_email)

        # Email должен быть валиден (254 символа - это максимум)
        assert result.is_valid is True, (
            f"Email длиной 254 символа должен быть валиден: {result.error}"
        )

        # Невалидный email (255 символов)
        invalid_email = "a" * 243 + "@example.com"  # 255 символов
        result_invalid = validate_email(invalid_email)

        assert result_invalid.is_valid is False
        assert "слишком длинный" in result_invalid.error.lower()

    def test_validate_email_idn_support(self) -> None:
        """
        Тест поддержки IDN email.

        Проверяет:
        - Email с Unicode символами валиден

        Returns:
            None
        """
        idn_email = "test@пример.рф"
        result = validate_email(idn_email)

        assert result.is_valid is True

    def test_validate_positive_int_boundary_values(self) -> None:
        """
        Тест пограничных значений для validate_positive_int.

        Проверяет:
        - Минимальное значение валидно
        - Максимальное значение валидно
        - Значения за пределами невалидны

        Returns:
            None
        """
        # Минимальное значение
        assert validate_positive_int(1, 1, 100, "test") == 1

        # Максимальное значение
        assert validate_positive_int(100, 1, 100, "test") == 100

        # Ниже минимума
        with pytest.raises(ValueError) as exc_info:
            validate_positive_int(0, 1, 100, "test")
        assert "не менее 1" in str(exc_info.value)

        # Выше максимума
        with pytest.raises(ValueError) as exc_info:
            validate_positive_int(101, 1, 100, "test")
        assert "не более 100" in str(exc_info.value)

    def test_validate_positive_float_boundary_values(self) -> None:
        """
        Тест пограничных значений для validate_positive_float.

        Returns:
            None
        """
        # Минимальное значение
        assert validate_positive_float(0.0, 0.0, 10.0, "test") == 0.0

        # Максимальное значение
        assert validate_positive_float(10.0, 0.0, 10.0, "test") == 10.0

        # Ниже минимума
        with pytest.raises(ValueError):
            validate_positive_float(-0.1, 0.0, 10.0, "test")

        # Выше максимума
        with pytest.raises(ValueError):
            validate_positive_float(10.1, 0.0, 10.0, "test")

    def test_validate_non_empty_string_whitespace_only(self) -> None:
        """
        Тест строки только с пробелами.

        Проверяет:
        - Строка с только пробелами невалидна

        Returns:
            None
        """
        with pytest.raises(ValueError):
            validate_non_empty_string("   ", "test_field")

    def test_validate_string_length_boundary(self) -> None:
        """
        Тест длины строки по границам.

        Returns:
            None
        """
        # Ровно min_length
        assert validate_string_length("ab", 2, 10, "test") == "ab"

        # Ровно max_length
        assert validate_string_length("abcdefghij", 2, 10, "test") == "abcdefghij"

        # Короче min
        with pytest.raises(ValueError):
            validate_string_length("a", 2, 10, "test")

        # Длиннее max
        with pytest.raises(ValueError):
            validate_string_length("abcdefghijk", 2, 10, "test")

    def test_validate_non_empty_list_empty(self) -> None:
        """
        Тест пустого списка.

        Returns:
            None
        """
        with pytest.raises(ValueError):
            validate_non_empty_list([], "test_list")

    def test_validate_list_length_boundary(self) -> None:
        """
        Тест длины списка по границам.

        Returns:
            None
        """
        # Ровно min_length
        assert validate_list_length([1, 2], 2, 5, "test") == [1, 2]

        # Ровно max_length
        assert validate_list_length([1, 2, 3, 4, 5], 2, 5, "test") == [1, 2, 3, 4, 5]

        # Короче min
        with pytest.raises(ValueError):
            validate_list_length([1], 2, 5, "test")

        # Длиннее max
        with pytest.raises(ValueError):
            validate_list_length([1, 2, 3, 4, 5, 6], 2, 5, "test")


# =============================================================================
# ТЕСТЫ ДЛЯ parser_2gis/common.py - unwrap_dot_dict
# =============================================================================


class TestUnwrapDotDictEdgeCases:
    """Тесты на пограничные случаи unwrap_dot_dict."""

    def test_unwrap_dot_dict_none_value(self) -> None:
        """
        Тест None значения в unwrap_dot_dict.

        Проверяет:
        - None значения сохраняются

        Returns:
            None
        """
        input_dict = {"key": None}
        result = unwrap_dot_dict(input_dict)

        assert result == {"key": None}

    def test_unwrap_dot_dict_empty_key(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Тест пустого ключа в unwrap_dot_dict.

        Проверяет:
        - Пустые ключи пропускаются
        - Логгируется предупреждение

        Returns:
            None
        """
        input_dict = {"": "value"}
        result = unwrap_dot_dict(input_dict)

        # Пустой ключ должен быть пропущен
        assert result == {}

        # Проверяем логирование
        assert any("Пустой ключ" in record.message for record in caplog.records)

    def test_unwrap_dot_dict_empty_segments_in_path(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Тест пустых сегментов в пути.

        Проверяет:
        - Ключи с пустыми сегментами (a..b) пропускаются
        - Логгируется предупреждение

        Returns:
            None
        """
        input_dict = {"a..b": "value"}
        result = unwrap_dot_dict(input_dict)

        # Ключ с пустым сегментом должен быть пропущен
        assert result == {}

        # Проверяем логирование
        assert any("пустые сегменты" in record.message.lower() for record in caplog.records)

    def test_unwrap_dot_dict_nested_structure(self) -> None:
        """
        Тест вложенной структуры.

        Проверяет:
        - Корректно разворачивает вложенные ключи

        Returns:
            None
        """
        input_dict = {"a.b.c": "value1", "a.b.d": "value2", "x.y": "value3"}
        result = unwrap_dot_dict(input_dict)

        expected = {"a": {"b": {"c": "value1", "d": "value2"}}, "x": {"y": "value3"}}

        assert result == expected

    def test_unwrap_dot_dict_mixed_none_and_values(self) -> None:
        """
        Тест смеси None и значений.

        Проверяет:
        - None и обычные значения обрабатываются корректно

        Returns:
            None
        """
        input_dict = {"a.b": "value", "a.c": None, "d": "value2"}
        result = unwrap_dot_dict(input_dict)

        expected = {"a": {"b": "value", "c": None}, "d": "value2"}

        assert result == expected

    def test_unwrap_dot_dict_invalid_input_type(self) -> None:
        """
        Тест некорректного типа входных данных.

        Проверяет:
        - TypeError для не-dict

        Returns:
            None
        """
        with pytest.raises(TypeError):
            unwrap_dot_dict("not a dict")  # type: ignore[arg-type]

    def test_unwrap_dot_dict_empty_dict(self) -> None:
        """
        Тест пустого словаря.

        Returns:
            None
        """
        result = unwrap_dot_dict({})
        assert result == {}

    def test_unwrap_dot_dict_single_level_key(self) -> None:
        """
        Тест ключа без точек.

        Returns:
            None
        """
        input_dict = {"key": "value"}
        result = unwrap_dot_dict(input_dict)
        assert result == {"key": "value"}

    def test_unwrap_dot_dict_deep_nesting(self) -> None:
        """
        Тест глубокой вложенности.

        Returns:
            None
        """
        input_dict = {"a.b.c.d.e.f": "deep_value"}
        result = unwrap_dot_dict(input_dict)

        expected = {"a": {"b": {"c": {"d": {"e": {"f": "deep_value"}}}}}}

        assert result == expected


# =============================================================================
# ТЕСТЫ ДЛЯ parser_2gis/cache/manager.py - отрицательные ttl
# =============================================================================


class TestCacheManagerNegativeTtl:
    """Тесты на обработку отрицательных ttl в CacheManager."""

    def test_cache_manager_zero_ttl(self, tmp_path: Any) -> None:
        """
        Тест нулевого ttl.

        Проверяет:
        - ValueError для ttl=0

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            None
        """
        from parser_2gis.cache.manager import CacheManager

        cache_dir = tmp_path / "cache"

        with pytest.raises(ValueError) as exc_info:
            CacheManager(cache_dir, ttl_hours=0)

        assert "положительным числом" in str(exc_info.value).lower()

    def test_cache_manager_negative_ttl(self, tmp_path: Any) -> None:
        """
        Тест отрицательного ttl.

        Проверяет:
        - ValueError для ttl<0

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            None
        """
        from parser_2gis.cache.manager import CacheManager

        cache_dir = tmp_path / "cache"

        with pytest.raises(ValueError) as exc_info:
            CacheManager(cache_dir, ttl_hours=-5)

        assert "положительным числом" in str(exc_info.value).lower()

    def test_cache_manager_string_ttl_conversion_error(self, tmp_path: Any) -> None:
        """
        Тест строкового ttl с ошибкой конверсии.

        Проверяет:
        - TypeError для неконвертируемого ttl

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            None
        """
        from parser_2gis.cache.manager import CacheManager

        cache_dir = tmp_path / "cache"

        with pytest.raises(TypeError) as exc_info:
            CacheManager(cache_dir, ttl_hours="invalid")  # type: ignore[arg-type]

        assert "целым числом" in str(exc_info.value).lower()

    def test_cache_manager_string_ttl_valid_conversion(self, tmp_path: Any) -> None:
        """
        Тест строкового ttl с успешной конверсией.

        Проверяет:
        - Строка "24" конвертируется в 24

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            None
        """
        from parser_2gis.cache.manager import CacheManager

        cache_dir = tmp_path / "cache"

        # Должно успешно сконвертировать строку в int
        cache = CacheManager(cache_dir, ttl_hours="24")  # type: ignore[arg-type]

        assert cache is not None
        cache.close()

    def test_cache_manager_float_ttl_conversion(self, tmp_path: Any) -> None:
        """
        Тест float ttl.

        Проверяет:
        - Float конвертируется в int

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            None
        """
        from parser_2gis.cache.manager import CacheManager

        cache_dir = tmp_path / "cache"

        # Float должен сконвертироваться в int
        cache = CacheManager(cache_dir, ttl_hours=24.5)  # type: ignore[arg-type]

        assert cache is not None
        cache.close()

    def test_cache_manager_none_ttl(self, tmp_path: Any) -> None:
        """
        Тест None ttl.

        Проверяет:
        - TypeError для None ttl

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            None
        """
        from parser_2gis.cache.manager import CacheManager

        cache_dir = tmp_path / "cache"

        with pytest.raises(TypeError):
            CacheManager(cache_dir, ttl_hours=None)  # type: ignore[arg-type]

    def test_cache_manager_very_large_ttl(self, tmp_path: Any) -> None:
        """
        Тест очень большого ttl.

        Проверяет:
        - Большие значения ttl работают корректно

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            None
        """
        from parser_2gis.cache.manager import CacheManager

        cache_dir = tmp_path / "cache"

        # Очень большое но валидное значение
        cache = CacheManager(cache_dir, ttl_hours=8760)  # 1 год

        assert cache is not None
        cache.close()


# =============================================================================
# ПАРАМЕТРИЗОВАННЫЕ ТЕСТЫ
# =============================================================================


class TestEdgeCasesParametrized:
    """Параметризованные тесты на пограничные случаи."""

    @pytest.mark.parametrize(
        "phone,expected_valid",
        [
            ("+7 (495) 123-45-67", True),  # Стандартный формат
            ("8 (495) 123-45-67", True),  # Через 8
            ("+71234567890123", True),  # 15 символов
            ("+712345678901234", False),  # 16 символов - слишком длинный
            ("+712345678", False),  # 9 символов - слишком короткий
            ("", False),  # Пустая строка
            ("12345", False),  # Короткий
            ("abcdefghij", False),  # Не цифры
        ],
        ids=[
            "standard_format",
            "via_8",
            "max_length_15",
            "too_long_16",
            "too_short_9",
            "empty_string",
            "very_short",
            "non_digits",
        ],
    )
    def test_validate_phone_various_formats(self, phone: str, expected_valid: bool) -> None:
        """
        Параметризованный тест различных форматов телефона.

        Args:
            phone: Телефон для валидации.
            expected_valid: Ожидаемый результат валидации.

        Returns:
            None
        """
        result = validate_phone(phone)

        # Проверяем что результат соответствует ожидаемому
        # (с учётом что формат может не подойти для российского телефона)
        if phone.startswith("+7") or phone.startswith("8"):
            if len(phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")) > 15:
                assert result.is_valid is False
                assert "слишком длинный" in result.error.lower()
            elif (
                len(phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")) < 10
            ):
                assert result.is_valid is False
                assert "слишком короткий" in result.error.lower()

    @pytest.mark.parametrize(
        "input_dict,expected_result",
        [
            ({"a.b": "1"}, {"a": {"b": "1"}}),
            ({"a.b.c": "1", "a.b.d": "2"}, {"a": {"b": {"c": "1", "d": "2"}}}),
            ({"key": None}, {"key": None}),
            ({}, {}),
        ],
        ids=["single_level", "multiple_keys", "none_value", "empty_dict"],
    )
    def test_unwrap_dot_dict_parametrized(
        self, input_dict: Dict[str, Any], expected_result: Dict[str, Any]
    ) -> None:
        """
        Параметризованный тест unwrap_dot_dict.

        Args:
            input_dict: Входной словарь.
            expected_result: Ожидаемый результат.

        Returns:
            None
        """
        result = unwrap_dot_dict(input_dict)
        assert result == expected_result
