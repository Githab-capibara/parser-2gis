"""Модуль конфигураций для парсера.

Предоставляет dataclass ParserRunConfig для группировки параметров
запуска парсера. Это устраняет нарушение Data Clumps
(группы одинаковых параметров в нескольких функциях).

Пример использования:
    >>> from parser_2gis.parser.config import ParserRunConfig
    >>> config = ParserRunConfig(
    ...     url="https://2gis.ru/moscow/search/cafe",
    ...     output_file="./output.csv",
    ...     max_records=1000,
    ... )
    >>> parser = MainParser(**config.to_parser_kwargs())
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


@dataclass
class ParserRunConfig:
    """Конфигурация для запуска парсера.

    Dataclass для группировки параметров парсера,
    устраняет нарушение Data Clumps (группы одинаковых параметров).

    Attributes:
        url: URL для парсинга.
        output_file: Путь к выходному файлу.
        output_format: Формат выходного файла (csv, xlsx, json).
        max_records: Максимальное количество записей для парсинга.
        use_gc: Использовать сборщик мусора.
        gc_pages_interval: Интервал запуска GC (в страницах).
        memory_threshold: Порог памяти в МБ для оптимизации.
        max_retries: Максимальное количество попыток.
        retry_delay_base: Базовая задержка между попытками.
        delay_between_clicks: Задержка между кликами (мс).

    Example:
        >>> from parser_2gis.parser.config import ParserRunConfig
        >>> cfg = ParserRunConfig(
        ...     url="https://2gis.ru/moscow/search/cafe",
        ...     output_file=Path("./output.csv"),
        ...     max_records=500,
        ...     use_gc=True,
        ... )
        >>> parser = MainParser(**cfg.to_parser_kwargs())

    """

    url: str
    output_file: Path
    output_format: Literal["csv", "xlsx", "json"] = "csv"
    max_records: int = 10000
    use_gc: bool = True
    gc_pages_interval: int = 5
    memory_threshold: int = 800
    max_retries: int = 3
    retry_delay_base: float = 1.0
    delay_between_clicks: int = 100
    skip_404_response: bool = True
    stop_on_first_404: bool = False
    max_consecutive_empty_pages: int = 3
    retry_on_network_errors: bool = True

    def to_parser_kwargs(self) -> dict[str, Any]:
        """Конвертирует конфигурацию в kwargs для ParserOptions.

        Returns:
            dict: Словарь с ключами: max_records, use_gc, gc_pages_interval,
            memory_threshold, max_retries, retry_delay_base, delay_between_clicks,
            skip_404_response, stop_on_first_404, max_consecutive_empty_pages,
            retry_on_network_errors.

        """
        return {
            "max_records": self.max_records,
            "use_gc": self.use_gc,
            "gc_pages_interval": self.gc_pages_interval,
            "memory_threshold": self.memory_threshold,
            "max_retries": self.max_retries,
            "retry_delay_base": self.retry_delay_base,
            "delay_between_clicks": self.delay_between_clicks,
            "skip_404_response": self.skip_404_response,
            "stop_on_first_404": self.stop_on_first_404,
            "max_consecutive_empty_pages": self.max_consecutive_empty_pages,
            "retry_on_network_errors": self.retry_on_network_errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParserRunConfig:
        """Создаёт конфигурацию из словаря.

        Args:
            data: Словарь с параметрами.

        Returns:
            Экземпляр ParserRunConfig.

        """
        return cls(
            url=data.get("url", ""),
            output_file=Path(data.get("output_file", "./output.csv")),
            output_format=data.get("output_format", "csv"),
            max_records=data.get("max_records", 10000),
            use_gc=data.get("use_gc", True),
            gc_pages_interval=data.get("gc_pages_interval", 5),
            memory_threshold=data.get("memory_threshold", 800),
            max_retries=data.get("max_retries", 3),
            retry_delay_base=data.get("retry_delay_base", 1.0),
            delay_between_clicks=data.get("delay_between_clicks", 100),
            skip_404_response=data.get("skip_404_response", True),
            stop_on_first_404=data.get("stop_on_first_404", False),
            max_consecutive_empty_pages=data.get("max_consecutive_empty_pages", 3),
            retry_on_network_errors=data.get("retry_on_network_errors", True),
        )


__all__ = ["ParserRunConfig"]
