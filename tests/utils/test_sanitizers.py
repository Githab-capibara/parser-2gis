"""
Тесты для модуля utils/sanitizers.

Проверяет:
- Обработку циклических ссылок в _sanitize_value()
- Sanitizer не зацикливается при обнаружении циклических ссылок
"""

from parser_2gis.utils.sanitizers import _sanitize_value


class TestSanitizerCyclicReferences:
    """Тесты циклических ссылок в _sanitize_value()."""

    def test_cyclic_dict_reference(self) -> None:
        """Тест 1: Циклическая ссылка в dict — sanitizer не зацикливается."""
        data: dict = {"name": "test", "nested": {}}
        # Создаём циклическую ссылку
        data["nested"]["parent"] = data  # type: ignore[index]

        # Метод должен завершиться без зацикливания
        result = _sanitize_value(data)
        assert isinstance(result, dict)
        assert result["name"] == "test"

    def test_cyclic_list_reference(self) -> None:
        """Тест 2: Циклическая ссылка в list — sanitizer не зацикливается."""
        lst: list = [1, 2, 3]
        lst.append(lst)  # Циклическая ссылка

        result = _sanitize_value(lst)
        assert isinstance(result, list)
        assert result[0] == 1
        assert result[1] == 2
        assert result[2] == 3

    def test_deep_cyclic_reference(self) -> None:
        """Тест 3: Глубокая циклическая ссылка — несколько уровней вложенности."""
        level1: dict = {"level": 1}
        level2: dict = {"level": 2}
        level3: dict = {"level": 3}

        level1["child"] = level2
        level2["child"] = level3
        level3["ancestor"] = level1  # Цикл обратно на level1

        result = _sanitize_value(level1)
        assert isinstance(result, dict)
        assert result["level"] == 1

    def test_self_referencing_dict(self) -> None:
        """Тест 4: Dict ссылается сам на себя."""
        data: dict = {"title": "value"}
        data["self"] = data  # type: ignore[assignment]

        result = _sanitize_value(data)
        assert isinstance(result, dict)
        assert result["title"] == "value"

    def test_mutual_cyclic_reference(self) -> None:
        """Тест 5: Взаимная циклическая ссылка между двумя dict."""
        a: dict = {"name": "a"}
        b: dict = {"name": "b"}
        a["ref"] = b
        b["ref"] = a  # Цикл: a -> b -> a

        result = _sanitize_value(a)
        assert isinstance(result, dict)
        assert result["name"] == "a"

    def test_cyclic_reference_in_list_of_dicts(self) -> None:
        """Тест 6: Циклическая ссылка в списке dict."""
        parent: dict = {"type": "parent"}
        children: list = [{"type": "child1"}, {"type": "child2"}]
        for child in children:
            child["parent"] = parent  # type: ignore[assignment]
        parent["children"] = children

        result = _sanitize_value(parent)
        assert isinstance(result, dict)
        assert result["type"] == "parent"
        assert len(result["children"]) == 2  # type: ignore[index]

    def test_no_cyclic_reference_normal(self) -> None:
        """Тест 7: Нормальная структура без циклов работает корректно."""
        data = {"name": "test", "nested": {"title": "value", "items": [1, 2, 3]}}

        result = _sanitize_value(data)
        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert isinstance(result["nested"], dict)
        assert result["nested"]["title"] == "value"
        assert result["nested"]["items"] == [1, 2, 3]

    def test_cyclic_list_in_dict(self) -> None:
        """Тест 8: Циклическая ссылка — список содержит свой родительский dict."""
        data: dict = {"items": []}
        data["items"].append(data)  # type: ignore[arg-type]

        result = _sanitize_value(data)
        assert isinstance(result, dict)
        assert "items" in result

    def test_sensitive_key_with_cyclic_reference(self) -> None:
        """Тест 9: Циклическая ссылка с чувствительным ключом."""
        data: dict = {"password": "secret123", "data": {}}
        data["data"]["back"] = data  # type: ignore[index]

        result = _sanitize_value(data)
        assert isinstance(result, dict)
        assert result["password"] == "<REDACTED>"

    def test_triple_cyclic_chain(self) -> None:
        """Тест 10: Цепочка из трёх элементов с циклом."""
        a: dict = {"id": "a"}
        b: dict = {"id": "b"}
        c: dict = {"id": "c"}

        a["next"] = b
        b["next"] = c
        c["next"] = a  # Замыкаем цикл

        result = _sanitize_value(a)
        assert isinstance(result, dict)
        assert result["id"] == "a"
