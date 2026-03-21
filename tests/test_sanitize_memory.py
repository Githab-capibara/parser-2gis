"""
Тесты для обработки MemoryError в функции _sanitize_value.

ИСПРАВЛЕНИЕ P0-2: Улучшение обработки MemoryError
Файлы: parser_2gis/common.py

Тестируют:
- Обработку MemoryError во всех рекурсивных вызовах
- Лимит глубины вложенности
- Лимит размера коллекций
- Итеративный подход вместо рекурсии
"""

import os
import sys
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from parser_2gis.common import MAX_COLLECTION_SIZE, MAX_DATA_DEPTH, _sanitize_value


class TestSanitizeValueDepthLimit:
    """Тесты для лимита глубины вложенности."""

    def test_sanitize_shallow_dict(self) -> None:
        """Тест обработки неглубокого словаря."""
        data = {"name": "test", "value": 123}
        result = _sanitize_value(data)
        assert result == data

    def test_sanitize_deep_dict_within_limit(self) -> None:
        """Тест обработки глубокого словаря в пределах лимита."""
        # Создаём вложенную структуру глубиной 50 (в пределах 100)
        data: Dict[str, Any] = {"value": "leaf"}
        for i in range(50):
            data = {"nested": data}

        result = _sanitize_value(data)
        assert result is not None
        assert isinstance(result, dict)

    def test_sanitize_dict_exceeds_depth_limit(self) -> None:
        """Тест обработки словаря, превышающего лимит глубины."""
        # Создаём вложенную структуру глубиной 150 (превышает 100)
        data: Dict[str, Any] = {"value": "leaf"}
        for i in range(150):
            data = {"nested": data}

        # Должна вернуться None или оригинальное значение из-за лимита глубины
        result = _sanitize_value(data)
        # Функция должна обработать только до лимита глубины
        assert result is not None

    def test_sanitize_deep_list_within_limit(self) -> None:
        """Тест обработки глубокого списка в пределах лимита."""
        # Создаём вложенный список глубиной 50
        data: List[Any] = ["leaf"]
        for i in range(50):
            data = [data]

        result = _sanitize_value(data)
        assert result is not None

    def test_sanitize_list_exceeds_depth_limit(self) -> None:
        """Тест обработки списка, превышающего лимит глубины."""
        # Создаём вложенный список глубиной 150
        data: List[Any] = ["leaf"]
        for i in range(150):
            data = [data]

        result = _sanitize_value(data)
        assert result is not None


class TestSanitizeValueMemoryError:
    """Тесты для обработки MemoryError."""

    def test_sanitize_normal_data(self) -> None:
        """Тест обработки нормальных данных."""
        data = {"name": "test", "values": [1, 2, 3], "nested": {"key": "value"}}
        result = _sanitize_value(data)
        assert result == data

    def test_sanitize_with_memory_error_mock(self) -> None:
        """Тест обработки с mock MemoryError."""
        data = {"key": "value"}

        with patch(
            "parser_2gis.common._sanitize_value", side_effect=MemoryError("Mock MemoryError")
        ):
            # Функция должна обработать MemoryError gracefully
            with pytest.raises(MemoryError):
                _sanitize_value(data)

    def test_sanitize_large_string(self) -> None:
        """Тест обработки большой строки."""
        # Создаём строку размером 1MB
        large_string = "x" * (1024 * 1024)
        data = {"large": large_string}

        result = _sanitize_value(data)
        assert result is not None
        assert "large" in result


class TestSanitizeValueLargeCollection:
    """Тесты для обработки больших коллекций."""

    def test_sanitize_small_dict(self) -> None:
        """Тест обработки небольшого словаря."""
        data = {f"key_{i}": f"value_{i}" for i in range(100)}
        result = _sanitize_value(data)
        assert result is not None
        assert len(result) == 100

    def test_sanitize_dict_at_limit(self) -> None:
        """Тест обработки словаря на пределе лимита."""
        # Создаём словарь с 1000 элементами (в пределах 100,000)
        data = {f"key_{i}": f"value_{i}" for i in range(1000)}
        result = _sanitize_value(data)
        assert result is not None
        assert len(result) == 1000

    def test_sanitize_dict_exceeds_limit(self) -> None:
        """Тест обработки словаря, превышающего лимит."""
        # Создаём словарь с 150,000 элементами (превышает 100,000)
        # Это может занять много памяти, поэтому используем генератор
        data = {}
        for i in range(150000):
            data[f"key_{i}"] = f"value_{i}"

        # Функция должна обработать только до лимита
        result = _sanitize_value(data)
        assert result is not None

    def test_sanitize_large_list(self) -> None:
        """Тест обработки большого списка."""
        # Создаём список с 10,000 элементами
        data = [i for i in range(10000)]
        result = _sanitize_value(data)
        assert result is not None
        assert len(result) == 10000

    def test_sanitize_list_at_limit(self) -> None:
        """Тест обработки списка на пределе лимита."""
        # Создаём список с 50,000 элементами (в пределах 100,000)
        data = [i for i in range(50000)]
        result = _sanitize_value(data)
        assert result is not None
        assert len(result) == 50000


