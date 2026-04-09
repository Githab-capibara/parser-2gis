"""
Тесты для основного парсера 2GIS.

Проверяют интеграционное тестирование парсера с различными форматами вывода.
"""

import csv
import json
import os
import sys
from tempfile import TemporaryDirectory

import pytest

from parser_2gis import main as parser_main


def check_csv_result(result_path, num_records):
    """Проверка CSV вывода.

    Args:
        result_path: Путь к CSV файлу.
        num_records: Ожидаемое количество записей.
    """
    with open(result_path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        assert len(list(reader)) == num_records + 1  # num_records + заголовок


def check_json_result(result_path, num_records):
    """Проверка JSON вывода.

    Args:
        result_path: Путь к JSON файлу.
        num_records: Ожидаемое количество записей.
    """
    with open(result_path, encoding="utf-8-sig", errors="replace") as f:
        doc = json.load(f)
        assert len(doc) == num_records


# Тестовые данные: формат и функция проверки
testdata = [["csv", check_csv_result], ["json", check_json_result]]


@pytest.mark.parametrize("format, result_checker", testdata)
@pytest.mark.requires_network
@pytest.mark.requires_chrome
def test_parser(monkeypatch, format, result_checker, num_records=5):
    """Парсинг TOP `num_records` записей и проверка результирующего файла.

    Args:
        monkeypatch: pytest fixture для замены атрибутов.
        format: Формат результата ('csv' или 'json').
        result_checker: Функция проверки результата.
        num_records: Количество записей для парсинга.
    """
    with monkeypatch.context() as m, TemporaryDirectory() as tmpdir:
        result_path = os.path.join(tmpdir, f"output.{format}")

        m.setattr(
            sys,
            "argv",
            [
                os.path.abspath(__file__),
                "-i",
                "https://2gis.ru/moscow/search/Аптеки",
                "-o",
                result_path,
                "-f",
                format,
                "--parser.max-records",
                f"{num_records}",
                "--chrome.headless",
                "yes",
            ],
        )

        # Запускаем парсер на популярном запросе,
        # который должен иметь как минимум num_records записей.
        parser_main()

        # Проверяем результат парсинга
        result_checker(result_path, num_records)
