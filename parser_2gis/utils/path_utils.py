"""Модуль утилит для валидации путей в parser-2gis.

Содержит функции для безопасной валидации путей к файлам и директориям.
Предотвращает path traversal атаки и обеспечивает централизованную валидацию:
- validate_path_safety: комплексная валидация пути
- validate_path_traversal: валидация с URL-decode и symlink проверкой
- _get_allowed_base_dirs: получение списка разрешённых директорий

Пример использования:
    >>> from parser_2gis.utils.path_utils import validate_path_safety, validate_path_traversal
    >>> validate_path_safety("/safe/path/file.txt", "output_path")
    >>> path = validate_path_traversal("/safe/path/file.txt")
"""

from __future__ import annotations

import tempfile
import threading
import unicodedata
import urllib.parse
from pathlib import Path

from parser_2gis.constants import FORBIDDEN_PATH_CHARS, MAX_PATH_LENGTH

# Whitelist разрешенных символов для путей
# Разрешаем только безопасные символы: буквы, цифры, _, -, ., /, \, пробел, кириллица
_ALLOWED_CHARS_ASCII = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-. /\\"
_ALLOWED_CHARS_CYRILLIC = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
_ALLOWED_PATH_PATTERN = frozenset(_ALLOWED_CHARS_ASCII + _ALLOWED_CHARS_CYRILLIC)

# Блокировка для thread-safe инициализации _allowed_base_dirs
_allowed_base_dirs_lock = threading.Lock()


def _get_allowed_base_dirs() -> list[Path]:
    """Получает список разрешённых базовых директорий (thread-safe singleton).

    Returns:
        Список Path объектов разрешённых директорий.

    """
    if not hasattr(_get_allowed_base_dirs, "_allowed_dirs"):
        import tempfile

        with _allowed_base_dirs_lock:
            if not hasattr(_get_allowed_base_dirs, "_allowed_dirs"):
                _get_allowed_base_dirs._allowed_dirs = [
                    Path.cwd(),
                    Path.home() / "parser-2gis",
                    Path(tempfile.gettempdir()),
                ]
    return _get_allowed_base_dirs._allowed_dirs


# =============================================================================
# ФУНКЦИИ ВАЛИДАЦИИ ПУТЕЙ
# =============================================================================


def _check_unicode_safety(path: str, path_name: str) -> None:
    """Проверяет Unicode символы на недопустимые комбинации.

    Args:
        path: Путь для проверки.
        path_name: Имя параметра для сообщений.

    Raises:
        ValueError: При обнаружении недопустимых Unicode символов.
    """
    for char in path:
        category = unicodedata.category(char)
        if category in ("Cc", "Cf") and char not in ("\n", "\r", "\t"):
            msg = (
                f"{path_name} содержит недопустимый Unicode символ: {char!r} "
                f"(категория: {category}, код: U+{ord(char):04X})"
            )
            raise ValueError(msg)


def _check_path_length(path: str, path_name: str) -> None:
    """Проверяет длину пути.

    Args:
        path: Путь для проверки.
        path_name: Имя параметра.

    Raises:
        ValueError: Если путь слишком длинный.
    """
    if len(path) > MAX_PATH_LENGTH:
        msg = f"{path_name} превышает максимальную длину ({len(path)} > {MAX_PATH_LENGTH})"
        raise ValueError(msg)


def _check_forbidden_chars(path: str, path_name: str) -> None:
    """Проверяет наличие запрещённых символов.

    Args:
        path: Путь для проверки.
        path_name: Имя параметра.

    Raises:
        ValueError: При наличии запрещённых символов.
    """
    for forbidden_char in FORBIDDEN_PATH_CHARS:
        if forbidden_char in path:
            msg = f"{path_name} содержит запрещённый символ: {forbidden_char!r}. Path traversal атаки запрещены."
            raise ValueError(msg)


