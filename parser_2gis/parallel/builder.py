"""Builder для ParallelCityParser.

ISSUE 113: Добавляет паттерн Builder для создания ParallelCityParser
с использованием fluent interface вместо длинного списка параметров.

Пример использования:
    >>> from parser_2gis.parallel import ParallelCityParserBuilder
    >>> parser = (
    ...     ParallelCityParserBuilder(cities, categories)
    ...     .with_output_dir("./output")
    ...     .with_config(config)
    ...     .with_max_workers(5)
    ...     .with_timeout(1800)
    ...     .build()
    ... )
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from parser_2gis.constants import DEFAULT_TIMEOUT

if TYPE_CHECKING:
    from parser_2gis.config import Configuration

    from .parallel_parser import ParallelCityParser


class ParallelCityParserBuilder:
    """Builder для ParallelCityParser с fluent interface.

    ISSUE 113: Устраняет необходимость передавать много параметров в конструктор,
    позволяя пошагово конфигурировать парсер через цепочку вызовов.

    Example:
        >>> builder = ParallelCityParserBuilder(cities, categories)
        >>> builder = (
        ...     builder.with_output_dir("./output")
        ...     .with_config(config)
        ...     .with_max_workers(5)
        ...     .with_timeout(1800)
        ... )
        >>> parser = builder.build()

    """

    def __init__(self, cities: list[dict], categories: list[dict]) -> None:
        """Инициализирует builder с обязательными параметрами.

        Args:
            cities: Список городов для парсинга.
            categories: Список категорий для парсинга.

        """
        self._cities = cities
        self._categories = categories
        self._output_dir: str = "output"
        self._config: Configuration | None = None
        self._max_workers: int = 3
        self._timeout_per_url: int = DEFAULT_TIMEOUT

    def with_output_dir(self, output_dir: str) -> ParallelCityParserBuilder:
        """Устанавливает директорию вывода.

        Args:
            output_dir: Директория для сохранения результатов.

        Returns:
            Этот же экземпляр builder для цепочки вызовов.

        """
        self._output_dir = output_dir
        return self

    def with_config(self, config: Configuration) -> ParallelCityParserBuilder:
        """Устанавливает конфигурацию парсера.

        Args:
            config: Конфигурация парсера.

        Returns:
            Этот же экземпляр builder для цепочки вызовов.

        """
        self._config = config
        return self

    def with_max_workers(self, max_workers: int) -> ParallelCityParserBuilder:
        """Устанавливает максимальное количество рабочих потоков.

        Args:
            max_workers: Количество одновременных браузеров.

        Returns:
            Этот же экземпляр builder для цепочки вызовов.

        """
        self._max_workers = max_workers
        return self

    def with_timeout(self, timeout_per_url: int) -> ParallelCityParserBuilder:
        """Устанавливает таймаут на один URL в секундах.

        Args:
            timeout_per_url: Таймаут в секундах.

        Returns:
            Этот же экземпляр builder для цепочки вызовов.

        """
        self._timeout_per_url = timeout_per_url
        return self

    def build(self) -> ParallelCityParser:
        """Создаёт и возвращает экземпляр ParallelCityParser.

        Returns:
            Настроенный экземпляр ParallelCityParser.

        Raises:
            ValueError: Если не передана конфигурация.

        """
        from parser_2gis.parallel import ParallelCityParser

        if self._config is None:
            raise ValueError("Конфигурация обязательна. Используйте with_config().")

        return ParallelCityParser(
            cities=self._cities,
            categories=self._categories,
            output_dir=self._output_dir,
            config=self._config,
            max_workers=self._max_workers,
            timeout_per_url=self._timeout_per_url,
        )


__all__ = ["ParallelCityParserBuilder"]
