"""Тесты для URLValidator."""

import pytest

from parser_2gis.validation.url_validator import clear_url_cache, is_valid_url, validate_url


class TestValidateUrl:
    """Тесты validate_url."""

    @pytest.mark.parametrize(
        "url,expected_valid",
        [
            pytest.param("https://2gis.ru/moscow", True, id="valid_https"),
            pytest.param("http://example.com/search/test", True, id="valid_http"),
            pytest.param(
                "https://2gis.ru/msk/search/apteki/filters/sort=name", True, id="complex_url"
            ),
            pytest.param("ftp://example.com", False, id="invalid_scheme"),
            pytest.param("://example.com", False, id="no_scheme"),
            pytest.param("https://", False, id="no_host"),
            pytest.param("http://localhost:8080", False, id="localhost"),
            pytest.param("http://127.0.0.1:9222", False, id="loopback_ip"),
            pytest.param("", False, id="empty_string"),
        ],
    )
    def test_validate_url(self, url, expected_valid) -> None:
        """Валидация URL."""
        result = validate_url(url)
        assert result.is_valid is expected_valid

    def test_long_url_exceeds_max_length(self) -> None:
        """URL длиннее 2048 символов невалиден."""
        long_url = "https://example.com/" + "a" * 3000
        result = validate_url(long_url)
        assert result.is_valid is False


class TestIsValidUrl:
    """Тесты is_valid_url."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            pytest.param("https://2gis.ru/moscow", True, id="valid"),
            pytest.param("http://localhost:8080", False, id="localhost"),
            pytest.param("ftp://example.com", False, id="invalid_scheme"),
        ],
    )
    def test_is_valid_url(self, url, expected) -> None:
        """Упрощённая проверка URL."""
        assert is_valid_url(url) is expected


class TestClearUrlCache:
    """Тесты clear_url_cache."""

    def test_clear_cache_no_error(self) -> None:
        """Очистка кэша не выбрасывает ошибок."""
        # Сначала валидируем URL чтобы.populate кэш
        validate_url("https://example.com")
        # Очищаем кэш — не должно быть ошибок
        clear_url_cache()