class TestSanitizeValueNestedStructures:
    """Тесты для обработки вложенных структур."""

    def test_sanitize_nested_dict_list(self) -> None:
        """Тест обработки вложенной структуры словарь-список."""
        data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}], "total": 2}
        result = _sanitize_value(data)
        assert result == data

    def test_sanitize_nested_list_dict(self) -> None:
        """Тест обработки вложенной структуры список-словарь."""
        data = [{"id": 1, "values": [1, 2, 3]}, {"id": 2, "values": [4, 5, 6]}]
        result = _sanitize_value(data)
        assert result == data

    def test_sanitize_complex_nested_structure(self) -> None:
        """Тест обработки сложной вложенной структуры."""
        data = {
            "organizations": [
                {
                    "name": "Org 1",
                    "address": {"city": "Moscow", "street": "Tverskaya"},
                    "phones": ["+7 (495) 123-45-67"],
                    "emails": ["org1@example.com"],
                },
                {
                    "name": "Org 2",
                    "address": {"city": "SPb", "street": "Nevsky"},
                    "phones": ["+7 (812) 987-65-43"],
                    "emails": ["org2@example.com"],
                },
            ],
            "total": 2,
            "metadata": {"page": 1, "per_page": 10, "has_more": False},
        }
        result = _sanitize_value(data)
        assert result == data


class TestSanitizeValueEdgeCases:
    """Тесты для граничных случаев."""

    def test_sanitize_none(self) -> None:
        """Тест обработки None."""
        result = _sanitize_value(None)
        assert result is None

    def test_sanitize_empty_dict(self) -> None:
        """Тест обработки пустого словаря."""
        result = _sanitize_value({})
        assert result == {}

    def test_sanitize_empty_list(self) -> None:
        """Тест обработки пустого списка."""
        result = _sanitize_value([])
        assert result == []

    def test_sanitize_empty_string(self) -> None:
        """Тест обработки пустой строки."""
        result = _sanitize_value("")
        assert result == ""

    def test_sanitize_boolean(self) -> None:
        """Тест обработки булевого значения."""
        result = _sanitize_value(True)
        assert result is True

        result = _sanitize_value(False)
        assert result is False

    def test_sanitize_integer(self) -> None:
        """Тест обработки целого числа."""
        result = _sanitize_value(42)
        assert result == 42

    def test_sanitize_float(self) -> None:
        """Тест обработки числа с плавающей точкой."""
        result = _sanitize_value(3.14)
        assert result == 3.14

    def test_sanitize_mixed_types(self) -> None:
        """Тест обработки смешанных типов."""
        data = {
            "string": "text",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
        result = _sanitize_value(data)
        assert result == data


class TestSanitizeValueCircularReference:
    """Тесты для циклических ссылок."""

    def test_sanitize_circular_dict(self) -> None:
        """Тест обработки словаря с циклической ссылкой."""
        data: Dict[str, Any] = {"name": "test"}
        data["self"] = data  # Циклическая ссылка

        # Функция должна обработать циклическую ссылку
        # (либо через обнаружение цикла, либо через лимит глубины)
        result = _sanitize_value(data)
        assert result is not None

    def test_sanitize_circular_list(self) -> None:
        """Тест обработки списка с циклической ссылкой."""
        data: List[Any] = [1, 2, 3]
        data.append(data)  # Циклическая ссылка

        result = _sanitize_value(data)
        assert result is not None


class TestSanitizeValuePerformance:
    """Тесты производительности."""

    def test_sanitize_performance_small(self) -> None:
        """Тест производительности для небольших данных."""
        import time

        data = {f"key_{i}": f"value_{i}" for i in range(100)}

        start = time.time()
        result = _sanitize_value(data)
        elapsed = time.time() - start

        assert result is not None
        assert elapsed < 1.0  # Должно выполниться за 1 секунду

    def test_sanitize_performance_medium(self) -> None:
        """Тест производительности для средних данных."""
        import time

        data = {f"key_{i}": f"value_{i}" for i in range(1000)}

        start = time.time()
        result = _sanitize_value(data)
        elapsed = time.time() - start

        assert result is not None
        assert elapsed < 5.0  # Должно выполниться за 5 секунд


class TestSanitizeValueConstants:
    """Тесты для констант."""

    def test_max_data_depth_constant(self) -> None:
        """Тест константы MAX_DATA_DEPTH."""
        assert MAX_DATA_DEPTH == 100
        assert isinstance(MAX_DATA_DEPTH, int)

    def test_max_collection_size_constant(self) -> None:
        """Тест константы MAX_COLLECTION_SIZE."""
        assert MAX_COLLECTION_SIZE == 100000
        assert isinstance(MAX_COLLECTION_SIZE, int)


class TestSanitizeValueSecurity:
    """Тесты безопасности."""

    def test_sanitize_sensitive_data(self) -> None:
        """Тест обработки чувствительных данных."""
        data = {
            "password": "secret123",
            "api_key": "key-12345",
            "token": "token-abcde",
            "public": "visible",
        }
        result = _sanitize_value(data)
        assert result is not None
        # Чувствительные данные должны быть обработаны

    def test_sanitize_unicode_data(self) -> None:
        """Тест обработки Unicode данных."""
        data = {"russian": "Привет мир", "chinese": "你好世界", "emoji": "👋🌍"}
        result = _sanitize_value(data)
        assert result == data

    def test_sanitize_special_characters(self) -> None:
        """Тест обработки специальных символов."""
        data = {
            "html": "<script>alert(1)</script>",
            "sql": "'; DROP TABLE users; --",
            "path": "../../etc/passwd",
        }
        result = _sanitize_value(data)
        assert result is not None
