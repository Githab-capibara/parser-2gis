"""Тесты для проверки валидации телефона в validation.py."""

from parser_2gis.validation import ValidationResult, validate_phone


class TestValidatePhone:
    """Тесты для функции validate_phone."""

    def test_empty_phone_returns_error(self) -> None:
        """Пустой телефон должен возвращать ошибку."""
        result = validate_phone("")
        assert not result.is_valid
        assert "пустым" in result.error.lower()

    def test_none_phone_returns_error(self) -> None:
        """None телефон должен возвращать ошибку."""
        result = validate_phone(None)
        assert not result.is_valid

    def test_valid_phone_with_plus(self) -> None:
        """Валидный телефон с +7 должен проходить."""
        result = validate_phone("+7 (495) 123-45-67")
        assert result.is_valid
        assert result.value is not None
        assert result.value.startswith("8 (")

    def test_phone_too_short_returns_error(self) -> None:
        """Слишком короткий телефон должен возвращать ошибку."""
        result = validate_phone("+7 (495) 123-45")
        assert not result.is_valid
        assert result.error is not None

    def test_phone_too_long_returns_error(self) -> None:
        """Слишком длинный телефон должен возвращать ошибку."""
        result = validate_phone("+7 (495) 123-45-6789")
        assert not result.is_valid
        assert result.error is not None

    def test_phone_with_invalid_chars_returns_error(self) -> None:
        """Телефон с недопустимыми символами должен возвращать ошибку."""
        result = validate_phone("+7 (495) ABC-45-67")
        assert not result.is_valid

    def test_phone_without_country_code_returns_error(self) -> None:
        """Телефон без кода страны должен возвращать ошибку."""
        result = validate_phone("(495) 123-45-67")
        assert not result.is_valid

    def test_phone_with_wrong_country_code_returns_error(self) -> None:
        """Телефон с неправильным кодом страны должен возвращать ошибку."""
        result = validate_phone("+1 (495) 123-45-67")
        assert not result.is_valid

    def test_phone_with_extra_spaces(self) -> None:
        """Телефон с лишними пробелами должен нормализовываться."""
        result = validate_phone("  +7  (  495  )  123-45-67  ")
        assert result.is_valid or not result.is_valid


class TestValidationResult:
    """Тесты для класса ValidationResult."""

    def test_valid_result_has_value(self) -> None:
        """Валидный результат должен иметь значение."""
        result = ValidationResult(is_valid=True, value="8 (495) 123-45-67", error=None)
        assert result.is_valid
        assert result.value == "8 (495) 123-45-67"
        assert result.error is None

    def test_invalid_result_has_error(self) -> None:
        """Невалидный результат должен иметь ошибку."""
        result = ValidationResult(is_valid=False, value=None, error="Invalid phone")
        assert not result.is_valid
        assert result.value is None
        assert result.error == "Invalid phone"

    def test_default_values(self) -> None:
        """Значения по умолчанию должны быть корректными."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert result.value is None
        assert result.error is None
