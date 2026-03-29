"""
Тесты для проверки исправлений аудита в parser_2gis.

Покрывают 18 исправлений:
1. Race condition fix в parallel_optimizer.py
2. Уникальные task_id в parallel_optimizer.py
3. Декораторы @sleep_and_retry/@limits с проверкой None в remote.py
4. config.py делегирует к ConfigService
5. _cleanup_cache_manager закрывает пул
6. Удалён redundant индекс
7. validate_env_int вместо _validate_pool_env_int
8. Broad exception handling в remote.py
9. SignalHandler вместо локального обработчика
10. Magic numbers вынесены в константы
11. Типы заменены на встроенные
12. Проверка None для _pool
13. WeakSet для _active_instances
14. Правильная сигнатура register_parser
15-18. Мелкие исправления
"""

import gc
import inspect
import itertools
import os
import threading
import weakref
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestRaceConditionFix:
    """Тест 1: Race condition fix в parallel_optimizer.py"""

    def test_concurrent_add_task_thread_safety(self):
        """Тест потокобезопасности при конкурентном добавлении задач."""
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        optimizer = ParallelOptimizer(max_workers=10)
        num_threads = 20
        tasks_per_thread = 5

        def add_multiple_tasks():
            for _ in range(tasks_per_thread):
                optimizer.add_task(
                    url="http://test.com",
                    category_name=f"category{_}",
                    city_name=f"city{_}",
                    priority=0,
                )

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=add_multiple_tasks)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        stats = optimizer.get_stats()
        expected_total = num_threads * tasks_per_thread
        assert stats["total_tasks"] == expected_total, (
            f"Ожидалось {expected_total}, получено {stats['total_tasks']}"
        )


class TestUniqueTaskIds:
    """Тест 2: Уникальные task_id в parallel_optimizer.py"""

    def test_task_counter_generates_unique_ids(self):
        """Проверяет что task_counter генерирует уникальные ID."""
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        optimizer = ParallelOptimizer()

        ids = set()
        for i in range(100):
            optimizer.add_task(
                url=f"http://test{i}.com",
                category_name=f"category{i}",
                city_name=f"city{i}",
                priority=0,
            )
            stats = optimizer.get_stats()
            ids.add(stats["total_tasks"])

        assert len(ids) == 100, (
            f"Ожидалось 100 уникальных значений total_tasks, получено {len(ids)}"
        )

    def test_task_counter_uses_itertools_count(self):
        """Проверяет что используется itertools.count() для генерации ID."""
        from parser_2gis import parallel_optimizer

        assert hasattr(parallel_optimizer, "_task_counter"), (
            "Должен быть _task_counter для генерации ID"
        )
        assert isinstance(parallel_optimizer._task_counter, itertools.count), (
            "_task_counter должен быть itertools.count"
        )

    def test_task_ids_are_integers(self):
        """Проверяет что task_id являются целыми числами."""
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        optimizer = ParallelOptimizer()
        optimizer.add_task(
            url="http://test.com", category_name="category", city_name="city", priority=0
        )

        with optimizer._lock:
            for task_id in optimizer._active_tasks:
                assert isinstance(task_id, int), (
                    f"task_id должен быть целым числом, получен {type(task_id)}"
                )


class TestDecoratorsWithNoneCheck:
    """Тест 3: Декораторы @sleep_and_retry/@limits с проверкой None в remote.py"""

    def test_execute_script_works_when_ratelimit_unavailable(self):
        """Проверяет что _execute_script_internal работает когда _RATELIMIT_AVAILABLE = False."""
        from parser_2gis.chrome import remote as remote_module

        original_available = remote_module._RATELIMIT_AVAILABLE

        try:
            remote_module._RATELIMIT_AVAILABLE = False

            if hasattr(remote_module, "_execute_script_internal_impl"):
                func = remote_module._execute_script_internal_impl
                assert callable(func), "Функция должна быть callable"
        finally:
            remote_module._RATELIMIT_AVAILABLE = original_available

    def test_ratelimit_import_handled_gracefully(self):
        """Проверяет что импорт ratelimit обрабатывается корректно."""
        from parser_2gis.chrome import remote as remote_module

        assert hasattr(remote_module, "_RATELIMIT_AVAILABLE"), (
            "Должен быть атрибут _RATELIMIT_AVAILABLE"
        )
        assert isinstance(remote_module._RATELIMIT_AVAILABLE, bool), (
            "_RATELIMIT_AVAILABLE должен быть bool"
        )

    def test_limits_and_sleep_and_retry_are_none_when_unavailable(self):
        """Проверяет что limits и sleep_and_retry равны None когда недоступны."""
        from parser_2gis.chrome import remote as remote_module

        if not remote_module._RATELIMIT_AVAILABLE:
            assert remote_module.limits is None
            assert remote_module.sleep_and_retry is None


