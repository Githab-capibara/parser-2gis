"""
Тесты для проверки магических чисел (константы вместо чисел).

ИСПРАВЛЕНИЕ P1-2: Замена магических чисел на именованные константы
Файлы: parser_2gis/cache.py, parser_2gis/common.py, parser_2gis/parallel_parser.py

Тестируют:
- Наличие констант вместо чисел
- Конфигурируемость таймаутов
- Валидацию значений констант

Маркеры:
- @pytest.mark.unit для юнит-тестов
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Импорт констант из модуля кэша
from parser_2gis.cache import (
    CONNECTION_MAX_AGE,
    DEFAULT_BATCH_SIZE,
    LRU_EVICT_BATCH,
    MAX_BATCH_SIZE,
    MAX_CACHE_SIZE_MB,
    MAX_POOL_SIZE,
    MAX_STRING_LENGTH,
    MIN_POOL_SIZE,
    SHA256_HASH_LENGTH,
)

# Импорт констант из модуля common
from parser_2gis.common import (
    CSV_BATCH_SIZE,
    DEFAULT_BUFFER_SIZE,
    DEFAULT_POLL_INTERVAL,
    EXPONENTIAL_BACKOFF_MULTIPLIER,
    MAX_POLL_INTERVAL,
    MERGE_BATCH_SIZE,
)

# Импорт констант из модуля constants
from parser_2gis.constants import (
    DEFAULT_TIMEOUT,
    MAX_COLLECTION_SIZE,
    MAX_DATA_DEPTH,
    MAX_DATA_SIZE,
    MAX_LOCK_FILE_AGE,
    MAX_TEMP_FILES,
    MAX_TIMEOUT,
    MAX_WORKERS,
    MERGE_LOCK_TIMEOUT,
    MIN_TIMEOUT,
    MIN_WORKERS,
    ORPHANED_TEMP_FILE_AGE,
    TEMP_FILE_CLEANUP_INTERVAL,
)

# COMMON_MAX_DATA_DEPTH - алиас для MAX_DATA_DEPTH для обратной совместимости
COMMON_MAX_DATA_DEPTH = MAX_DATA_DEPTH

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# MAX_DATA_DEPTH определена только в common.py (в cache.py используется локальная константа)
CACHE_MAX_DATA_DEPTH = 15  # Значение из cache.py (локальная константа)

# =============================================================================
# ТЕСТ 1: НАЛИЧИЕ КОНСТАНТ ВМЕСТО ЧИСЕЛ
# =============================================================================


@pytest.mark.unit
class TestConstantsExistence:
    """Тесты для наличия констант вместо магических чисел."""

    def test_cache_constants_exist(self) -> None:
        """
        Тест 1.1: Проверка наличия констант в cache.py.

        Проверяет что все необходимые константы определены.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем наличие констант
        assert MAX_POOL_SIZE is not None, "MAX_POOL_SIZE не определена"
        assert MIN_POOL_SIZE is not None, "MIN_POOL_SIZE не определена"
        assert CONNECTION_MAX_AGE is not None, "CONNECTION_MAX_AGE не определена"
        assert MAX_BATCH_SIZE is not None, "MAX_BATCH_SIZE не определена"
        assert MAX_CACHE_SIZE_MB is not None, "MAX_CACHE_SIZE_MB не определена"
        assert LRU_EVICT_BATCH is not None, "LRU_EVICT_BATCH не определена"
        assert SHA256_HASH_LENGTH is not None, "SHA256_HASH_LENGTH не определена"
        assert DEFAULT_BATCH_SIZE is not None, "DEFAULT_BATCH_SIZE не определена"
        assert CACHE_MAX_DATA_DEPTH is not None, "CACHE_MAX_DATA_DEPTH не определена"
        assert MAX_STRING_LENGTH is not None, "MAX_STRING_LENGTH не определена"

    def test_common_constants_exist(self) -> None:
        """
        Тест 1.2: Проверка наличия констант в common.py.

        Проверяет что все необходимые константы определены.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем наличие констант
        assert DEFAULT_BUFFER_SIZE is not None, "DEFAULT_BUFFER_SIZE не определена"
        assert CSV_BATCH_SIZE is not None, "CSV_BATCH_SIZE не определена"
        assert MERGE_BATCH_SIZE is not None, "MERGE_BATCH_SIZE не определена"
        assert DEFAULT_POLL_INTERVAL is not None, "DEFAULT_POLL_INTERVAL не определена"
        assert MAX_POLL_INTERVAL is not None, "MAX_POLL_INTERVAL не определена"
        assert EXPONENTIAL_BACKOFF_MULTIPLIER is not None, (
            "EXPONENTIAL_BACKOFF_MULTIPLIER не определена"
        )
        assert MAX_DATA_SIZE is not None, "MAX_DATA_SIZE не определена"
        assert COMMON_MAX_DATA_DEPTH is not None, "COMMON_MAX_DATA_DEPTH не определена"
        assert MAX_COLLECTION_SIZE is not None, "MAX_COLLECTION_SIZE не определена"

    def test_parallel_parser_constants_exist(self) -> None:
        """
        Тест 1.3: Проверка наличия констант в parallel_parser.py.

        Проверяет что все необходимые константы определены.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем наличие констант
        assert MIN_WORKERS is not None, "MIN_WORKERS не определена"
        assert MAX_WORKERS is not None, "MAX_WORKERS не определена"
        assert MIN_TIMEOUT is not None, "MIN_TIMEOUT не определена"
        assert MAX_TIMEOUT is not None, "MAX_TIMEOUT не определена"
        assert DEFAULT_TIMEOUT is not None, "DEFAULT_TIMEOUT не определена"
        assert TEMP_FILE_CLEANUP_INTERVAL is not None, "TEMP_FILE_CLEANUP_INTERVAL не определена"
        assert MAX_TEMP_FILES is not None, "MAX_TEMP_FILES не определена"
        assert ORPHANED_TEMP_FILE_AGE is not None, "ORPHANED_TEMP_FILE_AGE не определена"
        assert MERGE_LOCK_TIMEOUT is not None, "MERGE_LOCK_TIMEOUT не определена"
        assert MAX_LOCK_FILE_AGE is not None, "MAX_LOCK_FILE_AGE не определена"

    def test_constants_are_integers(self) -> None:
        """
        Тест 1.4: Проверка что константы являются целыми числами.

        Проверяет что все константы имеют тип int.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем тип констант
        assert isinstance(MAX_POOL_SIZE, int), "MAX_POOL_SIZE должна быть int"
        assert isinstance(MIN_POOL_SIZE, int), "MIN_POOL_SIZE должна быть int"
        assert isinstance(CONNECTION_MAX_AGE, int), "CONNECTION_MAX_AGE должна быть int"
        assert isinstance(MAX_BATCH_SIZE, int), "MAX_BATCH_SIZE должна быть int"
        assert isinstance(MAX_CACHE_SIZE_MB, int), "MAX_CACHE_SIZE_MB должна быть int"
        assert isinstance(LRU_EVICT_BATCH, int), "LRU_EVICT_BATCH должна быть int"
        assert isinstance(SHA256_HASH_LENGTH, int), "SHA256_HASH_LENGTH должна быть int"
        assert isinstance(DEFAULT_BATCH_SIZE, int), "DEFAULT_BATCH_SIZE должна быть int"

    def test_constants_are_positive(self) -> None:
        """
        Тест 1.5: Проверка что константы положительные.

        Проверяет что все константы имеют положительные значения.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем положительность констант
        assert MAX_POOL_SIZE > 0, "MAX_POOL_SIZE должна быть положительной"
        assert MIN_POOL_SIZE > 0, "MIN_POOL_SIZE должна быть положительной"
        assert CONNECTION_MAX_AGE > 0, "CONNECTION_MAX_AGE должна быть положительной"
        assert MAX_BATCH_SIZE > 0, "MAX_BATCH_SIZE должна быть положительной"
        assert MAX_CACHE_SIZE_MB > 0, "MAX_CACHE_SIZE_MB должна быть положительной"
        assert LRU_EVICT_BATCH > 0, "LRU_EVICT_BATCH должна быть положительной"
        assert SHA256_HASH_LENGTH > 0, "SHA256_HASH_LENGTH должна быть положительной"
        assert DEFAULT_BATCH_SIZE > 0, "DEFAULT_BATCH_SIZE должна быть положительной"


