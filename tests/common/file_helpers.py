"""Вспомогательные функции для создания временных файлов в тестах."""

import csv
import json
from pathlib import Path
from typing import Any


def create_temp_csv(tmp_path: Path, headers: list[str], rows: list[list[str]], suffix: str = ".csv") -> Path:
    """Создаёт временный CSV файл и возвращает путь.

    Args:
        tmp_path: Базовая директория для временных файлов.
        headers: Заголовки CSV.
        rows: Строки данных.
        suffix: Расширение файла.

    Returns:
        Путь к созданному файлу.
    """
    file_path = tmp_path / f"test_{len(list(tmp_path.glob('*.csv')))}{suffix}"
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return file_path


def create_temp_json(tmp_path: Path, data: Any, suffix: str = ".json") -> Path:
    """Создаёт временный JSON файл.

    Args:
        tmp_path: Базовая директория для временных файлов.
        data: Данные для сериализации.
        suffix: Расширение файла.

    Returns:
        Путь к созданному файлу.
    """
    file_path = tmp_path / f"test_{len(list(tmp_path.glob('*.json')))}{suffix}"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return file_path


def create_temp_log(tmp_path: Path, lines: list[str], suffix: str = ".log") -> Path:
    """Создаёт временный log файл.

    Args:
        tmp_path: Базовая директория для временных файлов.
        lines: Строки лога.
        suffix: Расширение файла.

    Returns:
        Путь к созданному файлу.
    """
    file_path = tmp_path / f"test_{len(list(tmp_path.glob('*.log')))}{suffix}"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return file_path
