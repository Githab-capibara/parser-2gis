"""Тесты для абстрактного базового класса BaseParser.

Проверяет что BaseParser правильно определён как ABC и требует реализации
абстрактных методов parse() и get_stats().
"""

from typing import Any, Dict

import pytest

from parser_2gis.parser.parsers.base import BaseParser


# Моковый FileWriter для тестов
class MockFileWriter:
    """Mock FileWriter для тестов."""

    def __init__(self):
        self.data = []
        self.closed = False

    def write(self, data: Dict[str, Any]) -> None:
        """Записывает данные."""
        self.data.append(data)

    def close(self) -> None:
        """Закрывает писатель."""
        self.closed = True


class TestBaseParserABC:
    """Тесты абстрактного базового класса BaseParser."""

    def test_base_parser_is_abstract(self):
        """Тест 1: BaseParser является абстрактным классом."""
        # Проверяем что BaseParser имеет абстрактные методы
        assert hasattr(BaseParser, "__abstractmethods__")
        assert "parse" in BaseParser.__abstractmethods__
        assert "get_stats" in BaseParser.__abstractmethods__

    def test_cannot_instantiate_base_parser(self):
        """Тест 2: Нельзя создать экземпляр BaseParser напрямую."""
        # Попытка создать экземпляр должна вызвать TypeError
        with pytest.raises(TypeError):
            BaseParser()

    def test_concrete_parser_can_be_instantiated(self):
        """Тест 3: Можно создать экземпляр конкретного парсера."""

        class ConcreteParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = ConcreteParser()
        assert isinstance(parser, BaseParser)

    def test_parse_method_is_abstract(self):
        """Тест 4: Метод parse() является абстрактным."""
        # Проверяем что parse в абстрактных методах
        assert "parse" in BaseParser.__abstractmethods__

    def test_get_stats_method_is_abstract(self):
        """Тест 5: Метод get_stats() является абстрактным."""
        # Проверяем что get_stats в абстрактных методах
        assert "get_stats" in BaseParser.__abstractmethods__

    def test_concrete_parser_implements_parse(self):
        """Тест 6: Конкретный парсер реализует parse()."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                writer.write({"test": "data"})

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        mock_writer = MockFileWriter()
        parser.parse(mock_writer)

        assert len(mock_writer.data) == 1
        assert mock_writer.data[0] == {"test": "data"}

    def test_concrete_parser_implements_get_stats(self):
        """Тест 7: Конкретный парсер реализует get_stats()."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return {"custom": "stats"}

        parser = TestParser()
        stats = parser.get_stats()

        assert stats == {"custom": "stats"}

    def test_base_parser_has_stats_attribute(self):
        """Тест 8: BaseParser имеет атрибут _stats."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        assert hasattr(parser, "_stats")
        assert isinstance(parser._stats, dict)

    def test_base_parser_default_stats(self):
        """Тест 9: BaseParser имеет значения статистики по умолчанию."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        stats = parser.get_stats()

        assert "parsed" in stats
        assert "errors" in stats
        assert "skipped" in stats
        assert stats["parsed"] == 0
        assert stats["errors"] == 0
        assert stats["skipped"] == 0

    def test_parser_inherits_from_base_parser(self):
        """Тест 10: Парсер наследуется от BaseParser."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        assert issubclass(TestParser, BaseParser)
        assert isinstance(parser, BaseParser)

    def test_parse_method_signature(self):
        """Тест 11: Сигнатура метода parse() правильная."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        # Проверяем что метод принимает writer
        mock_writer = MockFileWriter()
        parser.parse(mock_writer)

    def test_get_stats_method_signature(self):
        """Тест 12: Сигнатура метода get_stats() правильная."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        stats = parser.get_stats()

        assert isinstance(stats, dict)

    def test_multiple_parsers_isolation(self):
        """Тест 13: Несколько парсеров изолированы друг от друга."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                self._stats["parsed"] += 1

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser1 = TestParser()
        parser2 = TestParser()

        parser1.parse(MockFileWriter())
        parser1.parse(MockFileWriter())

        assert parser1.get_stats()["parsed"] == 2
        assert parser2.get_stats()["parsed"] == 0

    def test_parser_stats_modification(self):
        """Тест 14: Можно модифицировать статистику парсера."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                self._stats["parsed"] += 1
                self._stats["custom"] = "value"

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        parser.parse(MockFileWriter())

        assert parser._stats["parsed"] == 1
        assert parser._stats["custom"] == "value"

    def test_parser_repr(self):
        """Тест 15: Метод __repr__() работает корректно."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        repr_str = repr(parser)

        assert "TestParser" in repr_str
        assert "parsed=0" in repr_str

    def test_parser_with_custom_init(self):
        """Тест 16: Парсер с кастомным __init__."""

        class TestParser(BaseParser):
            def __init__(self, custom_param: str = "default"):
                super().__init__()
                self.custom_param = custom_param

            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser(custom_param="test")
        assert parser.custom_param == "test"
        assert isinstance(parser, BaseParser)

    def test_parser_exception_handling_in_parse(self):
        """Тест 17: Обработка исключений в parse()."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                self._stats["errors"] += 1
                raise ValueError("Test error")

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        mock_writer = MockFileWriter()

        with pytest.raises(ValueError):
            parser.parse(mock_writer)

        assert parser.get_stats()["errors"] == 1

    def test_parser_get_stats_returns_dict(self):
        """Тест 18: get_stats() возвращает словарь."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return {"key": "value", "number": 42}

        parser = TestParser()
        stats = parser.get_stats()

        assert isinstance(stats, dict)
        assert stats["key"] == "value"
        assert stats["number"] == 42

    def test_parser_writer_interaction(self):
        """Тест 19: Взаимодействие парсера с writer."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                for i in range(5):
                    writer.write({"index": i})
                    self._stats["parsed"] += 1

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        mock_writer = MockFileWriter()
        parser.parse(mock_writer)

        assert len(mock_writer.data) == 5
        assert parser.get_stats()["parsed"] == 5

    def test_parser_multiple_parse_calls(self):
        """Тест 20: Несколько вызовов parse()."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                self._stats["parsed"] += 1

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        parser.parse(MockFileWriter())
        parser.parse(MockFileWriter())
        parser.parse(MockFileWriter())

        assert parser.get_stats()["parsed"] == 3

    def test_parser_subclass_override_stats(self):
        """Тест 21: Переопределение _stats в подклассе."""

        class TestParser(BaseParser):
            def __init__(self):
                super().__init__()
                self._stats["custom_field"] = 0

            def parse(self, writer: MockFileWriter) -> None:
                self._stats["custom_field"] += 1

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()
        parser.parse(MockFileWriter())

        assert parser._stats["custom_field"] == 1
        assert "parsed" in parser._stats

    def test_parser_abstractmethod_enforcement(self):
        """Тест 22: Принудительная реализация абстрактных методов."""

        # Попытка создать класс без реализации parse()
        def define_incomplete_parser1():
            class IncompleteParser1(BaseParser):
                def get_stats(self) -> Dict[str, Any]:
                    return {}

            return IncompleteParser1

        # Класс можно определить, но экземпляр создать нельзя
        IncompleteParser1 = define_incomplete_parser1()
        with pytest.raises(TypeError):
            IncompleteParser1()

        # Попытка создать класс без реализации get_stats()
        def define_incomplete_parser2():
            class IncompleteParser2(BaseParser):
                def parse(self, writer: MockFileWriter) -> None:
                    pass

            return IncompleteParser2

        # Класс можно определить, но экземпляр создать нельзя
        IncompleteParser2 = define_incomplete_parser2()
        with pytest.raises(TypeError):
            IncompleteParser2()

    def test_parser_isinstance_check(self):
        """Тест 23: Проверка isinstance для парсеров."""

        class TestParser(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser = TestParser()

        assert isinstance(parser, BaseParser)
        assert isinstance(parser, TestParser)

    def test_parser_type_check(self):
        """Тест 24: Проверка type для парсеров."""

        class TestParser1(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        class TestParser2(BaseParser):
            def parse(self, writer: MockFileWriter) -> None:
                pass

            def get_stats(self) -> Dict[str, Any]:
                return self._stats

        parser1 = TestParser1()
        parser2 = TestParser2()

        assert type(parser1) == TestParser1
        assert type(parser2) == TestParser2
        assert type(parser1) != type(parser2)
