"""Модуль CLI приложения.

Предоставляет функцию cli_app для запуска парсера в режиме командной строки:
- Настройка CLI логгера
- Запуск CLIRunner для обработки URL
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..logger import setup_cli_logger
from ..runner import CLIRunner

if TYPE_CHECKING:
    from ..config import Configuration


def cli_app(urls: list[str], output_path: str, format: str, config: Configuration) -> None:
    """Запускает парсер в режиме командной строки.

    Инициализирует CLI логгер, создаёт CLIRunner и запускает парсинг URL.

    Args:
        urls: Список URL для парсинга.
        output_path: Путь для сохранения результатов.
        format: Формат вывода данных (csv, json, xlsx).
        config: Конфигурация парсера.

    Пример:
        >>> from parser_2gis.config import Configuration
        >>> config = Configuration()
        >>> urls = ["https://2gis.ru/moscow"]
        >>> cli_app(urls, "./output", "csv", config)
    """
    setup_cli_logger(config.log)

    runner = CLIRunner(urls, output_path, format, config)
    runner.start()
