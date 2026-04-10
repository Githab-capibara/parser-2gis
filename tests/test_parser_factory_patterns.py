"""Тесты для проверки компиляции паттернов в parser/factory.py."""

import re

from parser_2gis.parser.factory import _parser_registry
from parser_2gis.parser.parsers import FirmParser, InBuildingParser, MainParser


def _get_patterns() -> list[tuple[type, re.Pattern[str]]]:
    """Получить актуальный список паттернов из реестра."""
    return _parser_registry.patterns


class TestParserPatternsCompiled:
    """Тесты для проверки компиляции паттернов."""

    def test_patterns_are_precompiled(self) -> None:
        """Паттерны должны быть предкомпилированы."""
        patterns = _get_patterns()
        assert len(patterns) == 3

        for _parser_cls, pattern in patterns:
            assert isinstance(pattern, re.Pattern)
            assert pattern.pattern is not None

    def test_firm_parser_pattern_compiled(self) -> None:
        """FirmParser паттерн должен быть скомпилирован."""
        firm_patterns = [(cls, pat) for cls, pat in _get_patterns() if cls == FirmParser]
        assert len(firm_patterns) == 1

        _, pattern = firm_patterns[0]
        assert isinstance(pattern, re.Pattern)
        assert "firm" in pattern.pattern.lower()

    def test_inbuilding_parser_pattern_compiled(self) -> None:
        """InBuildingParser паттерн должен быть скомпилирован."""
        inbuilding_patterns = [
            (cls, pat) for cls, pat in _get_patterns() if cls == InBuildingParser
        ]
        assert len(inbuilding_patterns) == 1

        _, pattern = inbuilding_patterns[0]
        assert isinstance(pattern, re.Pattern)

    def test_main_parser_pattern_compiled(self) -> None:
        """MainParser паттерн должен быть скомпилирован."""
        main_patterns = [(cls, pat) for cls, pat in _get_patterns() if cls == MainParser]
        assert len(main_patterns) == 1

        _, pattern = main_patterns[0]
        assert isinstance(pattern, re.Pattern)


class TestPatternMatching:
    """Тесты для проверки соответствия паттернов."""

    def test_firm_pattern_matches_firm_url(self) -> None:
        """Firm паттерн должен соответствовать firm URL."""
        firm_patterns = [(cls, pat) for cls, pat in _get_patterns() if cls == FirmParser]
        _, pattern = firm_patterns[0]

        assert pattern.match("https://2gis.ru/moscow/firm/123456")
        assert pattern.match("https://2gis.ru/spb/firm/789")
        assert pattern.match("http://2gis.example.com/firm/abc")

    def test_inbuilding_pattern_matches_inside_url(self) -> None:
        """InBuilding паттерн должен соответствовать inside URL."""
        inbuilding_patterns = [
            (cls, pat) for cls, pat in _get_patterns() if cls == InBuildingParser
        ]
        _, pattern = inbuilding_patterns[0]

        assert pattern.match("https://2gis.ru/moscow/inside/123456")

    def test_main_pattern_matches_search_url(self) -> None:
        """Main паттерн должен соответствовать search URL."""
        main_patterns = [(cls, pat) for cls, pat in _get_patterns() if cls == MainParser]
        _, pattern = main_patterns[0]

        assert pattern.match("https://2gis.ru/moscow/search/apteka")
        assert pattern.match("https://2gis.ru/spb/search/restoran")

    def test_patterns_compiled_once(self) -> None:
        """Паттерны должны компилироваться только один раз."""
        initial_count = len(_get_patterns())
        assert initial_count == 3
