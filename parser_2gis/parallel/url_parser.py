"""
Модуль для генерации URL парсинга.

Предоставляет класс UrlParser для генерации всех URL для парсинга:
- Генерация URL по городам и категориям
- Валидация сгенерированных URL
- Обработка ошибок генерации
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from parser_2gis.config import Configuration

logger = logging.getLogger("parser_2gis.parallel.url_parser")


class UrlParser:
    """Генератор URL для параллельного парсинга.

    Отвечает за генерацию всех URL для парсинга на основе
    списка городов и категорий.

    Attributes:
        cities: Список городов для парсинга.
        categories: Список категорий для парсинга.
        config: Конфигурация парсера.
    """

    def __init__(self, cities: List[dict], categories: List[dict], config: "Configuration") -> None:
        """Инициализация генератора URL.

        Args:
            cities: Список городов для парсинга.
            categories: Список категорий для парсинга.
            config: Конфигурация парсера.
        """
        self.cities = cities
        self.categories = categories
        self.config = config

    def generate_all_urls(self) -> List[Tuple[str, str, str]]:
        """Генерирует все URL для парсинга.

        Returns:
            Список кортежей (url, category_name, city_name).
        """
        from parser_2gis.utils.url_utils import generate_category_url

        all_urls: List[Tuple[str, str, str]] = []

        for city in self.cities:
            for category in self.categories:
                try:
                    url = generate_category_url(city, category)
                    all_urls.append((url, category["name"], city["name"]))
                except (OSError, RuntimeError, TypeError, ValueError, MemoryError) as e:
                    logger.error(
                        "Ошибка генерации URL для %s - %s: %s", city["name"], category["name"], e
                    )
                    continue

        logger.info("Сгенерировано %d URL для парсинга", len(all_urls))
        return all_urls

    def get_url_count(self) -> int:
        """Возвращает общее количество URL для парсинга.

        Returns:
            Количество URL (города * категории).
        """
        return len(self.cities) * len(self.categories)

    def get_statistics(self) -> dict:
        """Возвращает статистику по URL.

        Returns:
            Словарь со статистикой.
        """
        return {
            "cities_count": len(self.cities),
            "categories_count": len(self.categories),
            "total_urls": self.get_url_count(),
        }
