"""Модуль опций для параллельного парсинга.

Содержит классы:
- ParallelOptions: Опции для конфигурирования параллельного парсинга
- ParallelParserConfig: Dataclass для группировки параметров парсера

Примечание:
    Константа MAX_UNIQUE_NAME_ATTEMPTS перемещена в constants.py
    для устранения дублирования.

    ParallelParserConfig vs ParallelRunConfig:
    - ParallelParserConfig (этот модуль): использует config: Configuration
      (полный объект pydantic конфигурации). Используется в тестах.
    - ParallelRunConfig (parallel/config.py): использует config: Optional[Dict]
      (словарь конфигурации). Используется в ParallelCoordinator.
    Это не дублирование, а разные конфигурации для разных сценариев использования.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, PositiveInt

from parser_2gis.constants import validate_env_int

if TYPE_CHECKING:
    from parser_2gis.config import Configuration

MAX_TEMP_FILES = validate_env_int(
    "PARSER_MAX_TEMP_FILES",
    default=1000,
    min_value=100,
    max_value=10000,
)


class ParallelOptions(BaseModel):
    """Опции для параллельного парсинга.

    Атрибуты:
        use_temp_file_cleanup: Использовать автоматическую очистку временных файлов.
        temp_file_cleanup_interval: Интервал очистки временных файлов в секундах.
        max_temp_files: Максимальное количество временных файлов для мониторинга.
        orphaned_temp_file_age: Возраст временного файла в секундах,
            после которого он считается осиротевшим.
        merge_lock_timeout: Таймаут ожидания блокировки merge операции в секундах.
        max_lock_file_age: Максимальный возраст lock файла в секундах.
        max_workers: Количество параллельных работников для парсинга.
        use_delays: Использовать задержки перед парсингом (по умолчанию True).
        initial_delay_min: Минимальная начальная задержка в секундах.
        initial_delay_max: Максимальная начальная задержка в секундах.
        launch_delay_min: Минимальная задержка перед запуском Chrome.
        launch_delay_max: Максимальная задержка перед запуском Chrome.
    """

    use_temp_file_cleanup: bool = True
    temp_file_cleanup_interval: PositiveInt = 60
    max_temp_files: PositiveInt = 1000
    orphaned_temp_file_age: PositiveInt = 60
    merge_lock_timeout: PositiveInt = 60
    max_lock_file_age: PositiveInt = 60
    max_workers: PositiveInt = 10
    # H003: Задержки опциональны, по умолчанию минимальные для производительности
    use_delays: bool = True
    initial_delay_min: float = 0.0
    initial_delay_max: float = 0.1
    launch_delay_min: float = 0.0
    launch_delay_max: float = 0.05


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

    cities: list[dict[str, Any]]
    categories: list[dict[str, Any]]
    output_dir: Path
    config: Configuration
    max_workers: int = 10
    timeout_per_url: int = 60


__all__ = ["MAX_TEMP_FILES", "ParallelOptions", "ParallelParserConfig"]