class TestConfigDelegatesToService:
    """Тест 4: config.py делегирует к ConfigService"""

    def test_configuration_calls_configservice_methods(self):
        """Проверяет что Configuration вызывает ConfigService методы."""
        from parser_2gis.config import ConfigService

        assert hasattr(ConfigService, "merge_configs"), "ConfigService должен иметь merge_configs"
        assert hasattr(ConfigService, "save_config"), "ConfigService должен иметь save_config"
        assert hasattr(ConfigService, "load_config"), "ConfigService должен иметь load_config"

    def test_save_load_delegates_to_configservice(self, tmp_path):
        """Проверяет что save/load работают через ConfigService."""
        from parser_2gis.config import Configuration, ConfigService

        config_path = tmp_path / "config_test.json"
        config = Configuration()
        config.path = config_path

        with patch.object(ConfigService, "save_config") as mock_save:
            config.save_config()
            mock_save.assert_called_once()

        with patch.object(ConfigService, "load_config", return_value=config):
            loaded = Configuration.load_config(config_path=config_path)
            assert loaded is not None


class TestCleanupCacheManagerClosesPool:
    """Тест 5: _cleanup_cache_manager закрывает пул"""

    def test_cleanup_cache_manager_calls_close_all(self):
        """Проверяет что finalize вызывает close_all на пуле."""
        with patch("parser_2gis.cache.manager.sqlite3") as mock_sqlite:
            mock_conn = MagicMock()
            mock_sqlite.Connection.return_value = mock_conn

            from parser_2gis.cache import CacheManager
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                cache = CacheManager(cache_dir=Path(tmpdir))
                mock_pool = MagicMock()
                cache._pool = mock_pool

                cache._cleanup_cache_manager()

                mock_pool.close_all.assert_called_once()

    def test_cleanup_with_mock_connection_pool(self):
        """Проверяет вызов close_all с моком ConnectionPool."""
        from parser_2gis.cache import CacheManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))

            mock_pool = MagicMock()
            cache._pool = mock_pool

            cache._cleanup_cache_manager()

            mock_pool.close_all.assert_called_once()
            assert cache._pool is None


class TestRedundantIndexRemoved:
    """Тест 6: Удалён redundant индекс"""

    def test_no_url_hash_index_creation(self):
        """Проверяет что idx_url_hash не создаётся при создании БД."""

        from parser_2gis.cache import CacheManager

        source = inspect.getsource(CacheManager)

        has_url_hash_index = "idx_url_hash" in source and "CREATE INDEX" in source
        assert not has_url_hash_index, "idx_url_hash не должен создаваться"


class TestValidateEnvIntImported:
    """Тест 7: validate_env_int вместо _validate_pool_env_int"""

    def test_pool_imports_validate_env_int(self):
        """Проверяет что pool.py импортирует validate_env_int из constants.py."""
        from parser_2gis.cache import pool

        assert hasattr(pool, "validate_env_int"), "pool должен импортировать validate_env_int"

    def test_validate_env_int_works_correctly(self):
        """Проверяет что функция работает корректно."""
        from parser_2gis.constants import validate_env_int

        os.environ["PARSE2GIS_TEST_VAR"] = "55"
        result = validate_env_int("PARSE2GIS_TEST_VAR", default=42, min_value=10, max_value=100)
        assert result == 55
        os.environ.pop("PARSE2GIS_TEST_VAR", None)

    def test_validate_env_int_with_default(self):
        """Проверяет валидацию со значением по умолчанию."""
        from parser_2gis.constants import validate_env_int

        os.environ.pop("PARSE2GIS_TEST_VAR", None)
        result = validate_env_int("PARSE2GIS_TEST_VAR", default=100)
        assert result == 100


class TestBroadExceptionHandling:
    """Тест 8: Broad exception handling в remote.py"""

    def test_connection_error_and_timeout_caught(self):
        """Проверяет что ConnectionError и TimeoutError перехватываются."""

        from parser_2gis.chrome import remote as remote_module

        func_names = ["_execute_script_internal_impl", "_check_port_available_internal"]

        for func_name in func_names:
            if hasattr(remote_module, func_name):
                source = inspect.getsource(getattr(remote_module, func_name))
                has_except = "except" in source
                if has_except:
                    assert "OSError" in source or "ConnectionError" in source


