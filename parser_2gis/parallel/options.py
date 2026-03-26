"""
Модуль опций для параллельного парсинга.

Содержит классы:
- ParallelOptions: Опции для конфигурирования параллельного парсинга
- ParallelParserConfig: Dataclass для группировки параметров парсера
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from pydantic import BaseModel, PositiveInt

from parser_2gis.constants import validate_env_int

if TYPE_CHECKING:
    from parser_2gis.config import Configuration

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


@dataclass
class ParallelParserConfig:
    """Конфигурация для параллельного парсера.

    Dataclass для группировки параметров парсера, устраняет
    нарушение Data Clumps (группы одинаковых параметров).

    Attributes:
        cities: Список городов для парсинга.
        categories: Список категорий для парсинга.
        output_dir: Папка для сохранения результатов.
        config: Конфигурация парсера.
        max_workers: Максимальное количество рабочих потоков.
        timeout_per_url: Таймаут на один URL в секундах.

    Example:
        >>> from parser_2gis.parallel.options import ParallelParserConfig
        >>> cfg = ParallelParserConfig(
        ...     cities=[{"code": "msk", "domain": "moscow.2gis.ru"}],
        ...     categories=[{"name": "Кафе", "query": "cafe"}],
        ...     output_dir=Path("./output"),
        ...     config=Configuration(),
        ...     max_workers=5,
        ... )
        >>> parser = ParallelCityParser(**cfg.__dict__)
    """

    cities: List[Dict[str, Any]]
    categories: List[Dict[str, Any]]
    output_dir: Path
    config: Configuration
    max_workers: int = 10
    timeout_per_url: int = 300


__all__ = ["ParallelOptions", "ParallelParserConfig", "MAX_TEMP_FILES"]
