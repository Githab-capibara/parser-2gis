"""
Тесты для модуля common.py.

Проверяют следующие функции:
- report_from_validation_error()
- unwrap_dot_dict()
- floor_to_hundreds()

Тесты для wait_until_finished() перенесены в test_utils_decorators.py
"""

from pydantic import BaseModel, ValidationError

from parser_2gis.utils.data_utils import unwrap_dot_dict
from parser_2gis.utils.math_utils import floor_to_hundreds
from parser_2gis.utils.validation_utils import report_from_validation_error


class TestFloorToHundreds:
    """Тесты для функции floor_to_hundreds."""

    def test_floor_to_hundreds_with_exact_hundred(self):
        """Проверка округления до сотен для точных значений."""
        assert floor_to_hundreds(100) == 100
        assert floor_to_hundreds(200) == 200
        assert floor_to_hundreds(1000) == 1000

    def test_floor_to_hundreds_with_rounding_down(self):
        """Проверка округления вниз до сотен."""
        assert floor_to_hundreds(150) == 100
        assert floor_to_hundreds(199) == 100
        assert floor_to_hundreds(250) == 200
        assert floor_to_hundreds(999) == 900

    def test_floor_to_hundreds_with_float(self):
        """Проверка работы с плавающими числами."""
        assert floor_to_hundreds(150.5) == 100
        assert floor_to_hundreds(199.99) == 100

    def test_floor_to_hundreds_with_small_numbers(self):
        """Проверка работы с числами меньше 100."""
        assert floor_to_hundreds(50) == 0
        assert floor_to_hundreds(99) == 0
        assert floor_to_hundreds(0) == 0

    def test_floor_to_hundreds_with_negative(self):
        """Проверка работы с отрицательными числами."""
        assert floor_to_hundreds(-50) == -100
        assert floor_to_hundreds(-150) == -200


class TestUnwrapDotDict:
    """Тесты для функции unwrap_dot_dict."""

    def test_unwrap_simple_path(self):
        """Проверка разворачивания простого пути."""
        input_dict = {"a.b": "value"}
        expected = {"a": {"b": "value"}}
        assert unwrap_dot_dict(input_dict) == expected

    def test_unwrap_nested_paths(self):
        """Проверка разворачивания вложенных путей."""
        input_dict = {"a.b.c": "value1", "a.b.d": "value2"}
        expected = {"a": {"b": {"c": "value1", "d": "value2"}}}
        assert unwrap_dot_dict(input_dict) == expected

    def test_unwrap_multiple_top_level(self):
        """Проверка разворачивания нескольких верхнеуровневых ключей."""
        input_dict = {"a.b": "value1", "c.d": "value2"}
        expected = {"a": {"b": "value1"}, "c": {"d": "value2"}}
        assert unwrap_dot_dict(input_dict) == expected

    def test_unwrap_empty_dict(self):
        """Проверка разворачивания пустого словаря."""
        assert unwrap_dot_dict({}) == {}

    def test_unwrap_preserves_values(self):
        """Проверка сохранения значений разных типов."""
        input_dict = {
            "a.int": 42,
            "a.float": 3.14,
            "a.string": "test",
            "a.bool": True,
            "a.list": [1, 2, 3],
            "a.dict": {"nested": "value"},
        }
        result = unwrap_dot_dict(input_dict)
        assert result["a"]["int"] == 42
        assert result["a"]["float"] == 3.14
        assert result["a"]["string"] == "test"
        assert result["a"]["bool"] is True
        assert result["a"]["list"] == [1, 2, 3]
        assert result["a"]["dict"] == {"nested": "value"}


class TestReportFromValidationError:
    """Тесты для функции report_from_validation_error."""

    class SimpleModel(BaseModel):
        """Простая модель для тестирования."""

        name: str
        age: int

    def test_report_with_invalid_value(self):
        """Проверка отчёта с невалидным значением."""
        try:
            self.SimpleModel(name="test", age="invalid")
        except ValidationError as e:
            report = report_from_validation_error(e, {"name": "test", "age": "invalid"})
            assert "age" in report
            assert report["age"]["invalid_value"] == "invalid"
            assert "error_message" in report["age"]

    def test_report_without_dict(self):
        """Проверка отчёта без словаря значений."""
        try:
            self.SimpleModel(name="test", age="invalid")
        except ValidationError as e:
            report = report_from_validation_error(e)
            assert "age" in report
            assert "error_message" in report["age"]

    def test_report_with_multiple_errors(self):
        """Проверка отчёта с несколькими ошибками."""
        try:
            self.SimpleModel(name=123, age="invalid")
        except ValidationError as e:
            report = report_from_validation_error(e)
            assert "name" in report or "age" in report

    def test_report_with_missing_value(self):
        """Проверка отчёта с отсутствующим значением."""
        try:
            self.SimpleModel(name="test", age="invalid")
        except ValidationError as e:
            report = report_from_validation_error(e, {"name": "test"})
            assert "age" in report
            assert report["age"]["invalid_value"] == "<No value>"
