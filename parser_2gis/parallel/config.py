"""
Модуль конфигураций для параллельного парсинга.

Предоставляет dataclass ParallelRunConfig для группировки параметров
запуска параллельного парсинга. Это устраняет нарушение Data Clumps
(группы одинаковых параметров в нескольких функциях).

Пример использования:
    >>> from parser_2gis.parallel.config import ParallelRunConfig
    >>> config = ParallelRunConfig(
    ...     cities=[{"name": "Москва"}],
    ...     categories=[{"name": "Кафе"}],
    ...     output_dir="./output",
    ...     max_workers=10,
    ... )
    >>> parser = ParallelCoordinator(**config.to_dict())
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ParallelRunConfig:
    """Конфигурация для запуска параллельного парсинга.

    Dataclass для группировки параметров параллельного парсинга,
    устраняет нарушение Data Clumps (группы одинаковых параметров).

    Attributes:
        cities: Список городов для парсинга.
        categories: Список категорий для парсинга.
        output_dir: Директория для сохранения результатов.
        max_workers: Максимальное количество рабочих потоков.
        timeout_per_url: Таймаут на один URL в секундах.
        output_file: Имя выходного файла (опционально).
        config: Словарь конфигурации парсера (опционально).

    Example:
        >>> from parser_2gis.parallel.config import ParallelRunConfig
        >>> cfg = ParallelRunConfig(
        ...     cities=[{"name": "Москва", "domain": "moscow.2gis.ru"}],
        ...     categories=[{"name": "Кафе", "id": 123}],
        ...     output_dir=Path("./output"),
        ...     max_workers=5,
        ...     timeout_per_url=300,
        ... )
        >>> parser = ParallelCoordinator(**cfg.to_dict())
    """

    cities: List[Dict[str, Any]]
    categories: List[Dict[str, Any]]
    output_dir: Path
    max_workers: int = 10
    timeout_per_url: int = 300
    output_file: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует dataclass в словарь.

        Returns:
            Словарь с параметрами конфигурации.
        """
        result = {
            "cities": self.cities,
            "categories": self.categories,
            "output_dir": str(self.output_dir),
            "max_workers": self.max_workers,
            "timeout_per_url": self.timeout_per_url,
        }
        if self.output_file:
            result["output_file"] = self.output_file
        if self.config:
            result["config"] = self.config
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParallelRunConfig":
        """Создаёт конфигурацию из словаря.

        Args:
            data: Словарь с параметрами.

        Returns:
            Экземпляр ParallelRunConfig.
        """
        return cls(
            cities=data.get("cities", []),
            categories=data.get("categories", []),
            output_dir=Path(data.get("output_dir", "./output")),
            max_workers=data.get("max_workers", 10),
            timeout_per_url=data.get("timeout_per_url", 300),
            output_file=data.get("output_file"),
            config=data.get("config"),
        )


__all__ = ["ParallelRunConfig"]
