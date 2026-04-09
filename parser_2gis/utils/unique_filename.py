"""Утилиты для генерации уникальных имён файлов.

ISSUE-050: Вынесено из file_manager.py и url_parser.py (strategies.py) для устранения
дублирования логики генерации уникальных имён файлов с повторными попытками.

Пример использования:
    >>> from pathlib import Path
    >>> from parser_2gis.utils.unique_filename import generate_unique_filename_with_retry
    >>> path = generate_unique_filename_with_retry(Path("/tmp"), "output", ".csv")
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from parser_2gis.constants import MAX_UNIQUE_NAME_ATTEMPTS
from parser_2gis.logger import logger


def generate_unique_filename_with_retry(
    directory: Path,
    base_name: str,
    extension: str,
    max_attempts: int = MAX_UNIQUE_NAME_ATTEMPTS,
) -> Path:
    """Генерирует уникальное имя файла с повторными попытками.

    Общая функция для устранения дублирования между:
    - parallel/strategies.py (ParseStrategy._ensure_unique_temp_file)
    - parallel/url_parser.py (parse_single_url — создание временных файлов)

    Args:
        directory: Директория для создания файла.
        base_name: Базовое имя файла (без расширения).
        extension: Расширение файла (например, ".csv").
        max_attempts: Максимальное количество попыток.

    Returns:
        Путь к созданному уникальному файлу.

    Raises:
        FileExistsError: Если не удалось создать уникальный файл.
        OSError: Если произошла ошибка файловой системы.

    """
    timestamp = str(int(time.time() * 1000000))[-10:]
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{base_name}_{timestamp}_{unique_id}{extension}"
    filepath = directory / filename

    for attempt in range(max_attempts):
        try:
            # Атомарное создание файла
            fd = os.open(str(filepath), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o644)
            os.close(fd)
            logger.log(5, "Уникальный файл атомарно создан: %s", filepath.name)
            return filepath
        except FileExistsError:
            if attempt < max_attempts - 1:
                # Генерируем новое имя
                timestamp = str(int(time.time() * 1000000))[-10:]
                unique_id = uuid.uuid4().hex[:8]
                filename = f"{base_name}_{timestamp}_{unique_id}{extension}"
                filepath = directory / filename
            else:
                logger.error(
                    "Не удалось создать уникальный файл после %d попыток: %s",
                    max_attempts,
                    filepath,
                )
                raise
        except OSError as e:
            if attempt < max_attempts - 1:
                timestamp = str(int(time.time() * 1000000))[-10:]
                unique_id = uuid.uuid4().hex[:8]
                filename = f"{base_name}_{timestamp}_{unique_id}{extension}"
                filepath = directory / filename
            else:
                logger.error("Не удалось создать файл %s: %s", filepath, e)
                raise

    return filepath
