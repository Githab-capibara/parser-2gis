"""Тесты для проверки валидации initialState в firm.py."""

from parser_2gis.parser.parsers.firm import (
    MAX_INITIAL_STATE_DEPTH,
    MAX_INITIAL_STATE_SIZE,
    MAX_ITEMS_IN_COLLECTION,
    _safe_extract_initial_state,
    _validate_initial_state,
)


class TestValidateInitialState:
    """Тесты для функции _validate_initial_state."""

    def test_none_returns_true(self) -> None:
        """None должен проходить валидацию."""
        valid, count = _validate_initial_state(None)
        assert valid
        assert count == 0

    def test_bool_returns_true(self) -> None:
        """Bool должен проходить валидацию."""
        valid, _count = _validate_initial_state(True)
        assert valid
        valid, _count = _validate_initial_state(False)
        assert valid

    def test_int_float_returns_true(self) -> None:
        """Int и float должны проходить валидацию."""
        valid, _count = _validate_initial_state(42)
        assert valid
        valid, _count = _validate_initial_state(3.14)
        assert valid

    def test_string_returns_true(self) -> None:
        """Строка должна проходить валидацию."""
        valid, _count = _validate_initial_state("normal string")
        assert valid

    def test_nan_rejected(self) -> None:
        """NaN должен быть отклонён."""
        valid, _ = _validate_initial_state(float("nan"))
        assert not valid

    def test_infinity_rejected(self) -> None:
        """Infinity должен быть отклонён."""
        valid, _ = _validate_initial_state(float("inf"))
        assert not valid

    def test_script_tag_rejected(self) -> None:
        """Script тег должен быть отклонён."""
        valid, _ = _validate_initial_state("<script>alert('xss')</script>")
        assert not valid

    def test_javascript_protocol_rejected(self) -> None:
        """JavaScript protocol должен быть отклонён."""
        valid, _ = _validate_initial_state("javascript:alert('xss')")
        assert not valid

    def test_onerror_handler_rejected(self) -> None:
        """Onerror handler должен быть отклонён."""
        valid, _ = _validate_initial_state('<img src=x onerror="alert(1)">')
        assert not valid

    def test_eval_rejected(self) -> None:
        """eval() должен быть отклонён."""
        valid, _ = _validate_initial_state("eval('malicious code')")
        assert not valid

    def test_deep_nesting_rejected(self) -> None:
        """Глубокая вложенность должна быть отклонена."""

        def create_deep_dict(depth):
            if depth == 0:
                return {"key": "value"}
            return {"nested": create_deep_dict(depth - 1)}

        malicious = create_deep_dict(MAX_INITIAL_STATE_DEPTH + 1)
        valid, _ = _validate_initial_state(malicious)
        assert not valid

    def test_large_dict_rejected(self) -> None:
        """Слишком большой словарь должен быть отклонён."""
        large_dict = {f"key_{i}": f"value_{i}" for i in range(MAX_ITEMS_IN_COLLECTION + 1)}
        valid, _ = _validate_initial_state(large_dict)
        assert not valid

    def test_large_list_rejected(self) -> None:
        """Слишком большой список должен быть отклонён."""
        large_list = [f"item_{i}" for i in range(MAX_ITEMS_IN_COLLECTION + 1)]
        valid, _ = _validate_initial_state(large_list)
        assert not valid

    def test_large_string_rejected(self) -> None:
        """Слишком длинная строка должна быть отклонена."""
        long_string = "x" * (MAX_INITIAL_STATE_SIZE + 1)
        valid, _ = _validate_initial_state(long_string)
        assert not valid

    def test_nested_valid_data(self) -> None:
        """Валидные вложенные данные должны проходить."""
        valid_data = {"data": {"entity": {"profile": {"name": "Test Company", "address": "123 Main St"}}}}
        valid, _ = _validate_initial_state(valid_data)
        assert valid


class TestSafeExtractInitialState:
    """Тесты для функции _safe_extract_initial_state."""

    def test_non_dict_returns_none(self) -> None:
        """Не словарь должен возвращать None."""
        result = _safe_extract_initial_state("not a dict", ["data"])
        assert result is None

    def test_non_dict_list_returns_none(self) -> None:
        """Список вместо словаря должен возвращать None."""
        result = _safe_extract_initial_state([1, 2, 3], ["data"])
        assert result is None

    def test_missing_required_keys_returns_none(self) -> None:
        """Отсутствующие ключи должны возвращать None."""
        data = {"data": {"entity": {}}}
        result = _safe_extract_initial_state(data, ["data", "entity", "profile"])
        assert result is None

    def test_valid_extraction(self) -> None:
        """Валидные данные должны извлекаться."""
        data = {"data": {"entity": {"profile": {"name": "Test Company", "address": "123 Main St"}}}}
        result = _safe_extract_initial_state(data, ["data", "entity", "profile"])
        assert result is not None
        assert result["name"] == "Test Company"
        assert result["address"] == "123 Main St"

    def test_oversized_data_returns_none(self) -> None:
        """Слишком большие данные должны возвращать None."""
        large_data = {"key": "x" * (MAX_INITIAL_STATE_SIZE + 1)}
        result = _safe_extract_initial_state(large_data, ["key"])
        assert result is None

    def test_malicious_script_in_data_returns_none(self) -> None:
        """Вредоносный скрипт в данных должен возвращать None."""
        malicious_data = {"data": {"entity": {"profile": {"name": "<script>alert('xss')</script>"}}}}
        result = _safe_extract_initial_state(malicious_data, ["data", "entity", "profile"])
        assert result is None