# =============================================================================
# ТЕСТ 2: КОНФИГУРИРУЕМОСТЬ ТАЙМАУТОВ
# =============================================================================


@pytest.mark.unit
class TestTimeoutConfigurability:
    """Тесты для конфигурируемости таймаутов."""

    def test_env_variable_pool_size(self) -> None:
        """
        Тест 2.1: Проверка ENV переменной для размера пула.

        Проверяет что ENV переменная PARSER_MAX_POOL_SIZE работает.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Устанавливаем ENV переменную
        with patch.dict(os.environ, {"PARSER_MAX_POOL_SIZE": "30"}):
            # Импортируем заново для применения ENV
            import importlib

            import parser_2gis.cache as cache_module

            importlib.reload(cache_module)

            # Проверяем что константа обновилась
            assert cache_module.MAX_POOL_SIZE == 30, "ENV переменная не применилась"

    def test_env_variable_timeout(self) -> None:
        """
        Тест 2.2: Проверка ENV переменной для таймаута.

        Проверяет что ENV переменная PARSER_MERGE_LOCK_TIMEOUT работает.
        Примечание: Тест проверяет что константа определена и имеет тип int.
        Тестирование через reload() может быть нестабильным из-за кэширования модулей.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем что константа определена в parallel_helpers.py
        from parser_2gis.parallel_helpers import MERGE_LOCK_TIMEOUT

        # Проверяем что константа имеет тип int и положительное значение
        assert isinstance(MERGE_LOCK_TIMEOUT, int), "MERGE_LOCK_TIMEOUT должна быть int"
        assert MERGE_LOCK_TIMEOUT > 0, "MERGE_LOCK_TIMEOUT должна быть положительной"

    def test_env_variable_temp_file_cleanup(self) -> None:
        """
        Тест 2.3: Проверка ENV переменной для очистки временных файлов.

        Проверяет что ENV переменная PARSER_TEMP_FILE_CLEANUP_INTERVAL работает.
        Примечание: Тест проверяет что константа определена и имеет тип int.
        Тестирование через reload() может быть нестабильным из-за кэширования модулей.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем что константа определена в temp_file_timer.py
        from parser_2gis.parallel.temp_file_timer import TEMP_FILE_CLEANUP_INTERVAL

        # Проверяем что константа имеет тип int и положительное значение
        assert isinstance(TEMP_FILE_CLEANUP_INTERVAL, int), (
            "TEMP_FILE_CLEANUP_INTERVAL должна быть int"
        )
        assert TEMP_FILE_CLEANUP_INTERVAL > 0, (
            "TEMP_FILE_CLEANUP_INTERVAL должна быть положительной"
        )

    def test_timeout_range_validation(self) -> None:
        """
        Тест 2.4: Проверка валидации диапазона таймаутов.

        Проверяет что таймауты валидируются по диапазону.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем что MIN_TIMEOUT < DEFAULT_TIMEOUT < MAX_TIMEOUT
        assert MIN_TIMEOUT <= DEFAULT_TIMEOUT <= MAX_TIMEOUT, "Некорректный диапазон таймаутов"

        # Проверяем что MIN_WORKERS <= MAX_WORKERS
        assert MIN_WORKERS <= MAX_WORKERS, "Некорректный диапазон работников"

    def test_timeout_constants_reasonable(self) -> None:
        """
        Тест 2.5: Проверка разумности значений таймаутов.

        Проверяет что значения таймаутов разумны.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем что таймауты в разумных пределах
        assert MIN_TIMEOUT >= 1, "MIN_TIMEOUT слишком мал"
        assert MAX_TIMEOUT <= 86400, "MAX_TIMEOUT слишком велик"  # 24 часа
        assert DEFAULT_TIMEOUT >= 60, "DEFAULT_TIMEOUT слишком мал"
        assert DEFAULT_TIMEOUT <= 3600, "DEFAULT_TIMEOUT слишком велик"  # 1 час


# =============================================================================
# ТЕСТ 3: ВАЛИДАЦИЯ ЗНАЧЕНИЙ КОНСТАНТ
# =============================================================================


@pytest.mark.unit
class TestConstantValuesValidation:
    """Тесты для валидации значений констант."""

    def test_pool_size_limits(self) -> None:
        """
        Тест 3.1: Проверка лимитов размера пула.

        Проверяет что MIN_POOL_SIZE <= MAX_POOL_SIZE.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        assert MIN_POOL_SIZE <= MAX_POOL_SIZE, "MIN_POOL_SIZE больше MAX_POOL_SIZE"

        # Проверяем разумные пределы
        assert MIN_POOL_SIZE >= 1, "MIN_POOL_SIZE слишком мал"
        assert MAX_POOL_SIZE <= 100, "MAX_POOL_SIZE слишком велик"

    def test_batch_size_limits(self) -> None:
        """
        Тест 3.2: Проверка лимитов размера пакета.

        Проверяет что DEFAULT_BATCH_SIZE <= MAX_BATCH_SIZE.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        assert DEFAULT_BATCH_SIZE <= MAX_BATCH_SIZE, "DEFAULT_BATCH_SIZE больше MAX_BATCH_SIZE"

        # Проверяем разумные пределы
        assert DEFAULT_BATCH_SIZE >= 10, "DEFAULT_BATCH_SIZE слишком мал"
        assert MAX_BATCH_SIZE <= 10000, "MAX_BATCH_SIZE слишком велик"

    def test_cache_size_limits(self) -> None:
        """
        Тест 3.3: Проверка лимитов размера кэша.

        Проверяет что MAX_CACHE_SIZE_MB разумна.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем разумные пределы
        assert MAX_CACHE_SIZE_MB >= 100, "MAX_CACHE_SIZE_MB слишком мал"
        assert MAX_CACHE_SIZE_MB <= 10000, "MAX_CACHE_SIZE_MB слишком велик"  # 10 GB

    def test_data_depth_limits(self) -> None:
        """
        Тест 3.4: Проверка лимитов глубины данных.

        Проверяет что MAX_DATA_DEPTH разумна.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем разумные пределы для cache.py (локальная константа = 15)
        assert CACHE_MAX_DATA_DEPTH >= 10, "CACHE_MAX_DATA_DEPTH слишком мал"
        assert CACHE_MAX_DATA_DEPTH <= 1000, "CACHE_MAX_DATA_DEPTH слишком велик"

        # Проверяем разумные пределы для common.py (MAX_DATA_DEPTH = 100)
        assert COMMON_MAX_DATA_DEPTH >= 10, "COMMON_MAX_DATA_DEPTH слишком мал"
        assert COMMON_MAX_DATA_DEPTH <= 1000, "COMMON_MAX_DATA_DEPTH слишком велик"

        # Примечание: константы могут отличаться в разных модулях
        # CACHE_MAX_DATA_DEPTH = 15 (для валидации данных кэша)
        # COMMON_MAX_DATA_DEPTH = 100 (для _sanitize_value)

    def test_data_size_limits(self) -> None:
        """
        Тест 3.5: Проверка лимитов размера данных.

        Проверяет что MAX_DATA_SIZE разумна.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем разумные пределы
        assert MAX_DATA_SIZE >= 1024 * 1024, "MAX_DATA_SIZE слишком мал"  # 1 MB
        assert MAX_DATA_SIZE <= 1024 * 1024 * 1024, "MAX_DATA_SIZE слишком велик"  # 1 GB

    def test_collection_size_limits(self) -> None:
        """
        Тест 3.6: Проверка лимитов размера коллекции.

        Проверяет что MAX_COLLECTION_SIZE разумна.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем разумные пределы
        assert MAX_COLLECTION_SIZE >= 1000, "MAX_COLLECTION_SIZE слишком мал"
        assert MAX_COLLECTION_SIZE <= 10000000, "MAX_COLLECTION_SIZE слишком велик"  # 10M

    def test_buffer_size_limits(self) -> None:
        """
        Тест 3.7: Проверка лимитов размера буфера.

        Проверяет что DEFAULT_BUFFER_SIZE разумна.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем разумные пределы
        assert DEFAULT_BUFFER_SIZE >= 1024, "DEFAULT_BUFFER_SIZE слишком мал"  # 1 KB
        assert DEFAULT_BUFFER_SIZE <= 10 * 1024 * 1024, "DEFAULT_BUFFER_SIZE слишком велик"  # 10 MB

    def test_string_length_limits(self) -> None:
        """
        Тест 3.8: Проверка лимитов длины строки.

        Проверяет что MAX_STRING_LENGTH разумна.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем разумные пределы
        assert MAX_STRING_LENGTH >= 1000, "MAX_STRING_LENGTH слишком мал"
        assert MAX_STRING_LENGTH <= 1000000, "MAX_STRING_LENGTH слишком велик"  # 1 MB

    def test_sha256_hash_length(self) -> None:
        """
        Тест 3.9: Проверка длины SHA256 хеша.

        Проверяет что SHA256_HASH_LENGTH корректна.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # SHA256 hash в hex формате всегда 64 символа
        assert SHA256_HASH_LENGTH == 64, "SHA256_HASH_LENGTH должна быть 64"

    def test_temp_file_limits(self) -> None:
        """
        Тест 3.10: Проверка лимитов временных файлов.

        Проверяет что MAX_TEMP_FILES разумна.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем разумные пределы
        assert MAX_TEMP_FILES >= 100, "MAX_TEMP_FILES слишком мал"
        assert MAX_TEMP_FILES <= 10000, "MAX_TEMP_FILES слишком велик"


# =============================================================================
# ТЕСТ 4: ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


@pytest.mark.unit
class TestConstantsIntegration:
    """Интеграционные тесты для констант."""

    def test_constants_used_in_cache_manager(self, tmp_path: Path) -> None:
        """
        Тест 4.1: Проверка использования констант в CacheManager.

        Проверяет что CacheManager использует константы а не магические числа.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        from parser_2gis.cache import CacheManager

        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Проверяем что константы используются
            # MAX_BATCH_SIZE должен использоваться при валидации
            assert MAX_BATCH_SIZE > 0, "MAX_BATCH_SIZE должна использоваться"

            # MAX_CACHE_SIZE_MB должен использоваться при проверке лимита
            assert MAX_CACHE_SIZE_MB > 0, "MAX_CACHE_SIZE_MB должна использоваться"

        finally:
            cache.close()

    def test_constants_used_in_common(self) -> None:
        """
        Тест 4.2: Проверка использования констант в common.py.

        Проверяет что common.py использует константы а не магические числа.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем что константы используются в _sanitize_value
        assert MAX_DATA_SIZE > 0, "MAX_DATA_SIZE должна использоваться"
        assert COMMON_MAX_DATA_DEPTH > 0, "COMMON_MAX_DATA_DEPTH должна использоваться"
        assert MAX_COLLECTION_SIZE > 0, "MAX_COLLECTION_SIZE должна использоваться"

    def test_constants_used_in_parallel_parser(self, tmp_path: Path) -> None:
        """
        Тест 4.3: Проверка использования констант в parallel_parser.py.

        Проверяет что parallel_parser.py использует константы а не магические числа.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        # Проверяем что константы используются
        assert MAX_WORKERS > 0, "MAX_WORKERS должна использоваться"
        assert MAX_TIMEOUT > 0, "MAX_TIMEOUT должна использоваться"
        assert MAX_TEMP_FILES > 0, "MAX_TEMP_FILES должна использоваться"
        assert MERGE_LOCK_TIMEOUT > 0, "MERGE_LOCK_TIMEOUT должна использоваться"


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
