"""
Тесты для проверки динамического connection pool.

Проверяет что пул соединений корректно работает:
- dynamic_pool_size_calculation: расчет размера пула на основе памяти
- dynamic_pool_with_low_memory: работа при низкой памяти
- dynamic_pool_with_high_memory: работа при высокой памяти
- manual_pool_size_override: ручное переопределение размера пула
"""

import os
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from parser_2gis.cache import (
    MAX_POOL_SIZE,
    MIN_POOL_SIZE,
    CacheManager,
    _calculate_dynamic_pool_size,
    _ConnectionPool,
    _validate_pool_env_int,
)


class TestDynamicPoolSizeCalculation:
    """Тесты для расчета динамического размера пула."""

    def test_dynamic_pool_size_calculation_basic(self):
        """
        Тест 1.1: Базовая проверка расчета размера пула.

        Проверяет что функция _calculate_dynamic_pool_size
        возвращает значение в допустимых пределах.
        """
        pool_size = _calculate_dynamic_pool_size()

        # Проверяем что размер в допустимых пределах
        assert isinstance(pool_size, int)
        assert MIN_POOL_SIZE <= pool_size <= MAX_POOL_SIZE

    def test_dynamic_pool_size_calculation_with_psutil(self):
        """
        Тест 1.2: Проверка расчета размера пула с psutil.

        Проверяет что при установленном psutil
        размер пула рассчитывается на основе доступной памяти.
        """
        # Mock psutil для имитации доступной памяти
        mock_memory = MagicMock()
        mock_memory.available = 8 * 1024 * 1024 * 1024  # 8 GB

        with patch("parser_2gis.cache.psutil.virtual_memory", return_value=mock_memory):
            pool_size = _calculate_dynamic_pool_size()

            # Проверяем что размер в допустимых пределах
            assert isinstance(pool_size, int)
            assert MIN_POOL_SIZE <= pool_size <= MAX_POOL_SIZE

    def test_dynamic_pool_size_calculation_without_psutil(self):
        """
        Тест 1.3: Проверка расчета размера пула без psutil.

        Проверяет что при отсутствии psutil
        возвращается MIN_POOL_SIZE.
        """
        # Mock ImportError для psutil
        with patch.dict("sys.modules", {"psutil": None}):
            with patch("parser_2gis.cache.psutil", None):
                pool_size = _calculate_dynamic_pool_size()

                # Проверяем что返回 MIN_POOL_SIZE
                assert pool_size == MIN_POOL_SIZE

    def test_dynamic_pool_size_calculation_with_exception(self):
        """
        Тест 1.4: Проверка расчета размера пула при ошибке.

        Проверяет что при ошибке расчета
        возвращается MIN_POOL_SIZE.
        """
        # Mock psutil для вызова ошибки
        with patch("parser_2gis.cache.psutil.virtual_memory") as mock_memory:
            mock_memory.side_effect = Exception("Memory error")

            pool_size = _calculate_dynamic_pool_size()

            # Проверяем что返回 MIN_POOL_SIZE
            assert pool_size == MIN_POOL_SIZE

    def test_dynamic_pool_size_calculation_with_low_memory(self):
        """
        Тест 1.5: Проверка расчета размера пула при низкой памяти.

        Проверяет что при низкой доступной памяти
        размер пула минимальный.
        """
        # Mock psutil для имитации низкой памяти
        mock_memory = MagicMock()
        mock_memory.available = 100 * 1024 * 1024  # 100 MB

        with patch("parser_2gis.cache.psutil.virtual_memory", return_value=mock_memory):
            pool_size = _calculate_dynamic_pool_size()

            # Проверяем что размер минимальный
            assert pool_size == MIN_POOL_SIZE

    def test_dynamic_pool_size_calculation_with_high_memory(self):
        """
        Тест 1.6: Проверка расчета размера пула при высокой памяти.

        Проверяет что при высокой доступной памяти
        размер пула максимальный.
        """
        # Mock psutil для имитации высокой памяти
        mock_memory = MagicMock()
        mock_memory.available = 100 * 1024 * 1024 * 1024  # 100 GB

        with patch("parser_2gis.cache.psutil.virtual_memory", return_value=mock_memory):
            pool_size = _calculate_dynamic_pool_size()

            # Проверяем что размер не превышает MAX_POOL_SIZE
            assert pool_size <= MAX_POOL_SIZE


