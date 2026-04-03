"""Тесты для JsonSerializer."""

import json

import pytest

from parser_2gis.cache.serializer import JsonSerializer


class TestJsonSerializerConstruction:
    """Тесты конструирования JsonSerializer."""

    def test_default_construction(self):
        """JsonSerializer создаётся без ошибок."""
        serializer = JsonSerializer()
        assert serializer is not None
        assert isinstance(serializer.use_orjson, bool)


class TestJsonSerializerSerialize:
    """Тесты сериализации JsonSerializer."""

    @pytest.mark.parametrize(
        "data,expected_contains",
        [
            pytest.param({"key": "value"}, '"key"', id="simple_dict"),
            pytest.param({"nested": {"a": 1}}, '"nested"', id="nested_dict"),
            pytest.param({"count": 42}, '"count"', id="dict_with_int"),
            pytest.param({"active": True}, '"active"', id="dict_with_bool"),
            pytest.param({"name": "тест"}, '"name"', id="dict_with_cyrillic"),
            pytest.param({}, "", id="empty_dict"),
        ],
    )
    def test_serialize_returns_json_string(self, data, expected_contains):
        """Сериализация возвращает корректную JSON строку."""
        serializer = JsonSerializer()
        result = serializer.serialize(data)
        assert isinstance(result, str)
        if expected_contains:
            assert expected_contains in result
        # Проверяем что результат валидный JSON
        parsed = json.loads(result)
        assert parsed == data

    def test_serialize_invalid_data_raises(self):
        """Сериализация некорректных данных выбрасывает TypeError."""
        serializer = JsonSerializer()
        # set не сериализуется в JSON по умолчанию
        with pytest.raises((TypeError, ValueError)):
            serializer.serialize(object())


class TestJsonSerializerDeserialize:
    """Тесты десериализации JsonSerializer."""

    @pytest.mark.parametrize(
        "data,expected",
        [
            pytest.param('{"key":"value"}', {"key": "value"}, id="simple_dict"),
            pytest.param('{"nested":{"a":1}}', {"nested": {"a": 1}}, id="nested_dict"),
            pytest.param('{"count":42}', {"count": 42}, id="dict_with_int"),
            pytest.param("{}", {}, id="empty_dict"),
        ],
    )
    def test_deserialize_returns_dict(self, data, expected):
        """Десериализация возвращает ожидаемый словарь."""
        serializer = JsonSerializer()
        result = serializer.deserialize(data)
        assert result == expected
        assert isinstance(result, dict)

    def test_deserialize_non_dict_raises_typeerror(self):
        """Десериализация не-dict данных выбрасывает TypeError."""
        serializer = JsonSerializer()
        with pytest.raises(TypeError):
            serializer.deserialize("[1, 2, 3]")

    def test_deserialize_invalid_json_raises_valueerror(self):
        """Десериализация невалидного JSON выбрасывает ValueError."""
        serializer = JsonSerializer()
        with pytest.raises((ValueError, json.JSONDecodeError)):
            serializer.deserialize("{invalid json}")