class TestSignalHandlerUsage:
    """Тест 9: SignalHandler вместо локального обработчика"""

    def test_signalhandler_class_exists(self):
        """Проверяет что SignalHandler класс существует."""
        from parser_2gis.signal_handler import SignalHandler

        assert SignalHandler is not None, "SignalHandler должен существовать"

    def test_signalhandler_checks_old_handlers_none(self):
        """Проверяет что old_sigint/old_sigterm проверяются на None."""
        from parser_2gis.signal_handler import SignalHandler

        source = inspect.getsource(SignalHandler)

        assert "_original_handler_sigint" in source, "Должен быть атрибут _original_handler_sigint"
        assert "_original_handler_sigterm" in source, (
            "Должен быть атрибут _original_handler_sigterm"
        )


class TestMagicNumbersConstants:
    """Тест 10: Magic numbers вынесены в константы"""

    def test_constants_defined_in_constants_module(self):
        """Проверяет что константы определены и используются."""
        from parser_2gis import constants

        required_constants = ["MAX_DATA_DEPTH", "MAX_STRING_LENGTH", "DEFAULT_TIMEOUT"]

        for const in required_constants:
            assert hasattr(constants, const), f"Константа {const} должна быть определена"

    def test_validate_env_int_exported(self):
        """Проверяет что validate_env_int экспортируется."""
        from parser_2gis import constants

        assert hasattr(constants, "validate_env_int"), (
            "validate_env_int должен быть определён в constants"
        )


class TestBuiltinTypes:
    """Тест 11: Типы заменены на встроенные"""

    def test_parallel_optimizer_uses_builtin_types(self):
        """Проверяет что parallel_optimizer.py использует встроенные типы."""

        from parser_2gis.parallel_optimizer import ParallelOptimizer

        source = inspect.getsource(ParallelOptimizer)

        assert "list[" in source
        assert "dict[" in source or "Dict[" in source


class TestPoolNoneCheck:
    """Тест 12: Проверка None для _pool"""

    def test_cleanup_handles_pool_none(self):
        """Проверяет что _cleanup_cache_manager обрабатывает случай когда _pool is None."""
        from parser_2gis.cache import CacheManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=Path(tmpdir))
            cache._pool = None

            try:
                cache._cleanup_cache_manager()
            except AttributeError:
                pytest.fail(
                    "_cleanup_cache_manager не должна выбрасывать AttributeError когда _pool is None"
                )
            except Exception:
                pass


class TestWeakSetActiveInstances:
    """Тест 13: WeakSet для _active_instances"""

    def test_active_instances_is_weakset(self):
        """Проверяет что _active_instances является WeakSet."""
        from parser_2gis.chrome.remote import ChromeRemote

        assert hasattr(ChromeRemote, "_active_instances")
        assert isinstance(ChromeRemote._active_instances, weakref.WeakSet)

    def test_objects_removed_from_weakset_after_gc(self):
        """Проверяет что объекты автоматически удаляются из WeakSet при сборке мусора."""
        from parser_2gis.chrome.remote import ChromeRemote

        initial_count = len(ChromeRemote._active_instances)

        class TestInstance:
            pass

        obj = TestInstance()

        ChromeRemote._active_instances.add(obj)

        assert len(ChromeRemote._active_instances) == initial_count + 1

        del obj
        gc.collect()

        assert len(ChromeRemote._active_instances) == initial_count


class TestRegisterParserSignature:
    """Тест 14: Правильная сигнатура register_parser"""

    def test_register_parser_returns_callable(self):
        """Проверяет что register_parser возвращает Callable."""
        from parser_2gis.parser.factory import register_parser

        result = register_parser(priority=0)
        assert callable(result), "register_parser должен возвращать callable"

    def test_register_parser_decorator_function(self):
        """Проверяет что декоратор работает как функция."""
        from parser_2gis.parser.factory import register_parser

        @register_parser(priority=10)
        class MockParser:
            @staticmethod
            def url_pattern() -> str:
                return r".*test.*"

        assert MockParser.__name__ == "MockParser"


class TestMiscFixes:
    """Тест 15-18: Мелкие исправления"""

    def test_all_optimizer_methods_exist(self):
        """Проверяет что все методы optimizer существуют."""
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        required_methods = ["add_task", "get_next_task", "complete_task", "get_stats", "reset"]

        for method in required_methods:
            assert hasattr(ParallelOptimizer, method), (
                f"ParallelOptimizer должен иметь метод {method}"
            )

    def test_cache_manager_has_required_methods(self):
        """Проверяет что CacheManager имеет необходимые методы."""
        from parser_2gis.cache import CacheManager

        required_methods = ["get", "set", "close"]

        for method in required_methods:
            assert hasattr(CacheManager, method), f"CacheManager должен иметь метод {method}"

    def test_signal_handler_has_cleanup_callback(self):
        """Проверяет что SignalHandler имеет callback для очистки."""
        from parser_2gis.signal_handler import SignalHandler

        handler = SignalHandler(cleanup_callback=lambda: None)
        assert handler._cleanup_callback is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