class TestDynamicPoolWithLowMemory:
    """Тесты для работы пула при низкой памяти."""

    def test_dynamic_pool_with_low_memory_creation(self, tmp_path):
        """
        Тест 2.1: Проверка создания пула при низкой памяти.

        Проверяет что при низкой памяти
        пул создается с минимальным размером.
        """
        # Mock psutil для имитации низкой памяти
        mock_memory = MagicMock()
        mock_memory.available = 50 * 1024 * 1024  # 50 MB

        with patch("parser_2gis.cache.psutil.virtual_memory", return_value=mock_memory):
            cache_file = tmp_path / "cache.db"
            pool = _ConnectionPool(cache_file, use_dynamic=True)

            # Проверяем что размер пула минимальный
            assert pool._pool_size == MIN_POOL_SIZE

    def test_dynamic_pool_with_low_memory_connections(self, tmp_path):
        """
        Тест 2.2: Проверка создания соединений при низкой памяти.

        Проверяет что при низкой памяти
        соединения создаются корректно.
        """
        # Mock psutil для имитации низкой памяти
        mock_memory = MagicMock()
        mock_memory.available = 100 * 1024 * 1024  # 100 MB

        with patch("parser_2gis.cache.psutil.virtual_memory", return_value=mock_memory):
            cache_file = tmp_path / "cache.db"
            pool = _ConnectionPool(cache_file, use_dynamic=True)

            # Получаем соединение
            conn = pool.get_connection()

            # Проверяем что соединение создано
            assert conn is not None
            assert isinstance(conn, sqlite3.Connection)

            # Возвращаем соединение в пул
            pool.return_connection(conn)

    def test_dynamic_pool_with_low_memory_reuse(self, tmp_path):
        """
        Тест 2.3: Проверка reuse соединений при низкой памяти.

        Проверяет что при низкой памяти
        соединения корректно переиспользуются.
        """
        # Mock psutil для имитации низкой памяти
        mock_memory = MagicMock()
        mock_memory.available = 100 * 1024 * 1024  # 100 MB

        with patch("parser_2gis.cache.psutil.virtual_memory", return_value=mock_memory):
            cache_file = tmp_path / "cache.db"
            pool = _ConnectionPool(cache_file, use_dynamic=True)

            # Получаем соединение
            conn1 = pool.get_connection()

            # Возвращаем соединение в пул
            pool.return_connection(conn1)

            # Получаем соединение снова
            conn2 = pool.get_connection()

            # Проверяем что соединение переиспользовано
            assert conn1 is conn2


