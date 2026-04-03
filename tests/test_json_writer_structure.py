"""Тесты для проверки структуры JSON в json_writer.py."""

from unittest.mock import MagicMock

import pytest

from parser_2gis.writer.writers.json_writer import JSONWriter


class TestJSONWriterStructure:
    """Тесты для проверки структуры JSON данных."""

    @pytest.fixture
    def mock_writer(self, tmp_path):
        """Создает мок writer."""
        from unittest.mock import MagicMock
        from parser_2gis.writer.writers.json_writer import JSONWriter
        
        test_file = tmp_path / "test.json"
        options = MagicMock()
        options.verbose = False
        writer = JSONWriter(str(test_file), options)
        writer._file = MagicMock()
        writer._wrote_count = 0
        writer._first_item = True
        return writer

    def test_non_dict_returns_silently(self, mock_writer):
        """Не словарь должен пропускаться без записи."""
        mock_writer._writedoc("not a dict")
        mock_writer._file.write.assert_not_called()

    def test_missing_result_key_returns_silently(self, mock_writer):
        """Отсутствующий ключ 'result' должен пропускаться."""
        mock_writer._writedoc({"data": "value"})
        mock_writer._file.write.assert_not_called()

    def test_result_not_dict_returns_silently(self, mock_writer):
        """'result' не являющийся словарём должен пропускаться."""
        mock_writer._writedoc({"result": "not a dict"})
        mock_writer._file.write.assert_not_called()

    def test_missing_items_key_returns_silently(self, mock_writer):
        """Отсутствующий ключ 'items' должен пропускаться."""
        mock_writer._writedoc({"result": {"data": "value"}})
        mock_writer._file.write.assert_not_called()

    def test_empty_items_list_returns_silently(self, mock_writer):
        """Пустой список 'items' должен пропускаться."""
        mock_writer._writedoc({"result": {"items": []}})
        mock_writer._file.write.assert_not_called()

    def test_items_not_list_returns_silently(self, mock_writer):
        """'items' не являющийся списком должен пропускаться."""
        mock_writer._writedoc({"result": {"items": "not a list"}})
        mock_writer._file.write.assert_not_called()

    def test_valid_structure_writes(self, mock_writer):
        """Валидная структура должна записываться."""

        mock_writer._writedoc({"result": {"items": [{"name": "Test"}]}})
        mock_writer._file.write.assert_called()

    def test_valid_structure_with_verbose_logs_name(self):
        """Валидная структура с verbose должна логировать имя."""
        options = MagicMock()
        options.verbose = True

        writer = JSONWriter("/tmp/test.json", options)
        writer._file = MagicMock()
        writer._wrote_count = 0
        writer._first_item = True

        writer._writedoc(
            {
                "result": {
                    "items": [{"name": "Test Company", "name_ex": {"primary": "Primary Name"}}]
                }
            }
        )

        writer._file.write.assert_called()
