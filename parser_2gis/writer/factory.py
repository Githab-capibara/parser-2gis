"""Фабричный модуль writer.

Предоставляет фабричную функцию get_writer для создания экземпляра
файлового писателя в зависимости от формата (JSONWriter, CSVWriter, XLSXWriter).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .exceptions import WriterUnknownFileFormat
from .writers import CSVWriter, JSONWriter, XLSXWriter

if TYPE_CHECKING:
    from .options import WriterOptions
    from .writers.file_writer import FileWriter


def get_writer(
    file_path: str, file_format: str, writer_options: WriterOptions
) -> FileWriter:
    """Фабричная функция для создания писателя файлов.

    Args:
        file_path: Путь к результирующему файлу.
        file_format: Формат файла: `csv`, `xlsx` или `json`.
        writer_options: Опции писателя.

    Returns:
        Экземпляр файлового писателя.
    """
    if file_format == "json":
        return JSONWriter(file_path, writer_options)
    elif file_format == "csv":
        return CSVWriter(file_path, writer_options)
    elif file_format == "xlsx":
        return XLSXWriter(file_path, writer_options)

    raise WriterUnknownFileFormat(f"Неизвестный формат файла: {file_format}")
