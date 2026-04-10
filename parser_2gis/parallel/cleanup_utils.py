"""Общие утилиты очистки для параллельного парсинга.

Вынесены из error_handler.py, url_parser.py, strategies.py, helpers.py (#63).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path



def cleanup_temp_file(
    temp_filepath: Path,
    log_func: Callable[[str, str], None] | None = None,
    description: str = "Временный файл удалён",
) -> None:
    """Очищает временный файл.

    Args:
        temp_filepath: Путь к временному файлу.
        log_func: Функция логирования (принимает message, level).
            Если None, используется logger из parser_2gis.logger.
        description: Описание операции для логирования.

    """
    # Lazy import для предотвращения циклических зависимостей
    if log_func is None:
        from parser_2gis.logger import logger as _logger

        def _default_log(msg: str, level: str = "info") -> None:
            getattr(_logger, level)(msg)

        log_func = _default_log

    try:
        if temp_filepath.exists():
            temp_filepath.unlink()
            log_func(f"{description}: {temp_filepath.name}", "debug")
    except (OSError, RuntimeError, TypeError, ValueError) as cleanup_error:
        log_func(
            f"Не удалось удалить временный файл {temp_filepath.name}: {cleanup_error}", "warning"
        )
