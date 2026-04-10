"""Модуль для объединения конфигураций.

Предоставляет класс ConfigMerger для безопасного объединения конфигураций
с проверкой на циклические ссылки и ограничением глубины рекурсии.

Пример использования:
    >>> from parser_2gis.config import Configuration
    >>> from parser_2gis.config.config_merger import ConfigMerger
    >>> config1 = Configuration()
    >>> config2 = Configuration()
    >>> ConfigMerger.merge(config1, config2)
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from parser_2gis.logger.logger import Logger


class ConfigMerger:
    """Сервис для объединения конфигураций.

    Реализует безопасное рекурсивное объединение Pydantic моделей
    с проверкой на циклические ссылки и ограничением глубины.

    Этот класс следует принципу единственной ответственности (SRP),
    выделяя логику merge из класса Configuration.

    Example:
        >>> ConfigMerger.merge(config1, config2)

    """

    @classmethod
    def merge(cls, target: BaseModel, source: BaseModel, max_depth: int = 20) -> None:
        """Объединяет конфигурации рекурсивно.

        Args:
            target: Целевая конфигурация для обновления.
            source: Исходная конфигурация с новыми значениями.
            max_depth: Максимальная глубина рекурсии (по умолчанию 20).

        Raises:
            RecursionError: При превышении максимальной глубины.

        Example:
            >>> ConfigMerger.merge(config1, config2)

        """
        visited_objects: set[int] = set()
        cls._merge_recursive(target, source, 0, max_depth, visited_objects)

    @classmethod
    def _merge_recursive(
        cls, target: BaseModel, source: BaseModel, depth: int, max_depth: int, visited: set[int],
    ) -> None:
        """Рекурсивно объединяет модели.

        Args:
            target: Целевая модель.
            source: Исходная модель.
            depth: Текущая глубина рекурсии.
            max_depth: Максимальная глубина.
            visited: Множество ID посещённых объектов.

        """
        if depth >= max_depth:
            raise RecursionError(f"Превышена максимальная глубина обработки ({max_depth})")

        source_id = id(source)
        if source_id in visited:
            cls._get_logger().warning(
                "Обнаружена циклическая ссылка на объект %s (id=%d). Пропускаем.",
                type(source).__name__,
                source_id,
            )
            return
        visited.add(source_id)

        if depth >= int(max_depth * 0.8):
            cls._get_logger().warning(
                "Внимание: глубина обработки достигла %d/%d (80%% от лимита)", depth, max_depth,
            )

        fields_set = cls._get_fields_set(source)

        for field in fields_set:
            source_value = getattr(source, field, None)

            if not isinstance(source_value, BaseModel):
                setattr(target, field, source_value)
            else:
                target_value = getattr(target, field, None)
                if target_value is None:
                    setattr(target, field, deepcopy(source_value))
                else:
                    cls._merge_recursive(target_value, source_value, depth + 1, max_depth, visited)

        visited.discard(source_id)

    @staticmethod
    def _get_fields_set(model: BaseModel) -> set[str]:
        """Получает набор установленных полей модели.

        Args:
            model: Pydantic модель.

        Returns:
            Набор имён установленных полей.

        """
        from parser_2gis.pydantic_compat import get_model_fields_set

        fields_set: set[str] | None = get_model_fields_set(model)
        return fields_set if fields_set else set()

    @staticmethod
    def _get_logger() -> Logger:
        """Получает логгер для предупреждений.

        Returns:
            Экземпляр логгера.

        """
        from parser_2gis.logger.logger import logger as lazy_logger

        return lazy_logger


__all__ = ["ConfigMerger"]