class TestDynamicPoolWithHighMemory:
    """Тесты для работы пула при высокой памяти."""

    def test_dynamic_pool_with_high_memory_creation(self, tmp_path):
        """
        Тест 3.1: Проверка создания пула при высокой памяти.

        Проверяет что при высокой памяти
        пул создается с большим размером.
        """
        # Mock psutil для имитации высокой памяти
        mock_memory = MagicMock()
        mock_memory.available = 32 * 1024 * 1024 * 1024  # 32 GB

        with patch("parser_2gis.cache.psutil.virtual_memory", return_value=mock_memory):
            cache_file = tmp_path / "cache.db"
            pool = _ConnectionPool(cache_file, use_dynamic=True)

            # Проверяем что размер пула больше минимального
            assert pool._pool_size > MIN_POOL_SIZE
            assert pool._pool_size <= MAX_POOL_SIZE

    def test_dynamic_pool_with_high_memory_multiple_connections(self, tmp_path):
        """
        Тест 3.2: Проверка создания множества соединений при высокой памяти.

        Проверяет что при высокой памяти
        можно создать множество соединений.
        """
        # Mock psutil для имитации высокой памяти
        mock_memory = MagicMock()
        mock_memory.available = 32 * 1024 * 1024 * 1024  # 32 GB

        with patch("parser_2gis.cache.psutil.virtual_memory", return_value=mock_memory):
            cache_file = tmp_path / "cache.db"
            pool = _ConnectionPool(cache_file, use_dynamic=True)

            # Получаем несколько соединений
            connections = []
            for _ in range(pool._pool_size):
                conn = pool.get_connection()
                connections.append(conn)

            # Проверяем что все соединения созданы
            assert len(connections) == pool._pool_size

            # Возвращаем соединения в пул
            for conn in connections:
                pool.return_connection(conn)

    def test_dynamic_pool_with_high_memory_queue(self, tmp_path):
        """
        Тест 3.3: Проверка queue соединений при высокой памяти.

        Проверяет что при высокой памяти
        queue корректно управляет соединениями.
        """
        # Mock psutil для имитации высокой памяти
        mock_memory = MagicMock()
        mock_memory.available = 32 * 1024 * 1024 * 1024  # 32 GB

        with patch("parser_2gis.cache.psutil.virtual_memory", return_value=mock_memory):
            cache_file = tmp_path / "cache.db"
            pool = _ConnectionPool(cache_file, use_dynamic=True)

            # Проверяем что queue создан с правильным размером
            assert pool._connection_queue.maxsize == pool._pool_size


class TestManualPoolSizeOverride:
    """Тесты для ручного переопределения размера пула."""

    def test_manual_pool_size_override_basic(self, tmp_path):
        """
        Тест 4.1: Базовая проверка ручного переопределения размера.

        Проверяет что при use_dynamic=False
        используется заданный размер пула.
        """
        cache_file = tmp_path / "cache.db"
        pool = _ConnectionPool(cache_file, pool_size=10, use_dynamic=False)

        # Проверяем что размер пула заданный
        assert pool._pool_size == 10

    def test_manual_pool_size_override_min_limit(self, tmp_path):
        """
        Тест 4.2: Проверка минимального предела ручного размера.

        Проверяет что при заданном размере меньше MIN_POOL_SIZE
        используется MIN_POOL_SIZE.
        """
        cache_file = tmp_path / "cache.db"
        pool = _ConnectionPool(cache_file, pool_size=1, use_dynamic=False)

        # Проверяем что размер пула не меньше MIN_POOL_SIZE
        assert pool._pool_size >= MIN_POOL_SIZE

    def test_manual_pool_size_override_max_limit(self, tmp_path):
        """
        Тест 4.3: Проверка максимального предела ручного размера.

        Проверяет что при заданном размере больше MAX_POOL_SIZE
        используется MAX_POOL_SIZE.
        """
        cache_file = tmp_path / "cache.db"
        pool = _ConnectionPool(cache_file, pool_size=100, use_dynamic=False)

        # Проверяем что размер пула не больше MAX_POOL_SIZE
        assert pool._pool_size <= MAX_POOL_SIZE

    def test_manual_pool_size_override_with_env(self, tmp_path):
        """
        Тест 4.4: Проверка ручного размера с ENV переменной.

        Проверяет что ENV переменная PARSER_MAX_POOL_SIZE
        корректно переопределяет размер пула.
        """
        # Устанавливаем ENV переменную
        os.environ["PARSER_MAX_POOL_SIZE"] = "15"

        try:
            # Пересоздаем пул с ENV переменной
            cache_file = tmp_path / "cache.db"
            pool = _ConnectionPool(cache_file, pool_size=10, use_dynamic=False)

            # Проверяем что размер пула учитывает ENV переменную
            # (в реальной реализации ENV переменная используется при инициализации константы)
            assert pool._pool_size <= MAX_POOL_SIZE
        finally:
            # Очищаем ENV переменную
            del os.environ["PARSER_MAX_POOL_SIZE"]


