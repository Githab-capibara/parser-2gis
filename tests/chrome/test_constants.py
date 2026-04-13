"""Тесты для Chrome constants."""

import pytest

from parser_2gis.chrome.constants import (
    _DEFAULT_REMOTE_DEBUGGING_PORT_RANGE,
    _RATE_LIMIT_PERIOD,
    CHROME_NO_SANDBOX_FLAG,
    CHROME_STARTUP_DELAY,
    DEFAULT_MEMORY_LIMIT_MB,
    DEFAULT_STARTUP_DELAY_SEC,
    DEFAULT_TTL_HOURS,
    EXTERNAL_RATE_LIMIT_PERIOD,
    LOCALHOST_BASE_URL,
    MAX_PORT,
    MEMORY_FRACTION_FOR_V8,
    MIN_PORT,
)


class TestChromeConstantsExist:
    """Тесты существования всех констант."""

    @pytest.mark.parametrize(
        "name,value_type",
        [
            pytest.param("DEFAULT_MEMORY_LIMIT_MB", int, id="memory_limit"),
            pytest.param("DEFAULT_STARTUP_DELAY_SEC", (int, float), id="startup_delay"),
            pytest.param("CHROME_STARTUP_DELAY", (int, float), id="chrome_startup"),
            pytest.param("_DEFAULT_REMOTE_DEBUGGING_PORT", int, id="debug_port"),
            pytest.param("_DEFAULT_REMOTE_DEBUGGING_PORT_RANGE", tuple, id="port_range"),
            pytest.param("MAX_JS_CODE_LENGTH", int, id="max_js_length"),
            pytest.param("MAX_TOTAL_JS_SIZE", int, id="max_total_js"),
            pytest.param("_RATE_LIMIT_CALLS", int, id="rate_limit_calls"),
            pytest.param("_RATE_LIMIT_PERIOD", int, id="rate_limit_period"),
            pytest.param("MAX_RESPONSE_SIZE", int, id="max_response_size"),
            pytest.param("MEMORY_FRACTION_FOR_V8", float, id="memory_fraction"),
            pytest.param("EXTERNAL_RATE_LIMIT_CALLS", int, id="external_rate_calls"),
            pytest.param("EXTERNAL_RATE_LIMIT_PERIOD", int, id="external_rate_period"),
            pytest.param("_DEFAULT_REMOTE_DEBUGGING_PORT", int, id="default_port"),
            pytest.param("MIN_PORT", int, id="min_port"),
            pytest.param("MAX_PORT", int, id="max_port"),
            pytest.param("SECONDS_PER_HOUR", int, id="seconds_per_hour"),
            pytest.param("DEFAULT_NETWORK_TIMEOUT", int, id="network_timeout"),
            pytest.param("DEFAULT_TTL_HOURS", int, id="ttl_hours"),
            pytest.param("_DEFAULT_CONNECTION_TIMEOUT_SEC", int, id="connection_timeout"),
            pytest.param("LOCALHOST_BASE_URL", str, id="localhost_url"),
            pytest.param("_PORT_CACHE_MAXSIZE", int, id="port_cache_maxsize"),
        ],
    )
    def test_constant_exists_and_correct_type(self, name, value_type) -> None:
        """Константа существует и имеет правильный тип."""
        import parser_2gis.chrome.constants as constants_mod

        value = getattr(constants_mod, name)
        assert isinstance(value, value_type)


class TestChromeConstantsValues:
    """Тесты конкретных значений констант."""

    def test_default_memory_limit_is_2048(self) -> None:
        """DEFAULT_MEMORY_LIMIT_MB равен 2048."""
        assert DEFAULT_MEMORY_LIMIT_MB == 2048

    def test_default_startup_delay_matches_alias(self) -> None:
        """CHROME_STARTUP_DELAY совпадает с DEFAULT_STARTUP_DELAY_SEC."""
        assert CHROME_STARTUP_DELAY == DEFAULT_STARTUP_DELAY_SEC

    def test_port_range_min_less_than_max(self) -> None:
        """Минимальный порт в диапазоне меньше максимального."""
        min_port, max_port = _DEFAULT_REMOTE_DEBUGGING_PORT_RANGE
        assert min_port < max_port

    def test_min_port_is_1024(self) -> None:
        """MIN_PORT равен 1024."""
        assert MIN_PORT == 1024

    def test_max_port_is_65535(self) -> None:
        """MAX_PORT равен 65535."""
        assert MAX_PORT == 65535

    def test_localhost_url_contains_port_placeholder(self) -> None:
        """LOCALHOST_BASE_URL содержит плейсхолдер порта."""
        assert "{port}" in LOCALHOST_BASE_URL
        assert LOCALHOST_BASE_URL.format(port=9222) == "http://127.0.0.1:9222"

    def test_memory_fraction_is_less_than_one(self) -> None:
        """MEMORY_FRACTION_FOR_V8 меньше 1.0."""
        assert 0 < MEMORY_FRACTION_FOR_V8 < 1.0

    def test_rate_limit_period_is_positive(self) -> None:
        """_RATE_LIMIT_PERIOD положительный."""
        assert _RATE_LIMIT_PERIOD > 0

    def test_external_rate_limit_period_is_positive(self) -> None:
        """EXTERNAL_RATE_LIMIT_PERIOD положительный."""
        assert EXTERNAL_RATE_LIMIT_PERIOD > 0

    def test_ttl_hours_is_positive(self) -> None:
        """DEFAULT_TTL_HOURS положительный."""
        assert DEFAULT_TTL_HOURS > 0

    def test_chrome_no_sandbox_flag_is_correct(self) -> None:
        """CHROME_NO_SANDBOX_FLAG равен '--no-sandbox'."""
        assert CHROME_NO_SANDBOX_FLAG == "--no-sandbox"
        assert CHROME_NO_SANDBOX_FLAG.startswith("--")
        assert "sandbox" in CHROME_NO_SANDBOX_FLAG