def _check_symlink_safety(path_obj: Path, path_name: str, forbidden_dirs: set[str]) -> None:
    """Проверяет symlink на безопасность.

    Args:
        path_obj: Объект Path.
        path_name: Имя параметра.
        forbidden_dirs: Запрещённые директории.

    Raises:
        ValueError: При обнаружении небезопасных symlink.
    """
    temp_dir = tempfile.gettempdir()
    resolved = path_obj.resolve()
    if str(resolved) != str(path_obj) and path_obj.exists():
        for part_path in path_obj.parents:
            if part_path.is_symlink():
                target = part_path.resolve()
                target_str = str(target)
                if not target_str.startswith(temp_dir):
                    for forbidden_dir in forbidden_dirs:
                        if target_str == forbidden_dir or target_str.startswith(
                            forbidden_dir + "/",
                        ):
                            msg = (
                                f"{path_name} содержит symlink, ведущий в системную директорию: {part_path} -> {target}"
                            )
                            raise ValueError(msg)


def _check_allowed_directories(resolved_path: Path, path_name: str) -> None:
    """Проверяет что путь находится в разрешённых директориях.

    Args:
        resolved_path: Разрешённый путь.
        path_name: Имя параметра.

    Raises:
        ValueError: Если путь не в разрешённых директориях.
    """
    forbidden_dirs = {"/", "/etc", "/root", "/home"}
    temp_dir = tempfile.gettempdir()
    resolved_path_str = str(resolved_path)

    if not resolved_path_str.startswith(temp_dir):
        for forbidden_dir in forbidden_dirs:
            if resolved_path_str == forbidden_dir or resolved_path_str.startswith(
                forbidden_dir + "/",
            ):
                msg = (
                    f"{path_name} не может находиться в системной директории: {forbidden_dir}. "
                    f"Попытка записи в: {resolved_path_str}"
                )
                raise ValueError(msg)

    allowed_dirs = _get_allowed_base_dirs()
    is_allowed = any(str(resolved_path).startswith(str(allowed_dir)) for allowed_dir in allowed_dirs)
    if not is_allowed:
        msg = f"{path_name} должен находиться в одной из разрешённых директорий: {[str(d) for d in allowed_dirs]}"
        raise ValueError(msg)


