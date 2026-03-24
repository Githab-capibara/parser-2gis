"""Фабричный модуль writer.

Предоставляет фабричную функцию get_writer для создания экземпляра
файлового писателя в зависимости от формата (JSONWriter, CSVWriter, XLSXWriter).
"""

from __future__ import annotations

import os
import unicodedata
import urllib.parse
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

    # Шаг 1: URL-decode проверка перед валидацией для обнаружения encoded атак
    try:
        decoded_path = urllib.parse.unquote(file_path)
        # Проверяем на наличие %2e%2e и другие encoded символы
        if decoded_path != file_path:
            # Путь был encoded - проверяем его на опасные паттерны
            dangerous_encoded_patterns = ["%2e%2e", "%2f", "%5c", "%00", "%25"]
            for pattern in dangerous_encoded_patterns:
                if pattern.lower() in file_path.lower():
                    raise ValueError(
                        f"Path traversal атака обнаружена: {file_path}. "
                        f"Обнаружен encoded опасный паттерн: {pattern}"
                    )
    except (ValueError, TypeError, UnicodeDecodeError) as decode_error:
        raise ValueError(f"Некорректный путь к файлу: {file_path}") from decode_error

    # Шаг 2: Unicode normalization для предотвращения атак через unicode
    try:
        normalized_path = unicodedata.normalize("NFC", decoded_path)
    except (ValueError, TypeError, UnicodeDecodeError) as unicode_error:
        raise ValueError(f"Некорректный Unicode в пути к файлу: {file_path}") from unicode_error

    # Шаг 3: Проверка на опасные паттерны в нормализованном пути
    dangerous_patterns = {"..", "~", "$", "`", "|", ";", "&", ">", "<", "\\", "\n", "\r"}
    for pattern in dangerous_patterns:
        if pattern in normalized_path:
            if ".." in pattern:
                raise ValueError(
                    f"Path traversal атака обнаружена: {file_path}. "
                    "Символы '..' не допускаются в пути к файлу."
                )
            raise ValueError(f"Path содержит запрещённый символ: {pattern!r} в пути {file_path}")

    # Шаг 4: Резолвинг symlink через os.path.realpath
    try:
        resolved_path = Path(normalized_path).resolve()
        # Используем realpath для резолвинга всех symlink
        resolved_path = Path(os.path.realpath(str(resolved_path)))
    except (OSError, RuntimeError) as resolve_error:
        raise ValueError(f"Ошибка разрешения пути: {file_path}") from resolve_error

    # Шаг 5: Проверка что путь абсолютный
    if not resolved_path.is_absolute():
        raise ValueError(
            f"Относительные пути не поддерживаются: {file_path}. Используйте абсолютные пути."
        )

    # Шаг 6: Дополнительная проверка частей пути
    path_parts = resolved_path.parts
    for part in path_parts:
        if ".." in str(part):
            raise ValueError(
                f"Path traversal атака обнаружена: {file_path}. "
                f"Символы '..' найдены в части пути: {part}"
            )

    # Шаг 7: Проверка возможности создания директории
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
