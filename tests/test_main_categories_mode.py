#!/usr/bin/env python3
"""
Тесты для проверки валидации аргументов --categories-mode в main.py.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Добавляем путь к пакету
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser_2gis.cli.arguments import parse_arguments  # noqa: E402


class TestCategoriesModeValidation:
    """Тесты валидации аргументов для --categories-mode."""

    def test_categories_mode_requires_cities(self):
        """--categories-mode без --cities должен вызывать ошибку."""
        with patch(
            "sys.argv", ["parser-2gis", "--categories-mode", "-o", "output.csv", "-f", "csv"]
        ):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 2  # Код ошибки argparse

    def test_categories_mode_with_cities_valid(self, tmp_path: Path):
        """--categories-mode с --cities должен проходить валидацию."""
        # Создаём фиктивный cities.json во временной директории
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        cities_file = data_dir / "cities.json"
        cities_file.write_text(
            '[{"code": "omsk", "domain": "ru", "name": "Омск", "country_code": "ru"}]'
        )

        output_file = tmp_path / "output.csv"

        with patch(
            "sys.argv",
            [
                "parser-2gis",
                "--cities",
                "omsk",
                "--categories-mode",
                "-o",
                str(output_file),
                "-f",
                "csv",
            ],
        ):
            args, config = parse_arguments()

            assert args.cities == ["omsk"]
            assert args.categories_mode is True

    def test_url_not_required_when_cities_specified(self, tmp_path: Path):
        """-i/--url не обязателен, когда указан --cities."""
        # Создаём фиктивный cities.json во временной директории
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        cities_file = data_dir / "cities.json"
        cities_file.write_text(
            '[{"code": "omsk", "domain": "ru", "name": "Омск", "country_code": "ru"}]'
        )

        output_file = tmp_path / "output.csv"

        with patch(
            "sys.argv", ["parser-2gis", "--cities", "omsk", "-o", str(output_file), "-f", "csv"]
        ):
            args, config = parse_arguments()

            assert args.cities == ["omsk"]
            assert args.url is None

    def test_requires_url_or_cities(self):
        """Требуется хотя бы один источник URL: -i или --cities."""
        with patch("sys.argv", ["parser-2gis", "-o", "output.csv", "-f", "csv"]):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 2

    def test_both_url_and_cities_valid(self, tmp_path: Path):
        """Можно указать и -i и --cities одновременно."""
        # Создаём фиктивный cities.json во временной директории
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        cities_file = data_dir / "cities.json"
        cities_file.write_text(
            '[{"code": "omsk", "domain": "ru", "name": "Омск", "country_code": "ru"}]'
        )

        output_file = tmp_path / "output.csv"

        with patch(
            "sys.argv",
            [
                "parser-2gis",
                "-i",
                "https://2gis.ru/moscow/search/Аптеки",
                "--cities",
                "omsk",
                "-o",
                str(output_file),
                "-f",
                "csv",
            ],
        ):
            args, config = parse_arguments()

            assert args.url is not None
            assert args.cities == ["omsk"]


class TestParallelWorkersValidation:
    """Тесты валидации --parallel-workers."""

    def test_parallel_workers_default(self, tmp_path: Path):
        """Проверка значения по умолчанию."""
        # Создаём фиктивный cities.json во временной директории
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        cities_file = data_dir / "cities.json"
        cities_file.write_text(
            '[{"code": "omsk", "domain": "ru", "name": "Омск", "country_code": "ru"}]'
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)

        with patch(
            "sys.argv",
            [
                "parser-2gis",
                "--cities",
                "omsk",
                "--categories-mode",
                "-o",
                str(output_dir),
                "-f",
                "csv",
            ],
        ):
            args, config = parse_arguments()

            # Проверяем что parallel.max_workers имеет значение по умолчанию
            # Аргумент парсится как 'parallel.max_workers' (с точкой в имени)
            assert hasattr(args, "parallel.max_workers")
            # Значение по умолчанию 10
            assert getattr(args, "parallel.max_workers") == 10

    def test_parallel_workers_custom(self, tmp_path: Path):
        """Проверка пользовательского значения."""
        # Создаём фиктивный cities.json во временной директории
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        cities_file = data_dir / "cities.json"
        cities_file.write_text(
            '[{"code": "omsk", "domain": "ru", "name": "Омск", "country_code": "ru"}]'
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)

        with patch(
            "sys.argv",
            [
                "parser-2gis",
                "--cities",
                "omsk",
                "--categories-mode",
                "--parallel.max-workers",
                "5",
                "-o",
                str(output_dir),
                "-f",
                "csv",
            ],
        ):
            args, config = parse_arguments()

            assert hasattr(args, "parallel.max_workers")
            assert getattr(args, "parallel.max_workers") == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
