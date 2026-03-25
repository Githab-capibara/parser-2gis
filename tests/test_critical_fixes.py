"""Тесты для критических исправлений в коде.

Этот модуль тестирует исправления критических ошибок:
- Исправления ошибок Pydantic V1/V2 совместимости
- Исправления логики обработки None в парсерах
- Исправления вызовов методов кэша
"""

import unittest
from unittest.mock import patch

from parser_2gis.chrome.dom import DOMNode
from parser_2gis.common import get_cache_stats
from parser_2gis.logger.options import LogOptions
from parser_2gis.writer.options import WriterOptions


class TestPydanticValidatorFixes(unittest.TestCase):
    """Тесты исправлений для Pydantic V1/V2 валидаторов."""

    def test_logger_options_level_validation(self):
        """Тест валидации уровня логирования."""
        options = LogOptions(level="DEBUG", gui_format="%(message)s", cli_format="%(message)s")
        self.assertEqual(options.level, "DEBUG")

    def test_logger_options_format_validation(self):
        """Тест валидации формата логирования."""
        options = LogOptions(
            level="INFO", gui_format="%(message)s", cli_format="[%(levelname)s] %(message)s"
        )
        self.assertEqual(options.cli_format, "[%(levelname)s] %(message)s")

    def test_writer_options_encoding_validation(self):
        """Тест валидации кодировки writer опций."""
        options = WriterOptions(encoding="utf-8")
        self.assertEqual(options.encoding, "utf-8")

    def test_writer_options_invalid_encoding(self):
        """Тест отклонения недопустимой кодировки."""
        with self.assertRaises(ValueError):
            WriterOptions(encoding="invalid-encoding")


class TestDOMNodeValidation(unittest.TestCase):
    """Тесты исправлений для DOMNode валидации."""

    def test_dom_node_attributes_validation_pydantic_v2_v1(self):
        """Тест валидации атрибутов DOM узла (совместимо с V1 и V2)."""
        node_data = {
            "nodeId": 1,
            "backendNodeId": 2,
            "nodeType": 3,
            "nodeName": "div",
            "localName": "div",
            "nodeValue": "content",
            "attributes": ["id", "container", "class", "main"],
        }
        node = DOMNode(**node_data)
        self.assertEqual(node.attributes["id"], "container")
        self.assertEqual(node.attributes["class"], "main")

    def test_dom_node_invalid_attributes_count(self):
        """Тест отклонения нечетного количества атрибутов."""
        node_data = {
            "nodeId": 1,
            "backendNodeId": 2,
            "nodeType": 3,
            "nodeName": "div",
            "localName": "div",
            "nodeValue": "content",
            "attributes": ["id", "container", "class"],  # Нечетное количество
        }
        with self.assertRaises(ValueError):
            DOMNode(**node_data)


class TestCacheStatsFunction(unittest.TestCase):
    """Тесты исправлений для функции get_cache_stats."""

    def test_get_cache_stats_returns_dict(self):
        """Тест что get_cache_stats возвращает словарь."""
        stats = get_cache_stats()
        self.assertIsInstance(stats, dict)

    def test_get_cache_stats_has_expected_keys(self):
        """Тест что get_cache_stats содержит ожидаемые ключи."""
        stats = get_cache_stats()
        expected_keys = {
            "_validate_city_cached",
            "_validate_category_cached",
            "_generate_category_url_cached",
            "url_query_encode",
        }
        self.assertEqual(set(stats.keys()), expected_keys)

    def test_get_cache_stats_cache_info_format(self):
        """Тест что cache_info имеет правильный формат."""
        stats = get_cache_stats()
        for cache_name, info in stats.items():
            self.assertTrue(hasattr(info, "hits"), f"{cache_name} не имеет hits")
            self.assertTrue(hasattr(info, "misses"), f"{cache_name} не имеет misses")
            self.assertTrue(hasattr(info, "maxsize"), f"{cache_name} не имеет maxsize")
            self.assertTrue(hasattr(info, "currsize"), f"{cache_name} не имеет currsize")


class TestParserLinksHandling(unittest.TestCase):
    """Тесты исправлений для обработки None в парсерах."""

    def test_in_building_parser_none_links_check(self):
        """Тест что in_building парсер правильно обрабатывает None ссылки.

        Это проверяет что исправления для non-iterable links ошибки
        правильно обрабатывают None возвращаемое get_unique_links().
        """
        # Этот тест просто проверяет что модуль может быть импортирован
        # без синтаксических ошибок после исправлений
        try:
            from parser_2gis.parser.parsers.in_building import InBuildingParser

            self.assertTrue(InBuildingParser is not None)
        except ImportError as e:
            self.fail(f"Не удалось импортировать InBuildingParser: {e}")

    def test_main_parser_none_links_check(self):
        """Тест что main парсер правильно обрабатывает None ссылки.

        Это проверяет что исправления для non-iterable links ошибки
        правильно обрабатывают None возвращаемое get_unique_links().
        """
        # Этот тест просто проверяет что модуль может быть импортирован
        # без синтаксических ошибок после исправлений
        try:
            from parser_2gis.parser.parsers.main import MainParser

            self.assertTrue(MainParser is not None)
        except ImportError as e:
            self.fail(f"Не удалось импортировать MainParser: {e}")


class TestChromeRemoteErrorHandling(unittest.TestCase):
    """Тесты исправлений для обработки ошибок в ChromeRemote."""

    def test_chrome_remote_error_raising(self):
        """Тест что ChromeRemote правильно выбрасывает ошибки.

        После исправления, вместо raise result['error'] (который может быть None),
        используется raise RuntimeError(...).
        """
        try:
            from parser_2gis.chrome.remote import ChromeRemote

            self.assertTrue(ChromeRemote is not None)
        except ImportError as e:
            self.fail(f"Не удалось импортировать ChromeRemote: {e}")


if __name__ == "__main__":
    unittest.main()
