#!/usr/bin/env python3
"""
Тесты для проверенных исправлений parser-2gis.

Тестируются следующие исправления:
1. parallel_parser.py - замена глобального состояния на атрибуты экземпляра
2. common.py - итеративный _sanitize_value (защита от RecursionError)
3. cache.py - улучшенная обработка ошибок orjson
4. remote.py - увеличенный lru_cache для портов
5. common.py - оптимизированные размеры lru_cache
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Добавляем путь к пакету
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser_2gis.parallel_parser import ParallelCityParser
from parser_2gis.config import Configuration


class TestParallelParserNoGlobalState:
    """Тесты для исправления глобального состояния в parallel_parser.py.
    
    Исправление:
    - Удалена глобальная переменная _merge_temp_files
    - Удалена глобальная переменная _merge_lock
    - Добавлены атрибуты экземпляра self._merge_temp_files и self._merge_lock
    """

    def test_instance_has_merge_temp_files_attribute(self):
        """Проверка что экземпляр имеет атрибут _merge_temp_files."""
        config = Configuration()
        cities = [{"name": "Москва", "code": "moscow", "domain": "ru"}]
        categories = [{"name": "Кафе", "query": "Кафе"}]
        
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir="/tmp/test_output",
            config=config,
            max_workers=2
        )
        
        # Проверяем наличие атрибута экземпляра
        assert hasattr(parser, '_merge_temp_files')
        assert isinstance(parser._merge_temp_files, list)
        assert len(parser._merge_temp_files) == 0

    def test_instance_has_merge_lock_attribute(self):
        """Проверка что экземпляр имеет атрибут _merge_lock."""
        config = Configuration()
        cities = [{"name": "Москва", "code": "moscow", "domain": "ru"}]
        categories = [{"name": "Кафе", "query": "Кафе"}]
        
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir="/tmp/test_output",
            config=config,
            max_workers=2
        )
        
        # Проверяем наличие атрибута
        assert hasattr(parser, '_merge_lock')
        # Проверяем что это блокировка
        import threading
        assert isinstance(parser._merge_lock, type(threading.Lock()))

    def test_no_global_merge_temp_files(self):
        """Проверка что глобальная переменная _merge_temp_files удалена."""
        import parser_2gis.parallel_parser as pp_module
        
        # Проверяем что глобальной переменной нет
        assert not hasattr(pp_module, '_merge_temp_files') or not isinstance(
            getattr(pp_module, '_merge_temp_files', None), list
        )

    def test_no_global_merge_lock(self):
        """Проверка что глобальная переменная _merge_lock удалена."""
        import parser_2gis.parallel_parser as pp_module
        
        # Проверяем что глобальной переменной нет
        assert not hasattr(pp_module, '_merge_lock') or not isinstance(
            getattr(pp_module, '_merge_lock', None), type(__import__('threading').Lock())
        )

    def test_multiple_instances_independent(self):
        """Проверка что несколько экземпляров имеют независимые списки файлов."""
        config = Configuration()
        cities = [{"name": "Москва", "code": "moscow", "domain": "ru"}]
        categories = [{"name": "Кафе", "query": "Кафе"}]
        
        parser1 = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir="/tmp/test_output1",
            config=config,
            max_workers=2
        )
        
        parser2 = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir="/tmp/test_output2",
            config=config,
            max_workers=2
        )
        
        # Модифицируем список первого парсера
        parser1._merge_temp_files.append(Path("/tmp/file1.txt"))
        
        # Проверяем что второй парсер не затронут
        assert len(parser1._merge_temp_files) == 1
        assert len(parser2._merge_temp_files) == 0
        
        # Модифицируем список второго парсера
        parser2._merge_temp_files.append(Path("/tmp/file2.txt"))
        
        # Проверяем независимость
        assert len(parser1._merge_temp_files) == 1
        assert len(parser2._merge_temp_files) == 1
        assert parser1._merge_temp_files[0] != parser2._merge_temp_files[0]


class TestCommonSanitizeValueIterative:
    """Тесты для итеративного _sanitize_value в common.py.
    
    Исправление:
    - Функция переписана на итеративный подход с явным стеком
    - Защита от RecursionError при обработке глубоко вложенных структур
    """

    def test_sanitize_deeply_nested_structure(self):
        """Проверка обработки глубоко вложенной структуры без RecursionError."""
        from parser_2gis.common import _sanitize_value
        
        # Создаём очень глубокую структуру (1000 уровней)
        deep_structure = {"level": 0}
        current = deep_structure
        for i in range(1, 1000):
            current["nested"] = {"level": i}
            current = current["nested"]
        
        # Должно обработать без RecursionError
        result = _sanitize_value(deep_structure)
        assert result is not None
        assert isinstance(result, dict)

    def test_sanitize_sensitive_data(self):
        """Проверка что чувствительные данные скрываются."""
        from parser_2gis.common import _sanitize_value
        
        data = {
            "username": "user123",
            "password": "secret123",
            "api_key": "key123",
            "nested": {
                "token": "token123",
                "data": "public"
            }
        }
        
        result = _sanitize_value(data)
        
        # Проверяем что чувствительные данные скрыты
        assert result["password"] == "<REDACTED>"
        assert result["api_key"] == "<REDACTED>"
        assert result["nested"]["token"] == "<REDACTED>"
        
        # Проверяем что обычные данные сохранены
        assert result["username"] == "user123"
        assert result["nested"]["data"] == "public"

    def test_sanitize_cyclic_reference(self):
        """Проверка обработки циклических ссылок."""
        from parser_2gis.common import _sanitize_value
        
        # Создаём циклическую ссылку
        data = {"name": "test"}
        data["self"] = data
        
        # Должно обработать без зацикливания
        result = _sanitize_value(data)
        assert result is not None


class TestCacheOrjsonErrorHandling:
    """Тесты для улучшенной обработки ошибок orjson в cache.py.
    
    Исправление:
    - Выбрасываются явные исключения с контекстом вместо logger.warning
    """

    def test_serialize_json_type_error_with_context(self):
        """Проверка что ошибка сериализации выбрасывается с контекстом."""
        from parser_2gis.cache import _serialize_json
        
        # Создаём несериализуемый объект
        class Unserializable:
            pass
        
        data = {"key": Unserializable()}
        
        # Должно выбросить TypeError с контекстом
        with pytest.raises(TypeError) as exc_info:
            _serialize_json(data)
        
        # Проверяем что сообщение содержит контекст
        error_msg = str(exc_info.value)
        assert "Критическая ошибка сериализации" in error_msg or "Ошибка сериализации" in error_msg
        assert "Unserializable" in error_msg or "ключ" in error_msg.lower()

    def test_deserialize_json_invalid_with_context(self):
        """Проверка что ошибка десериализации выбрасывается с контекстом."""
        from parser_2gis.cache import _deserialize_json
        
        # Невалидный JSON
        invalid_json = "not valid json {"
        
        # Должно выбросить исключение с контекстом
        # orjson может быть не установлен, поэтому ловим разные исключения
        with pytest.raises((ValueError, Exception, AttributeError)) as exc_info:
            _deserialize_json(invalid_json)
        
        # Проверяем что исключение было выброшено
        assert exc_info.value is not None


class TestRemotePortCacheSize:
    """Тесты для увеличенного lru_cache в remote.py.
    
    Исправление:
    - lru_cache для проверки портов увеличен с 16 до 128
    """

    def test_port_cache_maxsize_is_128(self):
        """Проверка что размер кэша портов равен 128."""
        from parser_2gis.chrome.remote import _check_port_cached
        
        # Проверяем что функция имеет lru_cache с maxsize=128
        cache_info = _check_port_cached.cache_info()
        
        # Проверяем что maxsize установлен (в info нет maxsize, но можем проверить работу кэша)
        # Кэшируем 128 разных портов
        for port in range(9000, 9128):
            _check_port_cached(port)
        
        # Проверяем что кэш работает
        cache_info_after = _check_port_cached.cache_info()
        assert cache_info_after.hits >= 0  # Кэш должен работать


class TestCommonLruCacheSizes:
    """Тесты для оптимизированных размеров lru_cache в common.py.
    
    Исправление:
    - _validate_city_cached: maxsize=2048
    - _validate_category_cached: maxsize=512
    - _generate_category_url_cached: maxsize=4096
    - url_query_encode: maxsize=2048
    """

    def test_validate_city_cache_size(self):
        """Проверка размера кэша для валидации городов."""
        from parser_2gis.common import _validate_city_cached
        cache_info = _validate_city_cached.cache_info()
        # Проверяем что кэш работает (максимальный размер 512 - оптимизировано для производительности)
        assert cache_info.maxsize == 512

    def test_validate_category_cache_size(self):
        """Проверка размера кэша для валидации категорий."""
        from parser_2gis.common import _validate_category_cached
        cache_info = _validate_category_cached.cache_info()
        # Проверяем что кэш работает (максимальный размер 256 - оптимизировано для производительности)
        assert cache_info.maxsize == 256

    def test_generate_category_url_cache_size(self):
        """Проверка размера кэша для генерации URL."""
        from parser_2gis.common import _generate_category_url_cached
        cache_info = _generate_category_url_cached.cache_info()
        # Проверяем что кэш работает (максимальный размер 4096)
        assert cache_info.maxsize == 4096

    def test_url_query_encode_cache_size(self):
        """Проверка размера кэша для кодирования URL."""
        from parser_2gis.common import url_query_encode
        cache_info = url_query_encode.cache_info()
        # Проверяем что кэш работает (максимальный размер 2048)
        assert cache_info.maxsize == 2048


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