def validate_path_safety(path: str, path_name: str = "Путь") -> None:
    """Валидирует путь на безопасность для предотвращения path traversal атак.

    Комплексная валидация путей:
    1. Проверка на запрещённые символы
    2. Проверка максимальной длины
    3. Разрешение символьных ссылок через realpath
    4. Проверка нахождения в разрешённых директориях
    5. Проверка на абсолютный путь
    6. Проверка запрещённых директорий (/, /etc, /root, /home)
    7. ISSUE-179: Проверка Unicode символов на недопустимые комбинации

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
        msg = f"{path_name} не может быть пустым"
        raise ValueError(msg)

    _check_unicode_safety(path, path_name)
    _check_path_length(path, path_name)
    _check_forbidden_chars(path, path_name)

    path_obj = Path(path)
    if not path_obj.is_absolute():
        msg = f"{path_name} должен быть абсолютным путём, получен относительный: {path}"
        raise ValueError(msg)

    try:
        resolved_path = path_obj.resolve()
    except (OSError, RuntimeError) as fs_error:
        msg = f"Ошибка разрешения {path_name}: {fs_error}"
        raise OSError(msg) from fs_error

    _check_symlink_safety(path_obj, path_name, {"/", "/etc", "/root", "/home"})
    _check_allowed_directories(resolved_path, path_name)


def validate_path_traversal(file_path: str) -> Path:
    """Валидирует путь к файлу для предотвращения path traversal атак.

    Комплексная валидация:
    1. URL-decode проверка перед валидацией для обнаружения encoded атак
    2. Unicode normalization для предотвращения атак через unicode
    3. Проверка на опасные паттерны
    4. Резолвинг symlink через Path.resolve()
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
        msg = "Путь к файлу не может быть пустым"
        raise ValueError(msg)

    # ИСПРАВЛЕНИЕ CRITICAL 1: Проверка encoded паттернов ДО декодирования
    # Это предотвращает атаки когда опасные паттерны скрыты в encoded форме
    dangerous_encoded_patterns = ["%2e%2e", "%2f", "%5c", "%00", "%25", "%2e", "%0a", "%0d"]
    for pattern in dangerous_encoded_patterns:
        if pattern.lower() in file_path.lower():
            msg = f"Path traversal атака обнаружена: {file_path}. Обнаружен encoded опасный паттерн: {pattern}"
            raise ValueError(msg)

    # ИСПРАВЛЕНИЕ HIGH 9: NFKC нормализация вместо NFC
    # NFKC обеспечивает более строгую нормализацию с канонической декомпозицией
    # Это предотвращает атаки через unicode-эквиваленты (например, fullwidth символы)
    try:
        normalized_input = unicodedata.normalize("NFKC", file_path)
    except (ValueError, TypeError, UnicodeDecodeError) as unicode_error:
        # ID:044: Добавлены детали unicode_error в сообщение
        msg = (
            f"Некорректный Unicode в пути к файлу: {file_path!r}. "
            f"Ошибка: {type(unicode_error).__name__}: {unicode_error}"
        )
        raise ValueError(msg) from unicode_error

    # ИСПРАВЛЕНИЕ CRITICAL 1: Whitelist проверка символов
    for char in normalized_input:
        if char not in _ALLOWED_PATH_PATTERN:
            msg = f"Path содержит запрещённый символ: {char!r} (код: U+{ord(char):04X}) в пути {file_path}"
            raise ValueError(msg)

    # ИСПРАВЛЕНИЕ CRITICAL 1: Многоуровневое декодирование с проверкой
    # Шаг 1: Многократное URL-decode до стабильного состояния
    # Это предотвращает атаки через двойное/тройное кодирование (%252e%252e -> %2e%2e -> ..)
    decoded_path = normalized_input
    # Оптимизация: ограничиваем разумным максимумом 3 итерации
    max_decode_iterations = 3
    decode_iteration = 0

    # ISSUE-180: Оптимизация URL-decode - кэширование предыдущего значения
    previous_path = None
    while decode_iteration < max_decode_iterations:
        previous_path = decoded_path
        try:
            decoded_path = urllib.parse.unquote(decoded_path)
        except (ValueError, TypeError, UnicodeDecodeError) as decode_error:
            msg = f"Некорректный путь к файлу: {file_path}"
            raise ValueError(msg) from decode_error

        # Если строка не изменилась - досрочный выход (оптимизация)
        if decoded_path == previous_path:
            break

        decode_iteration += 1

    # Проверка на бесконечное кодирование
    if decode_iteration >= max_decode_iterations and decoded_path != previous_path:
        msg = f"Path traversal атака обнаружена: {file_path}. Обнаружено многократное URL-кодирование (возможная атака)"
        raise ValueError(msg)

    # ИСПРАВЛЕНИЕ CRITICAL 1: Проверка на опасные паттерны ПОСЛЕ декодирования
    # Это второй уровень защиты на случай если атака прошла первый уровень
    dangerous_patterns: set[str] = {"..", "~", "$", "`", "|", ";", "&", ">", "<", "\n", "\r"}
    for pattern in dangerous_patterns:
        if pattern in decoded_path and ".." in pattern:
            msg = f"Path traversal атака обнаружена: {file_path}. Символы '..' не допускаются в пути к файлу."
            raise ValueError(msg)
        elif pattern in decoded_path:
            msg = f"Path содержит запрещённый символ: {pattern!r} в пути {file_path}"
            raise ValueError(msg)

    # Шаг 4: Резолвинг symlink через Path.resolve()
    try:
        resolved_path = Path(decoded_path).resolve()
    except (OSError, RuntimeError) as resolve_error:
        msg = f"Ошибка разрешения пути: {file_path}"
        raise ValueError(msg) from resolve_error

    # Шаг 5: Проверка что путь абсолютный
    if not resolved_path.is_absolute():
        msg = f"Относительные пути не поддерживаются: {file_path}. Используйте абсолютные пути."
        raise ValueError(msg)

    # Шаг 6: Дополнительная проверка частей пути
    path_parts = resolved_path.parts
    for part in path_parts:
        if ".." in str(part):
            msg = f"Path traversal атака обнаружена: {file_path}. Символы '..' найдены в части пути: {part}"
            raise ValueError(msg)

    # Шаг 7: Проверка возможности создания директории
    try:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        msg = f"Невозможно создать директорию для пути: {file_path}"
        raise ValueError(msg) from e

    return resolved_path


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "FORBIDDEN_PATH_CHARS",
    "_get_allowed_base_dirs",
    "validate_path_safety",
    "validate_path_traversal",
]
