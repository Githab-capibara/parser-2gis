"""Тесты для cache_utils."""

import hashlib
import zlib

import pytest

from parser_2gis.cache.cache_utils import (
    compute_crc32_cached,
    compute_data_json_hash,
    get_cache_size_mb,
    hash_url,
    is_cache_expired,
    parse_expires_at,
    validate_hash,
)


class TestComputeCrc32Cached:
    """Тесты compute_crc32_cached."""

    @pytest.mark.parametrize(
        "data_json_hash,data_json",
        [
            pytest.param("abc123", '{"key":"value"}', id="simple"),
            pytest.param("hash2", '{"a":1,"b":2}', id="nested"),
            pytest.param("hash3", "", id="empty"),
        ],
    )
    def test_compute_crc32_returns_int(self, data_json_hash, data_json):
        """compute_crc32_cached возвращает целое число."""
        result = compute_crc32_cached(data_json_hash, data_json)
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFFFFFF

    def test_same_data_same_crc(self):
        """Одинаковые данные дают одинаковый CRC."""
        crc1 = compute_crc32_cached("h1", "test_data")
        crc2 = compute_crc32_cached("h1", "test_data")
        assert crc1 == crc2

    def test_different_data_different_crc(self):
        """Разные данные дают разный CRC."""
        crc1 = compute_crc32_cached("h1", "data1")
        crc2 = compute_crc32_cached("h1", "data2")
        assert crc1 != crc2


class TestComputeDataJsonHash:
    """Тесты compute_data_json_hash."""

    def test_returns_sha256_hex(self):
        """compute_data_json_hash возвращает SHA256 хеш."""
        result = compute_data_json_hash('{"key":"value"}')
        assert isinstance(result, str)
        assert len(result) == 64
        # Проверяем что это валидный hex
        int(result, 16)

    def test_same_input_same_hash(self):
        """Одинаковый вход даёт одинаковый хеш."""
        h1 = compute_data_json_hash("test")
        h2 = compute_data_json_hash("test")
        assert h1 == h2

    def test_different_input_different_hash(self):
        """Разный вход даёт разный хеш."""
        h1 = compute_data_json_hash("data1")
        h2 = compute_data_json_hash("data2")
        assert h1 != h2

    def test_matches_hashlib_sha256(self):
        """Хеш совпадает с hashlib.sha256."""
        data = "test data"
        expected = hashlib.sha256(data.encode("utf-8")).hexdigest()
        result = compute_data_json_hash(data)
        assert result == expected


class TestHashUrl:
    """Тесты hash_url."""

    @pytest.mark.parametrize(
        "url",
        [
            pytest.param("https://2gis.ru/moscow", id="https_url"),
            pytest.param("http://example.com", id="http_url"),
            pytest.param("https://2gis.ru/msk/search/apteki", id="complex_url"),
        ],
    )
    def test_hash_url_returns_sha256_hex(self, url):
        """hash_url возвращает SHA256 hex строку."""
        result = hash_url(url)
        assert isinstance(result, str)
        assert len(result) == 64
        int(result, 16)

    def test_hash_url_none_raises_valueerror(self):
        """hash_url с None выбрасывает ValueError."""
        with pytest.raises(ValueError):
            hash_url(None)

    def test_hash_url_empty_string_raises_valueerror(self):
        """hash_url с пустой строкой выбрасывает ValueError."""
        with pytest.raises(ValueError):
            hash_url("")

    def test_hash_url_non_string_raises_typeerror(self):
        """hash_url с не-string выбрасывает TypeError."""
        with pytest.raises(TypeError):
            hash_url(123)


class TestValidateHash:
    """Тесты validate_hash."""

    @pytest.mark.parametrize(
        "hash_val,expected",
        [
            pytest.param("a" * 64, True, id="valid_64_hex"),
            pytest.param("0" * 64, True, id="valid_zeros"),
            pytest.param("f" * 64, True, id="valid_fs"),
            pytest.param("a" * 63, False, id="too_short"),
            pytest.param("a" * 65, False, id="too_long"),
            pytest.param("g" * 64, False, id="invalid_hex_char"),
            pytest.param("", False, id="empty_string"),
        ],
    )
    def test_validate_hash(self, hash_val, expected):
        """Валидация хеша."""
        result = validate_hash(hash_val)
        assert result is expected


class TestParseExpiresAt:
    """Тесты parse_expires_at."""

    def test_valid_iso_format(self):
        """Парсинг валидной ISO даты."""
        result = parse_expires_at("2025-01-01T12:00:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

    def test_invalid_format_returns_none(self):
        """Парсинг невалидной даты возвращает None."""
        result = parse_expires_at("not_a_date")
        assert result is None


class TestIsCacheExpired:
    """Тесты is_cache_expired."""

    def test_none_expires_is_expired(self):
        """None expires_at считается истёкшим."""
        assert is_cache_expired(None) is True

    def test_past_date_is_expired(self):
        """Дата в прошлом считается истёкшей."""
        from datetime import datetime, timedelta

        past = datetime.now() - timedelta(hours=1)
        assert is_cache_expired(past) is True

    def test_future_date_not_expired(self):
        """Дата в будущем не считается истёкшей."""
        from datetime import datetime, timedelta

        future = datetime.now() + timedelta(hours=24)
        assert is_cache_expired(future) is False


class TestGetCacheSizeMb:
    """Тесты get_cache_size_mb."""

    def test_nonexistent_file_returns_zero(self, tmp_path):
        """Несуществующий файл возвращает 0.0."""
        non_existent = tmp_path / "nonexistent.db"
        result = get_cache_size_mb(non_existent)
        assert result == 0.0
