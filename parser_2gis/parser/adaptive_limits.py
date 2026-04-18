"""Модуль для адаптивного управления лимитами парсинга.

Этот модуль предоставляет логику для динамического определения оптимальных
лимитов пустых страниц и таймаутов в зависимости от размера города
и количества результатов.
"""

from __future__ import annotations

from typing import Any, ClassVar

from parser_2gis.logger import logger

# Константы
MIN_PAGES_FOR_ANALYSIS: int = 3
"""Минимальное количество страниц для анализа размера города."""

DEFAULT_TIMEOUT_MULTIPLIER: int = 10
"""Множитель для вычисления fallback таймаута до определения размера города."""

# Пороги классификации городов по количеству организаций
CITY_SIZE_SMALL_THRESHOLD: float = 10.0
"""Порог малого города (организаций <= 10)."""

CITY_SIZE_MEDIUM_THRESHOLD: float = 50.0
"""Порог среднего города (организаций <= 50)."""

CITY_SIZE_LARGE_THRESHOLD: float = 200.0
"""Порог крупного города (организаций <= 200)."""


class AdaptiveLimits:
    """Менеджер адаптивных лимитов для парсинга.

    Автоматически определяет размер города/категории и подстраивает
    лимиты пустых страниц для оптимизации скорости парсинга.
    """

    # Классификация городов по количеству организаций
    CITY_SIZE_CLASSIFICATION: ClassVar[dict[str, float]] = {
        "small": CITY_SIZE_SMALL_THRESHOLD,  # Маленький город: <= 10 организаций
        "medium": CITY_SIZE_MEDIUM_THRESHOLD,  # Средний город: <= 50 организаций
        "large": CITY_SIZE_LARGE_THRESHOLD,  # Крупный город: <= 200 организаций
        "huge": float("inf"),  # Огромный город: > 200 организаций
    }

    # Адаптивные лимиты пустых страниц для каждого класса
    ADAPTIVE_EMPTY_LIMITS: ClassVar[dict[str, int]] = {
        "small": 2,  # Для маленьких городов: сразу после 2 пустых
        "medium": 3,  # Для средних городов: после 3 пустых
        "large": 5,  # Для крупных городов: после 5 пустых
        "huge": 7,  # Для огромных городов: после 7 пустых
    }

    # Адаптивные таймауты для навигации (секунды)
    ADAPTIVE_TIMEOUTS: ClassVar[dict[str, int]] = {
        "small": 10,
        "medium": 20,
        "large": 30,
        "huge": 45,
    }

    def __init__(self, base_limit: int = 3) -> None:
        """Инициализирует менеджер адаптивных лимитов.

        Args:
            base_limit: Базовый лимит пустых страниц (по умолчанию 3).

        """
        self._base_limit = base_limit
        self._records_on_first_pages: list[int] = []
        self._city_size: str | None = None
        self._adaptive_limit = base_limit

        logger.debug("Инициализирован AdaptiveLimits с базовым лимитом: %d", base_limit)

    def add_records_count(self, count: int) -> None:
        """Добавляет количество записей на странице для анализа.

        Args:
            count: Количество записей на странице.

        Raises:
            ValueError: Если count отрицательный.

        """
        if count < 0:
            msg = f"Количество записей не может быть отрицательным: {count}"
            raise ValueError(msg)
        self._records_on_first_pages.append(count)
        logger.debug(
            "Добавлено записей: %d (всего записей: %d)",
            count,
            len(self._records_on_first_pages),
        )

        # Анализируем размер города после 3-5 страниц
        if len(self._records_on_first_pages) >= MIN_PAGES_FOR_ANALYSIS:
            self._determine_city_size()

    def _determine_city_size(self) -> None:
        """Определяет размер города по количеству записей.

        Анализирует накопленные данные о количестве записей и классифицирует
        город как small/medium/large/huge на основе пороговых значений.

        Returns:
            None. Устанавливает внутреннее состояние _city_size и _adaptive_limit.

        """
        if not self._records_on_first_pages:
            return

        # Вычисляем среднее количество записей на страницу
        avg_records = sum(self._records_on_first_pages) / len(self._records_on_first_pages)

        # Определяем класс города
        if avg_records <= self.CITY_SIZE_CLASSIFICATION["small"]:
            self._city_size = "small"
        elif avg_records <= self.CITY_SIZE_CLASSIFICATION["medium"]:
            self._city_size = "medium"
        elif avg_records <= self.CITY_SIZE_CLASSIFICATION["large"]:
            self._city_size = "large"
        else:
            self._city_size = "huge"

        # Устанавливаем адаптивный лимит
        self._adaptive_limit = self.ADAPTIVE_EMPTY_LIMITS[self._city_size]

        logger.info(
            "Определен размер города: %s (среднее записей: %.1f). Адаптивный лимит пустых страниц: %d",
            self._city_size,
            avg_records,
            self._adaptive_limit,
        )

    def get_adaptive_limit(self) -> int:
        """Возвращает адаптивный лимит пустых страниц.

        Returns:
            Адаптивный лимит пустых страниц. Возвращает базовый лимит,
            если город ещё не определён или недостаточно данных для анализа.

        """
        return self._adaptive_limit

    def get_adaptive_timeout(self) -> int:
        """Возвращает адаптивный таймаут для навигации.

        Returns:
            Адаптивный таймаут в секундах.

        """
        if self._city_size:
            return self.ADAPTIVE_TIMEOUTS[self._city_size]
        return self._base_limit * DEFAULT_TIMEOUT_MULTIPLIER  # Fallback до определения размера города

    def get_city_size(self) -> str | None:
        """Возвращает определенный размер города.

        Returns:
            Размер города ('small', 'medium', 'large', 'huge') или None.

        """
        return self._city_size

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику адаптивных лимитов.

        Returns:
            Словарь со статистикой.

        """
        return {
            "city_size": self._city_size,
            "base_limit": self._base_limit,
            "adaptive_limit": self._adaptive_limit,
            "records_on_first_pages": self._records_on_first_pages,
            "avg_records": (
                sum(self._records_on_first_pages) / len(self._records_on_first_pages)
                if self._records_on_first_pages
                else 0
            ),
        }

    def reset(self) -> None:
        """Сбрасывает состояние детектора для нового URL."""
        self._records_on_first_pages = []
        self._city_size = None
        self._adaptive_limit = self._base_limit
        logger.debug("AdaptiveLimits сброшен")
