"""Общие функции логирования для parser-2gis.

ISSUE-052: Вынесено из coordinator.py и parallel_parser.py для устранения
дублирования логики логирования завершения парсинга.

Пример использования:
    >>> from parser_2gis.utils.logging_common import log_parsing_completion
    >>> log_parsing_completion(
    ...     city_name="Москва",
    ...     category_name="Аптеки",
    ...     success=True,
    ...     duration=5.2,
    ... )
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_parsing_completion(
    city_name: str,
    category_name: str,
    success: bool,
    duration: float | None = None,
    result_path: str | None = None,
    extra_info: dict[str, Any] | None = None,
) -> None:
    """Логирует завершение парсинга одного URL.

    Общая функция для устранения дублирования между:
    - coordinator.py: логирование завершения парсинга
    - parallel_parser.py: логирование завершения парсинга

    Args:
        city_name: Название города.
        category_name: Название категории.
        success: True если парсинг успешен.
        duration: Длительность парсинга в секундах.
        result_path: Путь к файлу результата.
        extra_info: Дополнительная информация для логирования.

    """
    status = "успешно" if success else "ошибка"
    duration_str = f" ({duration:.2f} сек)" if duration is not None else ""
    path_str = f" → {result_path}" if result_path else ""

    message = (
        f"Завершён парсинг: {city_name} - {category_name} "
        f"[{status}]{duration_str}{path_str}"
    )

    if success:
        logger.info(message)
    else:
        logger.error(message)

    if extra_info:
        logger.debug("Дополнительная информация: %s", extra_info)


def log_parsing_summary(
    total: int,
    success: int,
    failed: int,
    skipped: int = 0,
    duration: float | None = None,
    cities: list[str] | None = None,
    categories_count: int | None = None,
) -> None:
    """Логирует сводку по парсингу.

    Args:
        total: Общее количество задач.
        success: Количество успешных.
        failed: Количество ошибок.
        skipped: Количество пропущенных.
        duration: Общая длительность в секундах.
        cities: Список городов.
        categories_count: Количество категорий.

    """
    duration_str = f"{duration:.2f} сек" if duration is not None else "N/A"
    cities_str = f", города: {cities}" if cities else ""
    cats_str = f", категорий: {categories_count}" if categories_count else ""

    logger.info(
        "Парсинг завершён. Всего: %d, Успешно: %d, Ошибок: %d, Пропущено: %d, "
        "Время: %s%s%s",
        total,
        success,
        failed,
        skipped,
        duration_str,
        cities_str,
        cats_str,
    )
