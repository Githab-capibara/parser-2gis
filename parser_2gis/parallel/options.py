"""
Модуль опций для параллельного парсинга.

Содержит класс ParallelOptions для конфигурирования
параллельного парсинга городов.
"""

from __future__ import annotations

from pydantic import BaseModel, PositiveInt


class ParallelOptions(BaseModel):
    """Опции для параллельного парсинга.

    Атрибуты:
        use_temp_file_cleanup: Использовать автоматическую очистку временных файлов.
        temp_file_cleanup_interval: Интервал очистки временных файлов в секундах.
        max_temp_files: Максимальное количество временных файлов для мониторинга.
        orphaned_temp_file_age: Возраст временного файла в секундах, после которого он считается осиротевшим.
        merge_lock_timeout: Таймаут ожидания блокировки merge операции в секундах.
        max_lock_file_age: Максимальный возраст lock файла в секундах.
    """

    use_temp_file_cleanup: bool = True
    temp_file_cleanup_interval: PositiveInt = 60
    max_temp_files: PositiveInt = 1000
    orphaned_temp_file_age: PositiveInt = 300
    merge_lock_timeout: PositiveInt = 300
    max_lock_file_age: PositiveInt = 300
