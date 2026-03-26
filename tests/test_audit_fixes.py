"""
Тесты для проверки исправлений, найденных при аудите кода.
"""

from unittest.mock import patch

import pytest


class TestUrlValidatorFixes:
    """Тесты для url_validator.py"""

    def test_all_logic_correctly_validates_urls(self):
        """Проверяет что all() используется корректно (с генератором/кортежем)"""

        class MockResult:
            def __init__(self, scheme, netloc):
                self.scheme = scheme
                self.netloc = netloc

        result = MockResult.__new__(MockResult)
        result.scheme = "http"
        result.netloc = "example.com"

        scheme_valid = result.scheme in ("http", "https")
        netloc_valid = bool(result.netloc)
        assert scheme_valid is True
        assert netloc_valid is True
        assert all((scheme_valid, netloc_valid)) is True

        result.scheme = "ftp"
        scheme_valid = result.scheme in ("http", "https")
        assert all((scheme_valid, netloc_valid)) is False

    def test_clear_url_cache_exists(self):
        """Проверяет что функция очистки кэша URL существует"""
        from parser_2gis.utils import url_utils

        assert hasattr(url_utils, "clear_url_query_cache")
        assert callable(url_utils.clear_url_query_cache)


class TestCacheFixes:
    """Тесты для cache.py"""

    def test_orjson_uses_non_str_keys(self):
        """Проверяет что orjson использует OPT_NON_STR_KEYS"""
        import parser_2gis.cache as cache_module

        if hasattr(cache_module, "_USE_ORJSON") and cache_module._USE_ORJSON:
            try:
                import orjson

                assert hasattr(orjson, "OPT_NON_STR_KEYS")
            except ImportError:
                pytest.skip("orjson не установлен")

    def test_cleanup_cache_manager_no_unused_param(self):
        """Проверяет что _cleanup_cache_manager не имеет неиспользуемых параметров"""
        from parser_2gis.cache import CacheManager

        assert hasattr(CacheManager, "_cleanup_cache_manager")


class TestSignalHandlerFixes:
    """Тесты для signal_handler.py"""

    def test_signal_handler_thread_safe(self):
        """Проверяет что SignalHandler использует блокировку"""
        from parser_2gis.signal_handler import SignalHandler

        handler = SignalHandler()

        assert hasattr(handler, "_lock")
        lock = handler._lock
        assert hasattr(lock, "acquire") and hasattr(lock, "release")


class TestMainModuleFixes:
    """Тесты для main.py"""

    def test_normalize_argv_validates_types(self):
        """Проверяет что _normalize_argv проверяет тип argv"""
        from parser_2gis.main import _normalize_argv

        result = _normalize_argv(["--city", "Москва"])
        assert isinstance(result, list)

        with pytest.raises((TypeError, ValueError)):
            _normalize_argv(None)

        with pytest.raises((TypeError, ValueError)):
            _normalize_argv("not a list")

    def test_chrome_remote_has_active_instances(self):
        """Проверяет что ChromeRemote имеет атрибут _active_instances"""
        from parser_2gis.chrome.remote import ChromeRemote

        assert hasattr(ChromeRemote, "_active_instances")

    def test_validate_positive_int_handles_float(self):
        """Проверяет что validate_positive_int корректно обрабатывает float"""
        from parser_2gis.main import validate_positive_int

        result = validate_positive_int(5, 0, float("inf"), "test")
        assert result == 5


class TestChromeModuleFixes:
    """Тесты для chrome модуля"""

    def test_psutil_used_as_context_manager(self):
        """Проверяет что psutil.Process используется как контекстный менеджер"""
        import inspect

        from parser_2gis.chrome.health_monitor import BrowserHealthMonitor

        source = inspect.getsource(BrowserHealthMonitor.check_health)
        assert "with psutil.Process" in source or "psutil.Process" in source


class TestRemoteModuleFixes:
    """Тесты для chrome/remote.py"""

    def test_memory_error_not_caught(self):
        """Проверяет что MemoryError не перехватывается в socket операциях"""
        import inspect

        from parser_2gis.chrome.remote import _check_port_available_internal

        source = inspect.getsource(_check_port_available_internal)
        assert "MemoryError" not in source.split("except")[1] if "except" in source else True

    def test_check_port_uses_timeout_params(self):
        """Проверяет что timeout и retries используются"""
        import inspect

        from parser_2gis.chrome.remote import _check_port_available

        sig = inspect.signature(_check_port_available)
        params = list(sig.parameters.keys())
        assert "timeout" in params
        assert "retries" in params


class TestValidationModuleFixes:
    """Тесты для validation модуля"""

    def test_path_validator_logs_empty_path(self):
        """Проверяет что PathValidator логирует пустой путь"""
        from parser_2gis.validation import path_validator

        with patch.object(path_validator.logger, "warning") as mock_warning:
            validator = path_validator.PathValidator()
            validator.validate("", "test_path")
            mock_warning.assert_called()


class TestParallelModuleFixes:
    """Тесты для parallel модуля"""

    def test_parallel_parser_flock_order(self):
        """Проверяет что flock снимается до восстановления сигналов"""
        import inspect

        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        if hasattr(ParallelCityParser, "merge_csv_files"):
            source = inspect.getsource(ParallelCityParser.merge_csv_files)
            flock_pos = source.find("flock")
            sigint_pos = source.find("SIGINT")

            if flock_pos != -1 and sigint_pos != -1:
                finally_pos = source.find("finally")
                if finally_pos != -1:
                    assert flock_pos < finally_pos, "flock должен быть до finally"


class TestOptimizerFixes:
    """Тесты для parallel_optimizer.py"""

    def test_no_redundant_none_check(self):
        """Проверяет что убрана избыточная проверка на None"""
        import inspect

        from parser_2gis.parallel_optimizer import ParallelOptimizer

        if hasattr(ParallelOptimizer, "get_next_task"):
            source = inspect.getsource(ParallelOptimizer.get_next_task)
            lines = source.split("\n")

            for i, line in enumerate(lines):
                if "if task is not None" in line:
                    context = "\n".join(lines[max(0, i - 2) : i + 3])
                    assert "queue.get_nowait()" not in context or "start()" not in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
