"""
Модуль опций для параллельного парсинга.

Содержит класс ParallelOptions для конфигурирования
параллельного парсинга городов.
"""

from __future__ import annotations

from pydantic import BaseModel, PositiveInt

from parser_2gis.constants import validate_env_int

MAX_TEMP_FILES = validate_env_int(
    "PARSER_MAX_TEMP_FILES", default=1000, min_value=100, max_value=10000
)


class ParallelOptions(BaseModel):
    """Опции для параллельного парсинга.

    Атрибуты:
        use_temp_file_cleanup: Использовать автоматическую очистку временных файлов.
        temp_file_cleanup_interval: Интервал очистки временных файлов в секундах.
        max_temp_files: Максимальное количество временных файлов для мониторинга.
        orphaned_temp_file_age: Возраст временного файла в секундах, после которого он считается осиротевшим.
        merge_lock_timeout: Таймаут ожидания блокировки merge операции в секундах.
        max_lock_file_age: Максимальный возраст lock файла в секундах.
        max_workers: Количество параллельных работников для парсинга.
    """

    use_temp_file_cleanup: bool = True
    temp_file_cleanup_interval: PositiveInt = 60
    max_temp_files: PositiveInt = 1000
    orphaned_temp_file_age: PositiveInt = 300
    merge_lock_timeout: PositiveInt = 300
    max_lock_file_age: PositiveInt = 300
    max_workers: PositiveInt = 10
