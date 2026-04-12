"""Модуль конфигураций для параллельного парсинга.

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
from typing import Any


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

    cities: list[dict[str, Any]]
    categories: list[dict[str, Any]]
    output_dir: Path
    max_workers: int = 10
    timeout_per_url: int = 300
    output_file: str | None = None
    config: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
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
    def from_dict(cls, data: dict[str, Any]) -> ParallelRunConfig:
        """Создаёт конфигурацию из словаря.

        #190: Добавлена валидация типов входных данных.

        Args:
            data: Словарь с параметрами.

        Returns:
            Экземпляр ParallelRunConfig.

        Raises:
            TypeError: Если типы данных некорректны.
            ValueError: Если значения некорректны.

        """
        # #190: Валидация типов входных данных
        cities = data.get("cities", [])
        if not isinstance(cities, list):
            msg = f"cities должен быть списком, получен {type(cities).__name__}"
            raise TypeError(msg)

        categories = data.get("categories", [])
        if not isinstance(categories, list):
            msg = f"categories должен быть списком, получен {type(categories).__name__}"
            raise TypeError(msg)

        output_dir = data.get("output_dir", "./output")
        if not isinstance(output_dir, (str, Path)):
            msg = f"output_dir должен быть str или Path, получен {type(output_dir).__name__}"
            raise TypeError(
                msg
            )

        max_workers = data.get("max_workers", 10)
        if not isinstance(max_workers, int):
            msg = f"max_workers должен быть int, получен {type(max_workers).__name__}"
            raise TypeError(msg)

        timeout_per_url = data.get("timeout_per_url", 300)
        if not isinstance(timeout_per_url, (int, float)):
            msg = f"timeout_per_url должен быть числом, получен {type(timeout_per_url).__name__}"
            raise TypeError(
                msg
            )

        output_file = data.get("output_file")
        if output_file is not None and not isinstance(output_file, str):
            msg = f"output_file должен быть str или None, получен {type(output_file).__name__}"
            raise TypeError(
                msg
            )

        config = data.get("config")
        if config is not None and not isinstance(config, dict):
            msg = f"config должен быть dict или None, получен {type(config).__name__}"
            raise TypeError(msg)

        return cls(
            cities=cities,
            categories=categories,
            output_dir=Path(output_dir),
            max_workers=max_workers,
            timeout_per_url=int(timeout_per_url),
            output_file=output_file,
            config=config,
        )


__all__ = ["ParallelRunConfig"]
