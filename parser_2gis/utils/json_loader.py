"""Утилиты для загрузки JSON файлов с mmap поддержкой.

ISSUE-048: Вынесено из resources/cities_loader.py и cache/config_cache.py
для устранения дублирования логики загрузки JSON через mmap.

Пример использования:
    >>> from pathlib import Path
    >>> from parser_2gis.utils.json_loader import load_json_mmap
    >>> data = load_json_mmap(Path("data.json"), threshold_bytes=1048576)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from parser_2gis.logger import logger as app_logger

# Порог для использования mmap (1 MB)
DEFAULT_MMAP_THRESHOLD = 1 * 1024 * 1024


def load_json_mmap(
    file_path: Path,
    threshold_bytes: int = DEFAULT_MMAP_THRESHOLD,
    *,
    validate_size: bool = True,
    max_file_size: int | None = None,
) -> Any:
    """Загружает JSON файл с оптимизированным чтением через mmap.

    Для файлов больше threshold_bytes используется mmap для чтения,
    что снижает потребление памяти при работе с большими файлами.

    Общая функция для устранения дублирования между:
    - resources/cities_loader.py: mmap загрузка городов
    - cache/config_cache.py: mmap загрузка городов в кэше

    Args:
        file_path: Путь к JSON файлу.
        threshold_bytes: Порог размера файла для использования mmap.
        validate_size: Проверять ли размер файла.
        max_file_size: Максимальный допустимый размер файла.

    Returns:
        Распарсенные данные JSON.

    Raises:
        FileNotFoundError: Если файл не найден.
        ValueError: Если файл пустой, повреждён или слишком большой.
        OSError: Если произошла ошибка операционной системы.
        json.JSONDecodeError: Если файл содержит некорректный JSON.

    """
    if not file_path.is_file():
        app_logger.error("Файл не найден: %s", file_path)
        raise FileNotFoundError(f"Файл {file_path} не найден")

    try:
        file_size = file_path.stat().st_size
        if file_size == 0:
            app_logger.error("Файл пуст: %s", file_path)
            raise ValueError(f"Файл {file_path} пуст")

        if validate_size and max_file_size is not None and file_size > max_file_size:
            app_logger.error(
                "Файл слишком большой: %d байт (макс: %d байт)", file_size, max_file_size
            )
            raise ValueError(
                f"Файл {file_path} слишком большой ({file_size} > {max_file_size} байт)"
            )

        app_logger.debug("Размер файла: %d байт", file_size)
    except OSError as stat_error:
        app_logger.error("Ошибка получения информации о файле: %s", stat_error)
        raise OSError(f"Не удалось получить информацию о файле: {stat_error}") from stat_error

    use_mmap = file_size > threshold_bytes

    try:
        if use_mmap:
            app_logger.info(
                "Файл большой (%.2f MB), используется mmap для чтения", file_size / (1024 * 1024)
            )
            import mmap as mmap_module

            with open(file_path, "rb") as f:
                mmapped_file = mmap_module.mmap(f.fileno(), 0, access=mmap_module.ACCESS_READ)
                try:
                    json_data = mmapped_file.read().decode("utf-8")
                    return json.loads(json_data)
                finally:
                    mmapped_file.close()
        else:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)

    except json.JSONDecodeError as e:
        app_logger.error("Ошибка парсинга JSON в файле %s: %s", file_path, e)
        raise ValueError(f"Некорректный формат JSON в файле {file_path}: {e}") from e
    except OSError as e:
        app_logger.error("Ошибка ОС при чтении файла %s: %s", file_path, e)
        raise OSError(f"Не удалось прочитать файл {file_path}: {e}") from e
