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
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from parser_2gis.utils.path_utils import validate_path_traversal

from .exceptions import WriterUnknownFileFormat
from .writers import CSVWriter, JSONWriter, XLSXWriter
from .writers.file_writer import FileWriter

if TYPE_CHECKING:
    from .options import WriterOptions


# =============================================================================
# WRITER REGISTRY CLASS (ISSUE 065: Инкапсуляция реестра писателей)
# =============================================================================


class WriterRegistry:
    """Реестр писателей с инкапсуляцией.

    ISSUE 065: Оборачивает WRITER_REGISTRY в класс с надлежащей инкапсуляцией.
    """

    def __init__(self) -> None:
        """Инициализирует реестр писателей."""
        self._registry: dict[str, type[FileWriter]] = {}
        self._lock = threading.Lock()

    def register(self, format_name: str, writer_cls: type[FileWriter]) -> None:
        """Регистрирует класс писателя в реестре.

        Args:
            format_name: Название формата (например, "json", "csv", "xlsx").
            writer_cls: Класс писателя.

        Raises:
            ValueError: Если format_name пустой или содержит недопустимые символы.

        """
        if not format_name or not format_name.strip():
            msg = "Название формата не может быть пустым"
            raise ValueError(msg)

        if not re.match(r"^[a-zA-Z0-9_-]+$", format_name):
            msg = (
                f"Название формата содержит недопустимые символы: {format_name}. "
                "Разрешены только буквы, цифры, дефис и подчёркивание."
            )
            raise ValueError(
                msg
            )

        with self._lock:
            self._registry[format_name.lower()] = writer_cls

    def unregister(self, format_name: str) -> None:
        """Удаляет формат из реестра.

        Args:
            format_name: Название формата для удаления.

        """
        with self._lock:
            self._registry.pop(format_name.lower(), None)

    def get_writer(self, format_name: str) -> type[FileWriter] | None:
        """Получает класс писателя по формату.

        Args:
            format_name: Название формата.

        Returns:
            Класс писателя или None если не найден.

        """
        with self._lock:
            return self._registry.get(format_name.lower())

    def get_registry(self) -> dict[str, type[FileWriter]]:
        """Возвращает копию реестра.

        Returns:
            Словарь {формат: класс_писателя}.

        """
        with self._lock:
            return self._registry.copy()

    def clear(self) -> None:
        """Очищает реестр."""
        with self._lock:
            self._registry.clear()

    def has_format(self, format_name: str) -> bool:
        """Проверяет наличие формата в реестре.

        Args:
            format_name: Название формата.

        Returns:
            True если формат зарегистрирован.

        """
        with self._lock:
            return format_name.lower() in self._registry


# Глобальный экземпляр реестра для обратной совместимости
_writer_registry = WriterRegistry()

# Алиас для обратной совместимости
WRITER_REGISTRY = _writer_registry._registry


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
        """Декоратор для регистрации формата записи."""
        _writer_registry.register(format_name, cls)
        return cls

    return decorator


def _detect_format_from_extension(file_path: str | Path) -> str | None:
    """Автоматически определяет формат файла по расширению.

    ISSUE 079: Поддержка автоопределения формата из расширения файла.

    Args:
        file_path: Путь к файлу.

    Returns:
        Название формата или None если не определён.

    """
    path = Path(file_path)
    ext = path.suffix.lower().lstrip(".")

    # Маппинг расширений на форматы
    extension_map = {"json": "json", "csv": "csv", "xlsx": "xlsx", "xls": "xlsx"}

    return extension_map.get(ext)


def get_writer(
    file_path: str | Path,
    file_format: str | None = None,
    writer_options: WriterOptions | None = None,
) -> FileWriter:
    """Фабричная функция для создания писателя файлов.

    Использует реестр для получения класса writer по формату файла.
    ISSUE 079: Поддерживает автоопределение формата из расширения файла.

    Args:
        file_path: Путь к результирующему файлу.
        file_format: Формат файла: `csv`, `xlsx` или `json`.
                     Если None, определяется автоматически из расширения.
        writer_options: Опции писателя.

    Returns:
        Экземпляр файлового писателя.

    Raises:
        ValueError: Если путь небезопасен или обнаружена path traversal атака.
        WriterUnknownFileFormat: Если формат файла не зарегистрирован в реестре.

    Example:
        >>> writer = get_writer("output.json", "json", options)
        >>> writer = get_writer("output.csv", "csv", options)
        >>> # Автоопределение формата (ISSUE 079)
        >>> writer = get_writer("output.json", writer_options=options)

    """
    validated_path = validate_path_traversal(str(file_path))

    # ISSUE 079: Автоопределение формата из расширения
    if file_format is None:
        detected_format = _detect_format_from_extension(validated_path)
        if detected_format is None:
            msg = (
                f"Не удалось определить формат из расширения файла: {validated_path}. "
                f"Укажите формат явно или используйте поддерживаемые расширения: "
                f"{', '.join(_writer_registry.get_registry().keys())}"
            )
            raise WriterUnknownFileFormat(
                msg
            )
        file_format = detected_format

    if writer_options is None:
        from .options import WriterOptions

        writer_options = WriterOptions()

    # Получаем writer класс из реестра
    writer_cls = _writer_registry.get_writer(file_format.lower())
    if not writer_cls:
        msg = (
            f"Неизвестный формат: {file_format}. "
            f"Зарегистрированные форматы: {', '.join(_writer_registry.get_registry().keys())}"
        )
        raise WriterUnknownFileFormat(
            msg
        )

    return writer_cls(str(validated_path), writer_options)


def get_writer_registry() -> WriterRegistry:
    """Возвращает экземпляр реестра писателей.

    Returns:
        Экземпляр WriterRegistry.

    """
    return _writer_registry


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

__all__ = [
    "WRITER_REGISTRY",
    "WriterRegistry",
    "_detect_format_from_extension",
    "get_writer",
    "get_writer_registry",
    "register_writer",
]
