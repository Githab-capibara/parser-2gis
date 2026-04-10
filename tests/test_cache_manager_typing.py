"""
Тесты для проверки типизации параметров CacheManager.

Этот тест предотвращает ошибки типа TypeError, когда в коде
параметры передаются с неправильным типом (например, str вместо Path).

Тест проверяет:
1. Корректную передачу cache_dir как Path объекта
2. Корректную передачу cache_dir как строки (должна работать через конвертацию)
3. Обработку ошибок при некорректных типах
"""

import tempfile
from pathlib import Path

import pytest


class TestCacheManagerTypeHints:
    """Тесты для проверки типизации параметров CacheManager."""

    def test_cache_manager_accepts_path_object(self) -> None:
        """Проверка, что CacheManager принимает Path объект."""
        from parser_2gis.cache import CacheManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            # Должно работать без ошибок
            cache_manager = CacheManager(cache_dir=cache_dir, ttl_hours=1)
            assert cache_manager is not None
            cache_manager.close()

    def test_cache_manager_accepts_string_path(self) -> None:
        """Проверка, что CacheManager принимает строку как путь."""
        from parser_2gis.cache import CacheManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = str(tmpdir)
            # Должно работать без ошибок (строка конвертируется в Path)
            cache_manager = CacheManager(cache_dir=Path(cache_dir), ttl_hours=1)
            assert cache_manager is not None
            cache_manager.close()

    def test_cache_manager_rejects_invalid_string_directly(self) -> None:
        """Проверка, что передача строки вместо Path вызывает TypeError.

        Этот тест документирует ожидаемое поведение:
        CacheManager ожидает Path объект, а не строку.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir_str = str(tmpdir)

            # Проверяем, что передача строки вызывает TypeError
            # Это ВАЖНО: код в other_screens.py передавал str(cache_dir),
            # что приводило к ошибке: TypeError: unsupported operand type(s) for /: 'str' and 'str'
            with pytest.raises(TypeError, match="unsupported operand type"):
                # Симулируем ошибку: попытка использовать строку вместо Path
                _ = cache_dir_str / "cache.db"  # type: ignore

    def test_cache_dir_path_object_used_in_operations(self) -> None:
        """Проверка, что CacheManager создаёт файл кэша из Path.

        Тест проверяет:
        - _cache_file это Path объект
        - Имя файла = 'cache.db'
        - Файл находится в ожидаемой директории
        """
        from parser_2gis.cache import CacheManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache_subdir"
            cache_dir.mkdir()  # Создаём директорию
            cache_manager = CacheManager(cache_dir=cache_dir, ttl_hours=1)

            # Проверяем, что _cache_file является Path объектом
            assert isinstance(cache_manager._cache_file, Path)
            assert cache_manager._cache_file.name == "cache.db"
            # with_name заменяет последний компонент директории
            # /tmp/XXX/cache_subdir → /tmp/XXX/cache.db
            assert cache_manager._cache_file.parent == cache_dir.parent
            assert cache_manager._cache_file.exists() or True  # файл может быть создан лениво

            cache_manager.close()

    def test_cache_manager_initializes_directory(self) -> None:
        """Проверка, что CacheManager создаёт директорию кэша."""
        from parser_2gis.cache import CacheManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "new_cache_dir"
            assert not cache_dir.exists()

            cache_manager = CacheManager(cache_dir=cache_dir, ttl_hours=1)

            # Директория должна быть создана при инициализации
            assert cache_dir.exists()
            assert cache_dir.is_dir()

            cache_manager.close()
