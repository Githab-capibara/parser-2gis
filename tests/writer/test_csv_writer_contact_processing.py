"""
Тесты для обработки контактов в writer/writers/csv_writer.py.

Проверяет:
- Корректную обработку контактов с отсутствующими значениями
- Продолжение обработки следующих контактов при пропуске текущего
"""

import contextlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from parser_2gis.writer.writers.csv_writer import CSVWriter


class TestCSVWriterContactProcessing:
    """Тесты обработки контактов в CSVWriter."""

    @pytest.fixture
    def mock_options(self) -> MagicMock:
        """Создает mock опций.

        Returns:
            MagicMock с опциями.
        """
        options = MagicMock()
        options.verbose = False
        options.encoding = "utf-8-sig"
        options.csv.columns_per_entity = 3
        options.csv.add_rubrics = True
        options.csv.add_comments = False
        options.csv.remove_empty_columns = False
        options.csv.remove_duplicates = False
        options.csv.join_char = ", "
        return options

    @pytest.fixture
    def temp_output_path(self, tmp_path: Path) -> Path:
        """Создает временный путь для вывода.

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            Путь к временному файлу.
        """
        # Используем только имя файла, чтобы.FileWriter не обрезал путь
        return Path("test_output_contacts.csv")

    @pytest.fixture
    def csv_writer(self, mock_options, temp_output_path) -> CSVWriter:
        """Создает CSVWriter для тестов.

        Args:
            mock_options: Mock опций.
            temp_output_path: Путь к временному файлу.

        Returns:
            CSVWriter экземпляр.
        """
        writer = CSVWriter(file_path=str(temp_output_path), options=mock_options)
        yield writer
        with contextlib.suppress(Exception):
            writer.close()
        # Удаляем файл после теста
        actual_path = Path.cwd() / "test_output_contacts.csv"
        if actual_path.exists():
            actual_path.unlink()

    def test_append_contact_continues_on_empty_value(
        self, csv_writer: CSVWriter, temp_output_path: Path
    ) -> None:
        """Тест, что append_contact продолжает обработку при пустом значении контакта.

        Проверяет:
        - Если у контакта отсутствует значение, обработка продолжается
        - Следующие контакты обрабатываются корректно
        """
        # Создаем mock документ с несколькими контактами
        # Один контакт будет иметь пустое значение, другой - корректное
        catalog_doc = {
            "meta": {"code": 200},
            "result": {
                "items": [
                    {
                        "type": "branch",
                        "id": "123",
                        "locale": "ru_RU",
                        "name": "Test Business",
                        "contact_groups": [
                            {
                                "contacts": [
                                    # Контакт с пустым value (должен быть пропущен)
                                    {"type": "phone", "value": "", "comment": "First phone"},
                                    # Контакт с text (должен быть обработан)
                                    {
                                        "type": "phone",
                                        "value": "+7 (999) 123-45-67",
                                        "text": "+7 (999) 123-45-67",
                                        "comment": "Second phone",
                                    },
                                ]
                            }
                        ],
                        "point": {"lat": 55.7558, "lon": 37.6173},
                        "url": "https://example.com",
                    }
                ]
            },
        }

        # Записываем данные
        with csv_writer:
            csv_writer.write(catalog_doc)

        # Читаем результат (файл создается в текущей рабочей директории)
        actual_path = Path.cwd() / "test_output_contacts.csv"
        with open(actual_path, encoding="utf-8-sig") as f:
            content = f.read()

        # Проверяем, что второй телефон записан (форматированный)
        assert "89991234567" in content

        # Проверяем, что записана только одна строка данных (заголовок + 1 строка)
        lines = content.strip().split("\n")
        assert len(lines) == 2  # заголовок + 1 строка данных

    def test_append_contact_processes_multiple_valid_contacts(
        self, csv_writer: CSVWriter, temp_output_path: Path
    ) -> None:
        """Тест обработки нескольких валидных контактов.

        Проверяет:
        - Все валидные контакты обрабатываются
        """
        catalog_doc = {
            "meta": {"code": 200},
            "result": {
                "items": [
                    {
                        "type": "branch",
                        "id": "123",
                        "locale": "ru_RU",
                        "name": "Test Business",
                        "contact_groups": [
                            {
                                "contacts": [
                                    {
                                        "type": "phone",
                                        "value": "+7 (999) 111-11-11",
                                        "text": "+7 (999) 111-11-11",
                                    },
                                    {
                                        "type": "phone",
                                        "value": "+7 (999) 222-22-22",
                                        "text": "+7 (999) 222-22-22",
                                    },
                                    {
                                        "type": "phone",
                                        "value": "+7 (999) 333-33-33",
                                        "text": "+7 (999) 333-33-33",
                                    },
                                ]
                            }
                        ],
                        "point": {"lat": 55.7558, "lon": 37.6173},
                        "url": "https://example.com",
                    }
                ]
            },
        }

        with csv_writer:
            csv_writer.write(catalog_doc)

        # Читаем результат (файл создается в текущей рабочей директории)
        actual_path = Path.cwd() / "test_output_contacts.csv"
        with open(actual_path, encoding="utf-8-sig") as f:
            content = f.read()

        # Проверяем, что все три телефона записаны (форматированные)
        assert "89991111111" in content
        assert "89992222222" in content
        assert "89993333333" in content
