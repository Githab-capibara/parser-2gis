"""Общие утилиты для работы с именами файлов.

Вынесены из merger.py, file_merger.py, parallel_parser.py (#64).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING



def extract_category_from_filename(
    csv_file: Path, log_func: Callable[[str, str], None] | None = None
) -> str:
    """Извлекает название категории из имени CSV файла.

    Формат имени файла: ``{city}_{category}.csv``.
    Категория извлекается как часть после последнего подчёркивания.

    Args:
        csv_file: Путь к CSV файлу.
        log_func: Функция логирования (принимает message, level).
            Если None, предупреждение не логируется.

    Returns:
        Название категории.

    """
    stem = csv_file.stem
    last_underscore_idx = stem.rfind("_")

    if last_underscore_idx > 0:
        return stem[last_underscore_idx + 1 :].replace("_", " ")

    category = stem.replace("_", " ")

    if log_func is not None:
        log_func(f"Предупреждение: файл {csv_file.name} не содержит категорию в имени", "warning")

    return category
