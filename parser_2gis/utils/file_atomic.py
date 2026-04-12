"""Атомарные файловые операции для parser-2gis.

ISSUE-047: Вынесено из parallel_parser.py и merger.py для устранения дублирования
логики финализации (cleanup, os.replace/shutil.move).

Пример использования:
    >>> from pathlib import Path
    >>> from parser_2gis.utils.file_atomic import atomic_replace
    >>> atomic_replace(Path("temp.csv"), Path("final.csv"))
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from parser_2gis.logger import logger as app_logger


def atomic_replace(src: Path, dst: Path, *, log_debug: bool = False) -> bool:
    """Атомарно заменяет файл dst файлом src.

    Использует os.replace() для атомарной замены. Если os.replace() не удаётся
    (например, на разных файловых системах), использует shutil.move() как fallback.

    Общая функция для устранения дублирования между:
    - parallel_parser.py: os.replace + shutil.move fallback
    - merger.py: os.replace + shutil.move fallback
    - file_merger.py: os.replace + shutil.move fallback
    - strategies.py (ParseStrategy): os.replace + shutil.move fallback
    - coordinator.py: shutil.move

    Args:
        src: Путь к исходному (временному) файлу.
        dst: Путь к целевому файлу.
        log_debug: Логировать ли отладочные сообщения.

    Returns:
        True если операция успешна.

    Raises:
        OSError: Если ни os.replace(), ни shutil.move() не сработали.

    """
    try:
        os.replace(str(src), str(dst))
        if log_debug:
            app_logger.debug("Файл атомарно заменён: %s → %s", src.name, dst.name)
        return True
    except OSError as replace_error:
        app_logger.debug(
            "Не удалось переименовать файл (OSError): %s. Используем shutil.move", replace_error,
        )
        try:
            shutil.move(str(src), str(dst))
            if log_debug:
                app_logger.debug("Файл перемещён через shutil.move: %s → %s", src.name, dst.name)
            return True
        except (OSError, RuntimeError, ValueError) as move_error:
            app_logger.error("Не удалось переместить временный файл %s: %s", src, move_error)
            # Попытка cleanup временного файла
            try:
                if src.exists():
                    src.unlink()
            except OSError:
                pass
            raise


def safe_file_cleanup(file_path: Path, description: str = "файл") -> bool:
    """Безопасно удаляет файл с обработкой ошибок.

    Args:
        file_path: Путь к файлу для удаления.
        description: Описание файла для логирования.

    Returns:
        True если файл успешно удалён, False если произошла ошибка.

    """
    if not file_path.exists():
        return True

    try:
        file_path.unlink()
        app_logger.debug("%s удалён: %s", description.capitalize(), file_path)
        return True
    except OSError as cleanup_error:
        app_logger.warning("Не удалось удалить %s %s: %s", description, file_path, cleanup_error)
        return False
