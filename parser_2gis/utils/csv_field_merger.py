"""Утилита для слияния полей CSV файлов.

ISSUE 077: Создаёт CSVFieldMerger класс для:
- Общего слияния имён полей из нескольких CSV файлов
- Вставки колонки "Категория"
- Устранения дубликатов имён полей

Пример использования:
    >>> from parser_2gis.utils.csv_field_merger import CSVFieldMerger
    >>> merger = CSVFieldMerger()
    >>> fieldnames = merger.merge_fieldnames(
    ...     [["id", "name"], ["id", "name", "extra"]]
    ... )
    >>> # fieldnames: ["Категория", "id", "name", "extra"]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

CATEGORY_COLUMN_NAME = "Категория"
"""Имя колонки категории, добавляемой при слиянии."""


class CSVFieldMerger:
    """Класс для слияния полей CSV файлов.

    ISSUE 077: Объединяет общую логику слияния имён полей,
    вставки колонки категории и устранения дубликатов.

    Attributes:
        category_column: Имя колонки категории (по умолчанию "Категория").

    """

    def __init__(self, category_column: str = CATEGORY_COLUMN_NAME) -> None:
        """Инициализирует слияние полей CSV.

        Args:
            category_column: Имя колонки категории.

        """
        self._category_column = category_column

    def merge_fieldnames(self, all_fieldnames: list[list[str]]) -> list[str]:
        """Объединяет имена полей из нескольких CSV файлов.

        Собирает все уникальные имена полей из всех файлов,
        сохраняет порядок появления и добавляет колонку категории.

        Args:
            all_fieldnames: Список списков имён полей из каждого файла.

        Returns:
                Объединённый список имён полей с колонкой категории в начале.

        """
        seen: set[str] = set()
        merged: list[str] = []

        for fieldnames in all_fieldnames:
            for field in fieldnames:
                if field not in seen:
                    seen.add(field)
                    merged.append(field)

        # Добавляем колонку категории если её ещё нет
        if self._category_column not in seen:
            merged.insert(0, self._category_column)

        return merged

    def get_fieldnames_with_category(
        self, original_fieldnames: list[str], add_category: bool = True
    ) -> list[str]:
        """Возвращает имена полей с добавлением колонки категории.

        Args:
            original_fieldnames: Исходные имена полей.
            add_category: Добавить ли колонку категории.

        Returns:
            Список имён полей с категорией.

        """
        if not add_category:
            return list(original_fieldnames)

        result = list(original_fieldnames)
        if self._category_column not in result:
            result.insert(0, self._category_column)

        return result

    def deduplicate_fieldnames(self, fieldnames: list[str]) -> list[str]:
        """Устраняет дубликаты имён полей с сохранением порядка.

        Args:
            fieldnames: Список имён полей (возможно с дубликатами).

        Returns:
            Список уникальных имён полей.

        """
        seen: set[str] = set()
        result: list[str] = []

        for field in fieldnames:
            if field not in seen:
                seen.add(field)
                result.append(field)

        return result

    def add_category_to_row(self, row: dict[str, str], category_name: str) -> dict[str, str]:
        """Добавляет колонку категории к строке данных.

        Args:
            row: Словарь строки данных.
            category_name: Название категории.

        Returns:
            Новая строка с добавленной колонкой категории.

        """
        return {self._category_column: category_name, **row}

    @property
    def category_column(self) -> str:
        """Возвращает имя колонки категории."""
        return self._category_column


# Глобальный экземпляр для удобства использования
_field_merger = CSVFieldMerger()


def merge_fieldnames(all_fieldnames: list[list[str]]) -> list[str]:
    """Удобная функция для слияния имён полей.

    Args:
        all_fieldnames: Список списков имён полей.

    Returns:
        Объединённый список имён полей.

    """
    return _field_merger.merge_fieldnames(all_fieldnames)


def get_fieldnames_with_category(fieldnames: list[str], add_category: bool = True) -> list[str]:
    """Удобная функция для получения имён полей с категорией.

    Args:
        fieldnames: Исходные имена полей.
        add_category: Добавить ли колонку категории.

    Returns:
        Список имён полей с категорией.

    """
    return _field_merger.get_fieldnames_with_category(fieldnames, add_category)


__all__ = [
    "CATEGORY_COLUMN_NAME",
    "CSVFieldMerger",
    "get_fieldnames_with_category",
    "merge_fieldnames",
]
