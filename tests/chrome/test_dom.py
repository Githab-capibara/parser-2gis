"""Тесты для DOM parser."""

import pytest

from parser_2gis.chrome.dom import DOMNode


@pytest.fixture
def sample_dom_node():
    """Создаёт тестовый DOMNode."""
    return DOMNode(
        nodeId=1,
        backendNodeId=100,
        nodeType=1,
        nodeName="DIV",
        localName="div",
        nodeValue="",
        attributes=["class", "container", "id", "main"],
        children=[],
    )


@pytest.fixture
def nested_dom_node():
    """Создаёт вложенный DOMNode с детьми."""
    child = DOMNode(
        nodeId=2,
        backendNodeId=101,
        nodeType=3,
        nodeName="#text",
        localName="#text",
        nodeValue="Hello World",
        attributes=[],
        children=[],
    )
    return DOMNode(
        nodeId=1,
        backendNodeId=100,
        nodeType=1,
        nodeName="DIV",
        localName="div",
        nodeValue="",
        attributes=["class", "container"],
        children=[child],
    )


class TestDOMNodeConstruction:
    """Тесты конструирования DOMNode."""

    def test_basic_construction(self, sample_dom_node):
        """DOMNode создаётся с базовыми параметрами."""
        assert sample_dom_node.id == 1
        assert sample_dom_node.backend_id == 100
        assert sample_dom_node.type == 1
        assert sample_dom_node.name == "DIV"
        assert sample_dom_node.local_name == "div"
        assert sample_dom_node.value == ""

    def test_attributes_parsed_from_list(self, sample_dom_node):
        """Атрибуты парсятся из списка в словарь."""
        assert sample_dom_node.attributes == {"class": "container", "id": "main"}

    def test_attributes_odd_list_raises(self):
        """Нечётный список атрибутов вызывает ValueError."""
        with pytest.raises(ValueError, match="чётное количество"):
            DOMNode(
                nodeId=1,
                backendNodeId=100,
                nodeType=1,
                nodeName="DIV",
                localName="div",
                nodeValue="",
                attributes=["class", "container", "id"],  # Нечётное количество
            )


class TestDOMNodeText:
    """Тесты свойства text."""

    def test_text_returns_node_value(self):
        """text возвращает значение текстового узла."""
        node = DOMNode(
            nodeId=1,
            backendNodeId=100,
            nodeType=3,
            nodeName="#text",
            localName="#text",
            nodeValue="Hello",
            attributes=[],
            children=[],
        )
        assert node.text == "Hello"

    def test_text_includes_children(self, nested_dom_node):
        """text включает текст дочерних узлов."""
        assert "Hello World" in nested_dom_node.text


class TestDOMNodeSearch:
    """Тесты метода search."""

    def test_search_finds_matching_nodes(self, nested_dom_node):
        """search находит узлы по предикату."""
        results = nested_dom_node.search(lambda n: n.type == 3)
        assert len(results) == 1
        assert results[0].nodeValue == "Hello World"

    def test_search_no_matches(self, sample_dom_node):
        """search возвращает пустой список при отсутствии совпадений."""
        results = sample_dom_node.search(lambda n: n.type == 999)
        assert len(results) == 0

    def test_search_finds_self(self, sample_dom_node):
        """search может найти сам узел."""
        results = sample_dom_node.search(lambda n: n.id == 1)
        assert len(results) == 1
        assert results[0].id == 1

    @pytest.mark.parametrize(
        "predicate,expected_count",
        [
            pytest.param(lambda n: n.type == 1, 1, id="element_nodes"),
            pytest.param(lambda n: n.type == 3, 1, id="text_nodes"),
            pytest.param(lambda n: n.name == "DIV", 1, id="by_name"),
        ],
    )
    def test_search_parametrized(self, nested_dom_node, predicate, expected_count):
        """Параметризованный тест search."""
        results = nested_dom_node.search(predicate)
        assert len(results) == expected_count
