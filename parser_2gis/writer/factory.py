"""Фабричный модуль writer.

Предоставляет фабричную функцию get_writer для создания экземпляра
файлового писателя в зависимости от формата (JSONWriter, CSVWriter, XLSXWriter).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .exceptions import WriterUnknownFileFormat
from .writers import CSVWriter, JSONWriter, XLSXWriter

if TYPE_CHECKING:
    from .options import WriterOptions
    from .writers.file_writer import FileWriter


def _validate_path_traversal(file_path: str) -> Path:
    """Валидирует путь к файлу для предотвращения path traversal атак.

    Args:
        file_path: Путь к файлу для валидации.

    Returns:
        Нормализованный абсолютный путь.

    Raises:
        ValueError: Если путь небезопасен или содержит traversal последовательности.
    """
    if not file_path:
        raise ValueError("Путь к файлу не может быть пустым")

    resolved_path = Path(file_path).resolve()

    if not resolved_path.is_absolute():
        raise ValueError(
            f"Относительные пути не поддерживаются: {file_path}. Используйте абсолютные пути."
        )

    path_parts = resolved_path.parts
    dangerous_patterns = {"..", "~", "$"}
    for part in path_parts:
        if any(pattern in str(part) for pattern in dangerous_patterns):
            if ".." in str(part):
                raise ValueError(
                    f"Path traversal атака обнаружена: {file_path}. "
                    "Символы '..' не допускаются в пути к файлу."
                )

    try:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        raise ValueError(f"Невозможно создать директорию для пути: {file_path}") from e

    return resolved_path


def get_writer(file_path: str, file_format: str, writer_options: WriterOptions) -> FileWriter:
    """Фабричная функция для создания писателя файлов.

    Args:
        file_path: Путь к результирующему файлу.
        file_format: Формат файла: `csv`, `xlsx` или `json`.
        writer_options: Опции писателя.

    Returns:
        Экземпляр файлового писателя.

    Raises:
        ValueError: Если путь небезопасен или обнаружена path traversal атака.
    """
    validated_path = _validate_path_traversal(file_path)

    if file_format == "json":
        return JSONWriter(str(validated_path), writer_options)
    elif file_format == "csv":
        return CSVWriter(str(validated_path), writer_options)
    elif file_format == "xlsx":
        return XLSXWriter(str(validated_path), writer_options)

    raise WriterUnknownFileFormat(f"Неизвестный формат файла: {file_format}")
