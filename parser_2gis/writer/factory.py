"""Фабричный модуль writer.

Предоставляет фабричную функцию get_writer для создания экземпляра
файлового писателя в зависимости от формата (JSONWriter, CSVWriter, XLSXWriter).

Использует Registry pattern для регистрации и получения writer классов.
Это позволяет добавлять новые форматы без модификации фабричной функции.

Пример регистрации нового writer:
    >>> from parser_2gis.writer.factory import register_writer, get_writer
    >>> @register_writer("xml")
    ... class XMLWriter(FileWriter):
    ...     pass
    >>> writer = get_writer("output.xml", "xml", options)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from parser_2gis.utils.path_utils import validate_path_traversal

from .exceptions import WriterUnknownFileFormat
from .writers import CSVWriter, JSONWriter, XLSXWriter
from .writers.file_writer import FileWriter

if TYPE_CHECKING:
    from .options import WriterOptions


# =============================================================================
# REGISTRY PATTERN ДЛЯ WRITERS
# =============================================================================

from collections.abc import Callable

WRITER_REGISTRY: dict[str, type[FileWriter]] = {}
"""Реестр зарегистрированных writer классов по формату файла."""


def register_writer(format_name: str) -> Callable[[type[FileWriter]], type[FileWriter]]:
    """Декоратор для регистрации writer класса в реестре.

    Args:
        format_name: Название формата (например, "json", "csv", "xlsx").

    Returns:
        Декоратор для регистрации класса.

    Raises:
        ValueError: Если format_name пустой или содержит недопустимые символы.

    Example:
        >>> @register_writer("xml")
        ... class XMLWriter(FileWriter):
        ...     pass

    """

    def decorator(cls: type[FileWriter]) -> type[FileWriter]:
        # Валидация format_name
        if not format_name or not format_name.strip():
            raise ValueError("Название формата не может быть пустым")

        # Проверка на допустимые символы (только буквы, цифры, дефис, подчёркивание)
        if not re.match(r"^[a-zA-Z0-9_-]+$", format_name):
            raise ValueError(
                f"Название формата содержит недопустимые символы: {format_name}. "
                "Разрешены только буквы, цифры, дефис и подчёркивание."
            )

        WRITER_REGISTRY[format_name.lower()] = cls
        return cls

    return decorator


def get_writer(file_path: str, file_format: str, writer_options: WriterOptions) -> FileWriter:
    """Фабричная функция для создания писателя файлов.

    Использует реестр для получения класса writer по формату файла.

    Args:
        file_path: Путь к результирующему файлу.
        file_format: Формат файла: `csv`, `xlsx` или `json`.
        writer_options: Опции писателя.

    Returns:
        Экземпляр файлового писателя.

    Raises:
        ValueError: Если путь небезопасен или обнаружена path traversal атака.
        WriterUnknownFileFormat: Если формат файла не зарегистрирован в реестре.

    Example:
        >>> writer = get_writer("output.json", "json", options)
        >>> writer = get_writer("output.csv", "csv", options)

    """
    validated_path = validate_path_traversal(file_path)

    # Получаем writer класс из реестра
    writer_cls = WRITER_REGISTRY.get(file_format.lower())
    if not writer_cls:
        raise WriterUnknownFileFormat(
            f"Неизвестный формат: {file_format}. "
            f"Зарегистрированные форматы: {', '.join(WRITER_REGISTRY.keys())}"
        )

    return writer_cls(str(validated_path), writer_options)


# =============================================================================
# РЕГИСТРАЦИЯ ВСТРОЕННЫХ WRITERS
# =============================================================================

# Регистрируем встроенные writer классы
register_writer("json")(JSONWriter)
register_writer("csv")(CSVWriter)
register_writer("xlsx")(XLSXWriter)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = ["WRITER_REGISTRY", "get_writer", "register_writer"]