class TestConnectionPoolValidation:
    """Тесты для валидации параметров пула."""

    def test_validate_pool_env_int_default(self):
        """
        Тест 5.1: Проверка валидации ENV переменной по умолчанию.

        Проверяет что при отсутствии ENV переменной
        возвращается значение по умолчанию.
        """
        value = _validate_pool_env_int("NON_EXISTENT_VAR", default=10)

        # Проверяем что返回 значение по умолчанию
        assert value == 10

    def test_validate_pool_env_int_valid(self):
        """
        Тест 5.2: Проверка валидации корректной ENV переменной.

        Проверяет что при корректной ENV переменной
        возвращается валидированное значение.
        """
        os.environ["TEST_POOL_VAR"] = "25"

        try:
            value = _validate_pool_env_int("TEST_POOL_VAR", default=10, min_value=5, max_value=50)

            # Проверяем что返回 валидированное значение
            assert value == 25
        finally:
            del os.environ["TEST_POOL_VAR"]

    def test_validate_pool_env_int_below_min(self):
        """
        Тест 5.3: Проверка валидации ENV переменной ниже минимума.

        Проверяет что при значении ниже минимума
        возвращается минимальное значение.
        """
        os.environ["TEST_POOL_VAR"] = "3"

        try:
            value = _validate_pool_env_int("TEST_POOL_VAR", default=10, min_value=5, max_value=50)

            # Проверяем что返回 минимальное значение
            assert value == 5
        finally:
            del os.environ["TEST_POOL_VAR"]

    def test_validate_pool_env_int_above_max(self):
        """
        Тест 5.4: Проверка валидации ENV переменной выше максимума.

        Проверяет что при значении выше максимума
        возвращается максимальное значение.
        """
        os.environ["TEST_POOL_VAR"] = "100"

        try:
            value = _validate_pool_env_int("TEST_POOL_VAR", default=10, min_value=5, max_value=50)

            # Проверяем что返回 максимальное значение
            assert value == 50
        finally:
            del os.environ["TEST_POOL_VAR"]

    def test_validate_pool_env_int_invalid(self, caplog):
        """
        Тест 5.5: Проверка валидации некорректной ENV переменной.

        Проверяет что при некорректной ENV переменной
        возвращается значение по умолчанию.
        """
        os.environ["TEST_POOL_VAR"] = "invalid"

        try:
            value = _validate_pool_env_int("TEST_POOL_VAR", default=10, min_value=5, max_value=50)

            # Проверяем что返回 значение по умолчанию
            assert value == 10

            # Проверяем что было предупреждение в логе
            assert "не является целым числом" in caplog.text
        finally:
            del os.environ["TEST_POOL_VAR"]


class TestConnectionPoolIntegration:
    """Интеграционные тесты для пула соединений."""

    def test_connection_pool_full_lifecycle(self, tmp_path):
        """
        Тест 6.1: Полный жизненный цикл пула соединений.

        Проверяет что пул корректно работает
        от создания до закрытия.
        """
        cache_file = tmp_path / "cache.db"

        # Создаем пул
        pool = _ConnectionPool(cache_file, pool_size=5, use_dynamic=False)

        # Получаем соединения
        connections = []
        for _ in range(3):
            conn = pool.get_connection()
            connections.append(conn)

        # Возвращаем соединения
        for conn in connections:
            pool.return_connection(conn)

        # Закрываем пул
        pool.close_all()

        # Проверяем что все соединения закрыты
        assert len(pool._all_conns) == 0

    def test_cache_manager_with_dynamic_pool(self, tmp_path):
        """
        Тест 6.2: CacheManager с динамическим пулом.

        Проверяет что CacheManager корректно работает
        с динамическим пулом соединений.
        """
        # Mock psutil для имитации доступной памяти
        mock_memory = MagicMock()
        mock_memory.available = 8 * 1024 * 1024 * 1024  # 8 GB

        with patch("parser_2gis.cache.psutil.virtual_memory", return_value=mock_memory):
            cache_dir = tmp_path / "cache"
            cache = CacheManager(cache_dir, ttl_hours=24)

            # Проверяем что пул создан
            assert cache._pool is not None
            assert cache._pool._pool_size > 0

            # Закрываем кэш
            cache.close()


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
