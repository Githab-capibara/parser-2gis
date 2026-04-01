"""Модуль конфигураций для CLI.

Предоставляет dataclass CLIRunConfig для группировки параметров
запуска CLI. Это устраняет нарушение Data Clumps
(группы одинаковых параметров в нескольких функциях).

Пример использования:
    >>> from parser_2gis.cli.config import CLIRunConfig
    >>> config = CLIRunConfig(
    ...     urls=["https://2gis.ru/moscow/search/cafe"],
    ...     output_dir="./output",
    ...     format="csv",
    ...     parallel=True,
    ... )
    >>> run_parser(config)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CLIRunConfig:
    """Конфигурация для запуска CLI.

    Dataclass для группировки параметров CLI,
    устраняет нарушение Data Clumps (группы одинаковых параметров).

    Attributes:
        urls: Список URL для парсинга.
        cities: Список городов для парсинга (для параллельного режима).
        categories: Список категорий для парсинга (для параллельного режима).
        output_dir: Директория для сохранения результатов.
        output_file: Имя выходного файла.
        format: Формат выходного файла (csv, xlsx, json).
        parallel: Использовать параллельный парсинг.
        max_workers: Максимальное количество рабочих потоков.
        timeout: Таймаут на один URL в секундах.
        log_level: Уровень логирования.
        log_file: Путь к файлу логов.
        verbose: Включить подробный вывод.
        config_path: Путь к файлу конфигурации.

    Example:
        >>> from parser_2gis.cli.config import CLIRunConfig
        >>> cfg = CLIRunConfig(
        ...     urls=["https://2gis.ru/moscow/search/cafe"],
        ...     output_dir=Path("./output"),
        ...     format="csv",
        ...     parallel=False,
        ...     max_workers=5,
        ... )

    """

    urls: list[str] = field(default_factory=list)
    cities: list[dict[str, Any]] = field(default_factory=list)
    categories: list[dict[str, Any]] = field(default_factory=list)
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    output_file: str | None = None
    format: str = "csv"
    parallel: bool = False
    max_workers: int = 10
    timeout: int = 300
    log_level: str = "INFO"
    log_file: Path | None = None
    verbose: bool = False
    config_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """Преобразует dataclass в словарь.

        Returns:
            Словарь с параметрами конфигурации.

        """
        return {
            "urls": self.urls,
            "cities": self.cities,
            "categories": self.categories,
            "output_dir": str(self.output_dir),
            "output_file": self.output_file,
            "format": self.format,
            "parallel": self.parallel,
            "max_workers": self.max_workers,
            "timeout": self.timeout,
            "log_level": self.log_level,
            "log_file": str(self.log_file) if self.log_file else None,
            "verbose": self.verbose,
            "config_path": str(self.config_path) if self.config_path else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CLIRunConfig:
        """Создаёт конфигурацию из словаря.

        Args:
            data: Словарь с параметрами.

        Returns:
            Экземпляр CLIRunConfig.

        """
        return cls(
            urls=data.get("urls", []),
            cities=data.get("cities", []),
            categories=data.get("categories", []),
            output_dir=Path(data.get("output_dir", "./output")),
            output_file=data.get("output_file"),
            format=data.get("format", "csv"),
            parallel=data.get("parallel", False),
            max_workers=data.get("max_workers", 10),
            timeout=data.get("timeout", 300),
            log_level=data.get("log_level", "INFO"),
            log_file=Path(data["log_file"]) if data.get("log_file") else None,
            verbose=data.get("verbose", False),
            config_path=Path(data["config_path"]) if data.get("config_path") else None,
        )

    @classmethod
    def from_args(cls, args) -> CLIRunConfig:
        """Создаёт конфигурацию из аргументов командной строки.

        Args:
            args: Аргументы командной строки.

        Returns:
            Экземпляр CLIRunConfig.

        """
        return cls(
            urls=args.urls,
            cities=args.cities,
            categories=args.categories,
            output_dir=Path(args.output_dir) if hasattr(args, "output_dir") else Path("./output"),
            output_file=args.output_file,
            format=args.format,
            parallel=args.parallel,
            max_workers=args.max_workers,
            timeout=args.timeout,
            log_level=args.log_level,
            log_file=Path(args.log_file) if hasattr(args, "log_file") and args.log_file else None,
            verbose=args.verbose,
            config_path=Path(args.config) if hasattr(args, "config") and args.config else None,
        )


__all__ = ["CLIRunConfig"]
