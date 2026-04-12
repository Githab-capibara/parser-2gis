"""Модуль консолидированной валидации путей для parser-2gis.

Объединяет функции валидации путей для предотвращения дублирования:
- validate_path_traversal: проверка на path traversal атаки
- validate_path_safety: полная проверка безопасности пути
- PathSafetyValidator: класс для валидации путей
- PathValidator: алиас для обратной совместимости (из path_validator.py)
- get_path_safety_validator: получение singleton экземпляра валидатора
- get_path_validator: алиас для обратной совместимости

ISSUE-055: Консолидировано с path_validator.py — PathValidator добавлен как алиас.

Пример использования:
    >>> from parser_2gis.validation.path_validation import validate_path_safety
    >>> validate_path_safety("/safe/path/file.txt")
    >>> validate_path_traversal("/safe/path/file.txt")
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import ClassVar

from parser_2gis.constants import MAX_PATH_LENGTH

logger = logging.getLogger(__name__)


class PathTraversalError(ValueError):
    """Исключение при обнаружении path traversal атаки.

    Выбрасывается когда путь содержит запрещённые символы или паттерны,
    указывающие на попытку выхода за пределы разрешённой директории.

    Example:
        >>> try:
        ...     validate_path_traversal("../etc/passwd")
        ... except PathTraversalError as e:
        ...     print(f"Path traversal обнаружена: {e}")

    """


class PathSafetyValidator:
    """Валидатор безопасности путей для parser-2gis.

    Отвечает за:
    - Проверку на запрещённые символы
    - Проверку максимальной длины
    - Разрешение символьных ссылок через realpath
    - Проверку нахождения в разрешённых директориях
    - Предотвращение path traversal атак

    Attributes:
        _allowed_base_dirs: Список разрешённых базовых директорий.

    Example:
        >>> validator = PathSafetyValidator()
        >>> validator.validate_traversal("/safe/path/file.txt")
        True
        >>> validator.validate_safety("/safe/output.csv", "output_path")

    """

    # Запрещённые символы в путях для предотвращения path traversal атак
    _FORBIDDEN_CHARS: ClassVar[list[str]] = [
        "..",
        "~",
        "$",
        "`",
        "|",
        ";",
        "&",
        ">",
        "<",
        "\\",
        "\n",
        "\r",
    ]

    # Максимальная длина пути для предотвращения переполнения буфера
    _MAX_PATH_LENGTH: int = MAX_PATH_LENGTH

    # Разрешённые базовые директории для записи
    _ALLOWED_BASE_DIRS: ClassVar[list[Path]] = [
        Path.cwd(),
        Path.home() / "parser-2gis",
        Path(tempfile.gettempdir()),
    ]

    def __init__(self, allowed_base_dirs: list[Path] | None = None) -> None:
        """Инициализирует валидатор путей.

        Args:
            allowed_base_dirs: Список разрешённых базовых директорий.
                              Если None, используются директории по умолчанию.

        """
        if allowed_base_dirs is not None:
            self._allowed_base_dirs = allowed_base_dirs
        else:
            self._allowed_base_dirs = self._ALLOWED_BASE_DIRS.copy()

    def validate_traversal(self, path: str) -> bool:
        """Проверяет путь на наличие path traversal атак.

        Args:
            path: Путь для валидации.

        Returns:
            True если путь безопасен.

        Raises:
            PathTraversalError: При обнаружении path traversal атаки.

        """
        if not path:
            return True

        # Проверка на запрещённые символы
        for forbidden_char in self._FORBIDDEN_CHARS:
            if forbidden_char in path:
                logger.warning(
                    "Path traversal атака обнаружена: путь содержит запрещённый символ '%s'",
                    forbidden_char,
                )
                msg = (
                    f"Путь содержит запрещённый символ: {forbidden_char!r}. "
                    "Path traversal атака обнаружена."
                )
                raise PathTraversalError(
                    msg
                )

        # Разрешаем путь через realpath для предотвращения symlink атак
        try:
            Path(path).resolve()
        except (OSError, RuntimeError) as fs_error:
            msg = f"Ошибка разрешения пути: {fs_error}"
            raise PathTraversalError(msg) from fs_error

        return True

    def validate_safety(self, path: str, path_name: str = "Путь") -> None:
        """Полная проверка безопасности пути.

        Args:
            path: Путь для валидации.
            path_name: Имя параметра для сообщений об ошибках.

        Raises:
            PathTraversalError: При обнаружении path traversal атаки.
            ValueError: При некорректном пути.
            OSError: При ошибке работы с файловой системой.

        """
        if not path:
            logger.warning("Получен пустой путь для валидации, параметр: %s", path_name)
            return

        # Проверка на path traversal
        self.validate_traversal(path)

        # Проверка длины пути
        if len(path) > self._MAX_PATH_LENGTH:
            msg = f"{path_name} превышает максимальную длину ({len(path)} > {self._MAX_PATH_LENGTH})"
            raise ValueError(
                msg
            )

        # Разрешаем путь через realpath для предотвращения symlink атак
        try:
            resolved_path = Path(path).resolve()
        except (OSError, RuntimeError) as fs_error:
            msg = f"Ошибка разрешения {path_name}: {fs_error}"
            raise OSError(msg) from fs_error

        # Проверка что путь находится в разрешённой директории
        is_allowed = any(
            str(resolved_path).startswith(str(allowed_dir))
            for allowed_dir in self._allowed_base_dirs
        )

        if not is_allowed:
            # Разрешаем запись в текущую рабочую директорию и её поддиректории
            if str(resolved_path).startswith(str(Path.cwd())):
                return

            msg = (
                f"{path_name} должен находиться в одной из разрешённых директорий: "
                f"{[str(d) for d in self._allowed_base_dirs]}"
            )
            raise ValueError(
                msg
            )

    def validate_multiple(self, paths: dict[str, str]) -> None:
        """Валидирует несколько путей одновременно.

        Args:
            paths: Словарь {имя_пути: значение_пути}.

        Raises:
            PathTraversalError: При обнаружении path traversal атаки.
            ValueError: При некорректном пути.
            OSError: При ошибке работы с файловой системой.

        """
        for path_name, path_value in paths.items():
            if path_value:
                self.validate_safety(path_value, path_name)


# Singleton экземпляр для глобального использования (используем список для избежания global)
_path_safety_validator: list[PathSafetyValidator | None] = [None]


def get_path_safety_validator() -> PathSafetyValidator:
    """Получает глобальный singleton экземпляр PathSafetyValidator.

    Использует lazy инициализацию для создания экземпляра при первом вызове.
    Все последующие вызовы возвращают один и тот же экземпляр.

    Returns:
        Singleton экземпляр PathSafetyValidator.

    Example:
        >>> validator = get_path_safety_validator()
        >>> validator.validate_safety("/tmp/output.txt", "output_path")

    """
    if _path_safety_validator[0] is None:
        _path_safety_validator[0] = PathSafetyValidator()
    if _path_safety_validator[0] is None:
        msg = "Не удалось инициализировать валидатор безопасности путей"
        raise RuntimeError(msg)
    return _path_safety_validator[0]


def validate_path_traversal(path: str) -> bool:
    """Проверяет путь на наличие path traversal атак.

    Функция-обёртка для удобной валидации. Использует singleton экземпляр
    PathSafetyValidator для проверки пути на запрещённые символы и паттерны.

    Args:
        path: Путь для валидации.

    Returns:
        True если путь безопасен.

    Raises:
        PathTraversalError: При обнаружении path traversal атаки.

    Example:
        >>> validate_path_traversal("/safe/path/file.txt")
        True
        >>> validate_path_traversal("../etc/passwd")  # Raises PathTraversalError

    """
    validator = get_path_safety_validator()
    return validator.validate_traversal(path)


def validate_path_safety(path: str, path_name: str = "Путь") -> None:
    """Выполняет полную проверку безопасности пути.

    Функция-обёртка для удобной валидации. Проверяет путь на:
    - Запрещённые символы
    - Path traversal атаки
    - Нахождение в разрешённых директориях

    Args:
        path: Путь для валидации.
        path_name: Имя параметра для сообщений об ошибках.

    Raises:
        PathTraversalError: При обнаружении path traversal атаки.
        ValueError: При некорректном пути.
        OSError: При ошибке работы с файловой системой.

    Example:
        >>> validate_path_safety("/safe/output.csv", "output_path")

    """
    validator = get_path_safety_validator()
    validator.validate_safety(path, path_name)


# Алиасы для обратной совместимости (ISSUE-055: из path_validator.py)
validate_path = validate_path_safety
PathValidator = PathSafetyValidator
get_path_validator = get_path_safety_validator


__all__ = [
    "PathSafetyValidator",
    "PathTraversalError",
    "PathValidator",
    "get_path_safety_validator",
    "get_path_validator",
    "validate_path",
    "validate_path_safety",
    "validate_path_traversal",
]
