"""Модуль стратегий форматирования для CSVWriter.

Предоставляет классы-стратегии для форматирования данных CSV:
- BaseFormatter - базовый класс
- PhoneFormatter - форматирование телефонов
- SanitizeFormatter - санитизация данных
- ContactFormatter - форматирование контактов

ISSUE-005: Устранение нарушения OCP через стратегию.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod


class BaseFormatter(ABC):
    """Базовый класс для стратегий форматирования CSV.

    ISSUE-005: Стратегия для устранения нарушения OCP.
    Позволяет добавлять новые форматы без изменения CSVWriter.

    Example:
        >>> formatter = PhoneFormatter()
        >>> formatted = formatter.format("+7 (495) 123-45-67")
        >>> print(formatted)  # 84951234567

    """

    @abstractmethod
    def format(self, value: str) -> str:
        """Форматирует значение.

        Args:
            value: Исходное значение.

        Returns:
            Отформатированное значение.

        """
        pass


class PhoneFormatter(BaseFormatter):
    """Форматировщик номеров телефонов.

    Форматирует номера: замена +7 на 8, удаление нецифровых символов.

    Example:
        >>> formatter = PhoneFormatter()
        >>> formatter.format("+7 (495) 123-45-67")
        '84951234567'

    """

    def format(self, value: str) -> str:
        """Форматирует номер телефона.

        Args:
            value: Исходный номер телефона.

        Returns:
            Отформатированный номер (8 вместо +7, только цифры).

        """
        value = re.sub(r"[^0-9+]", "", value)
        if value.startswith("+7"):
            value = "8" + value[2:]
        return value


class SanitizeFormatter(BaseFormatter):
    """Форматировщик для санитизации CSV данных.

    D014: Защита от CSV injection и специальных символов.

    Example:
        >>> formatter = SanitizeFormatter()
        >>> formatter.format("=SUM(A1:A10)")
        "'=SUM(A1:A10)"

    """

    # Таблица санитизации для CSV данных
    _SANITIZE_TABLE = {
        '"': '""',  # Экранирование кавычек для CSV
        "\n": " ",  # Замена новых строк на пробелы
        "\r": "",  # Удаление carriage return
        "\t": " ",  # Замена табов на пробелы
        "\x00": "",  # Удаление null-символов для предотвращения CSV injection
    }

    # Опасные символы для CSV injection
    _DANGEROUS_CHARS = ("=", "+", "-", "@")

    def format(self, value: str) -> str:
        """Санитизирует значение для CSV.

        Args:
            value: Исходное строковое значение.

        Returns:
            Санитизированное значение безопасное для CSV.

        """
        if not isinstance(value, str):
            return value

        # Экранируем специальные символы CSV
        for char, replacement in self._SANITIZE_TABLE.items():
            value = value.replace(char, replacement)

        # D014: Защита от CSV injection
        if value and value[0] in self._DANGEROUS_CHARS:
            value = "'" + value

        return value


class ContactFormatter(BaseFormatter):
    """Форматировщик для контактов.

    Форматирует контакты с добавлением комментариев.

    Attributes:
        add_comments: Добавлять ли комментарии к контактам.

    Example:
        >>> formatter = ContactFormatter(add_comments=True)
        >>> formatter.format("test@example.com")
        'test@example.com'

    """

    def __init__(self, add_comments: bool = False) -> None:
        """Инициализирует ContactFormatter.

        Args:
            add_comments: Добавлять ли комментарии.

        """
        self._add_comments = add_comments

    def format(self, value: str, comment: str | None = None) -> str:
        """Форматирует контакт.

        Args:
            value: Значение контакта.
            comment: Комментарий к контакту.

        Returns:
            Отформатированный контакт с комментарием (если есть).

        """
        if self._add_comments and comment:
            return f"{value} ({comment})"
        return value


class TypeFormatter(BaseFormatter):
    """Форматировщик для типов объектов.

    Преобразует английские названия типов в русские.

    Example:
        >>> formatter = TypeFormatter()
        >>> formatter.format("parking")
        'Парковка'

    """

    # Отображение типов на русские названия
    _TYPE_NAMES = {
        "parking": "Парковка",
        "street": "Улица",
        "road": "Дорога",
        "crossroad": "Перекрёсток",
        "station": "Остановка",
    }

    def format(self, value: str) -> str:
        """Преобразует тип объекта.

        Args:
            value: Английское название типа.

        Returns:
            Русское название типа или оригинал.

        """
        return self._TYPE_NAMES.get(value, value)


class CompositeFormatter(BaseFormatter):
    """Композитный форматировщик для цепочки форматирования.

    Позволяет применять несколько форматировщиков последовательно.

    Attributes:
        formatters: Список форматировщиков.

    Example:
        >>> formatter = CompositeFormatter(
        ...     PhoneFormatter(),
        ...     SanitizeFormatter()
        ... )
        >>> formatter.format("+7 (495) 123-45-67")
        '84951234567'

    """

    def __init__(self, *formatters: BaseFormatter) -> None:
        """Инициализирует композитный форматировщик.

        Args:
            formatters: Форматировщики для применения.

        """
        self._formatters = formatters

    def format(self, value: str) -> str:
        """Применяет цепочку форматировщиков.

        Args:
            value: Исходное значение.

        Returns:
            Отформатированное значение.

        """
        result = value
        for formatter in self._formatters:
            result = formatter.format(result)
        return result


__all__ = [
    "BaseFormatter",
    "PhoneFormatter",
    "SanitizeFormatter",
    "ContactFormatter",
    "TypeFormatter",
    "CompositeFormatter",
]
