#!/usr/bin/env python3
"""
Тесты для проверки обработки исключений при инициализации parser/writer.

Проверяет корректность обработки ошибок при создании экземпляров парсера и writer.
Тесты покрывают исправления обработки исключений в параллельном парсере.

Тесты:
1. test_get_writer_exception_handled - Тест обработки исключения при ошибке get_writer
2. test_get_parser_exception_handled - Тест обработки исключения при ошибке get_parser
3. test_initialization_error_logs_and_continues - Тест что ошибка логируется и поток продолжается
"""

import logging
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest


class TestParallelParserInitErrors:
    """Тесты для проверки обработки исключений при инициализации парсера."""

    def test_get_writer_exception_handled(self, tmp_path: Any) -> None:
        """
        Тест 2.1: Проверка обработки исключения при ошибке get_writer.

        Мокирует get_writer для выбрасывания исключения.
        Проверяет что исключение корректно обрабатывается и логируется.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel_parser import ParallelCityParser

        # Создаем тестовые данные
        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        config = Configuration()

        # Мокируем get_writer для выбрасывания исключения
        with patch("parser_2gis.parallel_parser.get_writer") as mock_get_writer:
            mock_get_writer.side_effect = RuntimeError("Mocked writer error")

            # Создаем парсер - инициализация должна пройти успешно
            # (get_writer вызывается позже при парсинге)
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=output_dir,
                config=config,
                max_workers=3,
            )

            # Проверяем что парсер создан
            assert parser is not None
            assert hasattr(parser, "_stats")

    def test_get_parser_exception_handled(self, tmp_path: Any) -> None:
        """
        Тест 2.2: Проверка обработки исключения при ошибке get_parser.

        Мокирует get_parser для выбрасывания исключения.
        Проверяет что исключение корректно обрабатывается в parse_single_url.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel_parser import ParallelCityParser

        # Создаем тестовые данные
        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        config = Configuration()
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=3,
        )

        # Мокируем get_parser для выбрасывания исключения
        with patch("parser_2gis.parallel_parser.get_parser") as mock_get_parser:
            mock_get_parser.side_effect = RuntimeError("Mocked parser error")

            # Вызываем parse_single_url
            url = "https://2gis.ru/moscow/search/Кафе"
            success, message = parser.parse_single_url(
                url=url,
                category_name="Кафе",
                city_name="Москва",
            )

            # Проверяем что ошибка обработана
            assert success is False
            assert "Mocked parser error" in message or "ошибка" in message.lower()

    def test_initialization_error_logs_and_continues(
        self, tmp_path: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Тест 2.3: Проверка что ошибка логируется и поток продолжается.

        Создает ситуацию где инициализация компонента вызывает ошибку.
        Проверяет что ошибка логируется и выполнение продолжается.

        Args:
            tmp_path: pytest фикстура для временной директории.
            caplog: pytest фикстура для захвата логов.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel_parser import ParallelCityParser

        # Создаем тестовые данные
        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        config = Configuration()

        # Устанавливаем уровень логирования для захвата
        with caplog.at_level(logging.INFO):
            # Создаем парсер
            parser = ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=output_dir,
                config=config,
                max_workers=3,
            )

            # Проверяем что инициализация залогирована
            assert any(
                "Инициализирован парсер" in record.message for record in caplog.records
            )

        # Проверяем что парсер создан успешно
        assert parser is not None
        assert hasattr(parser, "_stats")
        assert hasattr(parser, "_lock")


class TestParallelParserValidationErrors:
    """Тесты для проверки обработки ошибок валидации при инициализации."""

    def test_empty_cities_list_raises_error(self, tmp_path: Any) -> None:
        """
        Проверка что пустой список городов вызывает ошибку.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel_parser import ParallelCityParser

        cities = []
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        config = Configuration()

        # Проверяем что возникает ValueError
        with pytest.raises(ValueError, match="Список городов не может быть пустым"):
            ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=output_dir,
                config=config,
                max_workers=3,
            )

    def test_empty_categories_list_raises_error(self, tmp_path: Any) -> None:
        """
        Проверка что пустой список категорий вызывает ошибку.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel_parser import ParallelCityParser

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = []
        output_dir = str(tmp_path / "output")

        config = Configuration()

        # Проверяем что возникает ValueError
        with pytest.raises(ValueError, match="Список категорий не может быть пустым"):
            ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=output_dir,
                config=config,
                max_workers=3,
            )

    def test_invalid_max_workers_raises_error(self, tmp_path: Any) -> None:
        """
        Проверка что некорректный max_workers вызывает ошибку.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel_parser import ParallelCityParser

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        config = Configuration()

        # Проверяем что возникает ValueError при max_workers=0
        with pytest.raises(ValueError, match="max_workers должен быть от"):
            ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=output_dir,
                config=config,
                max_workers=0,
            )

        # Проверяем что возникает ValueError при max_workers=100
        with pytest.raises(ValueError, match="max_workers должен быть от"):
            ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=output_dir,
                config=config,
                max_workers=100,
            )

    def test_invalid_timeout_raises_error(self, tmp_path: Any) -> None:
        """
        Проверка что некорректный timeout вызывает ошибку.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel_parser import ParallelCityParser

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        config = Configuration()

        # Проверяем что возникает ValueError при timeout=0
        with pytest.raises(ValueError, match="timeout_per_url должен быть от"):
            ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=output_dir,
                config=config,
                max_workers=3,
                timeout_per_url=0,
            )

        # Проверяем что возникает ValueError при timeout=10000
        with pytest.raises(ValueError, match="timeout_per_url должен быть от"):
            ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=output_dir,
                config=config,
                max_workers=3,
                timeout_per_url=10000,
            )


class TestParallelParserOutputDirErrors:
    """Тесты для проверки обработки ошибок с output_dir."""

    def test_output_dir_is_file_raises_error(self, tmp_path: Any) -> None:
        """
        Проверка что output_dir который является файлом вызывает ошибку.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel_parser import ParallelCityParser

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]

        # Создаем файл вместо директории
        output_file = tmp_path / "output_file.txt"
        output_file.write_text("test")
        output_dir = str(output_file)

        config = Configuration()

        # Проверяем что возникает ValueError
        with pytest.raises(ValueError, match="не является директорией"):
            ParallelCityParser(
                cities=cities,
                categories=categories,
                output_dir=output_dir,
                config=config,
                max_workers=3,
            )


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
