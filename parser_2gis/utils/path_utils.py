"""
Модуль утилит для валидации путей.

Содержит функции для безопасной валидации путей к файлам и директориям.
Предотвращает path traversal атаки и обеспечивает централизованную валидацию.

Пример использования:
    >>> from parser_2gis.utils.path_utils import validate_path_safety, validate_path_traversal
    >>> validate_path_safety("/safe/path/file.txt", "output_path")
    >>> path = validate_path_traversal("/safe/path/file.txt")
"""

from __future__ import annotations

import os
import unicodedata
import urllib.parse
from pathlib import Path
from typing import List, Optional, Set

from parser_2gis.constants import MAX_PATH_LENGTH

# =============================================================================
# КОНСТАНТЫ БЕЗОПАСНОСТИ
# =============================================================================

# Запрещённые символы в путях для предотвращения path traversal атак
FORBIDDEN_PATH_CHARS: List[str] = ["..", "~", "$", "`", "|", ";", "&", ">", "<", "\\", "\n", "\r"]

# Разрешённые базовые директории для записи
# ОБОСНОВАНИЕ: Используем tempfile.gettempdir() вместо hardcoded /tmp для кроссплатформенности
# - Unix: /tmp
# - macOS: /var/folders/...
# - Windows: C:\Users\...\AppData\Local\Temp
_ALLOWED_BASE_DIRS: Optional[List[Path]] = None


def _get_allowed_base_dirs() -> List[Path]:
    """Получает список разрешённых базовых директорий.

    Returns:
        Список Path объектов разрешённых директорий.
    """
    global _ALLOWED_BASE_DIRS
    if _ALLOWED_BASE_DIRS is None:
        import tempfile

        _ALLOWED_BASE_DIRS = [Path.cwd(), Path.home() / "parser-2gis", Path(tempfile.gettempdir())]
    return _ALLOWED_BASE_DIRS


# =============================================================================
# ФУНКЦИИ ВАЛИДАЦИИ ПУТЕЙ
# =============================================================================


def validate_path_safety(path: str, path_name: str = "Путь") -> None:
    """Валидирует путь на безопасность для предотвращения path traversal атак.

    Комплексная валидация путей:
    1. Проверка на запрещённые символы
    2. Проверка максимальной длины
    3. Разрешение символьных ссылок через realpath
    4. Проверка нахождения в разрешённых директориях

    Args:
        path: Путь для валидации.
        path_name: Имя параметра для сообщений об ошибках.

    Raises:
        ValueError: При обнаружении небезопасного пути.
        OSError: При ошибке работы с файловой системой.

    Example:
        >>> validate_path_safety("/tmp/output.txt", "output_path")
        >>> validate_path_safety("../etc/passwd", "output_path")  # Raises ValueError
    """
    if not path:
        return

    # Проверка длины пути
    if len(path) > MAX_PATH_LENGTH:
        raise ValueError(
            f"{path_name} превышает максимальную длину ({len(path)} > {MAX_PATH_LENGTH})"
        )

    # Проверка на запрещённые символы
    for forbidden_char in FORBIDDEN_PATH_CHARS:
        if forbidden_char in path:
            raise ValueError(
                f"{path_name} содержит запрещённый символ: {forbidden_char!r}. "
                "Path traversal атаки запрещены."
            )

    # Разрешаем путь через realpath для предотвращения symlink атак
    try:
        resolved_path = Path(path).resolve()
    except (OSError, RuntimeError) as fs_error:
        raise OSError(f"Ошибка разрешения {path_name}: {fs_error}") from fs_error

    # Проверка что путь находится в разрешённой директории
    # Это предотвращает запись в системные директории
    allowed_dirs = _get_allowed_base_dirs()
    is_allowed = any(
        str(resolved_path).startswith(str(allowed_dir)) for allowed_dir in allowed_dirs
    )

    if not is_allowed:
        raise ValueError(
            f"{path_name} должен находиться в одной из разрешённых директорий: "
            f"{[str(d) for d in allowed_dirs]}"
        )


def validate_path_traversal(file_path: str) -> Path:
    """Валидирует путь к файлу для предотвращения path traversal атак.

    Комплексная валидация:
    1. URL-decode проверка перед валидацией для обнаружения encoded атак
    2. Unicode normalization для предотвращения атак через unicode
    3. Проверка на опасные паттерны
    4. Резолвинг symlink через os.path.realpath
    5. Проверка что путь абсолютный
    6. Дополнительная проверка частей пути
    7. Проверка возможности создания директории

    Args:
        file_path: Путь к файлу для валидации.

    Returns:
        Нормализованный абсолютный путь.

    Raises:
        ValueError: Если путь небезопасен или содержит traversal последовательности.

    Example:
        >>> path = validate_path_traversal("/tmp/output.txt")
        >>> print(path)
        /tmp/output.txt
        >>> validate_path_traversal("../etc/passwd")  # Raises ValueError
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
    dangerous_patterns: Set[str] = {"..", "~", "$", "`", "|", ";", "&", ">", "<", "\\", "\n", "\r"}
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


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "validate_path_safety",
    "validate_path_traversal",
    "FORBIDDEN_PATH_CHARS",
    "_get_allowed_base_dirs",
]
