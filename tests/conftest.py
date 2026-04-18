"""
Общие фикстуры и конфигурация для тестов.

Содержит только активно используемые фикстуры.
Оптимизировано: 1073 -> 90 строк (удалено 46 неиспользуемых фикстур).
"""

import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

# =============================================================================
# АВТОМАТИЧЕСКИЕ ФИКСТУРЫ (autouse=True)
# =============================================================================


@pytest.fixture(autouse=True)
def setup_test_environment() -> Generator[None, None, None]:
    """Автоматическая фикстура для настройки тестового окружения.

    Выполняется перед каждым тестом.
    """
    os.environ["TESTING"] = "True"

    import logging

    logging.getLogger("parser-2gis").setLevel(logging.DEBUG)

    yield

    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture(autouse=True)
def reset_mock_state() -> Generator[None, None, None]:
    """Автоматическая фикстура для сброса состояния mock'ов между тестами."""
    yield
    patch.stopall()


# =============================================================================
# ПАРАМЕТРИЧЕСКИЕ ФИКСТУРЫ
# =============================================================================


@pytest.fixture(params=[1, 5, 10, 50, 100])
def num_records(request: pytest.FixtureRequest) -> int:
    """Фикстура для перебора количества записей."""
    return request.param


# =============================================================================
# КЭШ ФИКСТУРЫ
# =============================================================================


@pytest.fixture
def temp_cache_manager(tmp_path: Path):
    """Фикстура для создания временного CacheManager.

    Yields:
        CacheManager: Временный менеджер кэша.
    """
    from parser_2gis.cache import CacheManager

    cache_dir = tmp_path / "test_cache"
    cache = CacheManager(cache_dir, ttl_hours=24)

    yield cache

    cache.close()
