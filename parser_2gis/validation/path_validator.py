"""Модуль валидации путей.

Содержит класс PathValidator для валидации путей и предотвращения
path traversal атак.

ISSUE-034: Реализует протокол PathValidatorProtocol из protocols.py.

Пример использования:
    >>> from parser_2gis.validation.path_validator import PathValidator, validate_path
    >>> validator = PathValidator()
    >>> validator.validate("/safe/path/file.txt")
    >>> validate_path("/safe/output.csv", "output_path")
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from parser_2gis.constants import MAX_PATH_LENGTH
from parser_2gis.protocols import PathValidatorProtocol

logger = logging.getLogger(__name__)


class PathValidator(PathValidatorProtocol):
    """Валидатор путей для предотвращения path traversal атак.

    ISSUE-034: Реализует протокол PathValidatorProtocol.

    Класс инкапсулирует логику валидации путей, обеспечивая:
    - Проверку на запрещённые символы
    - Проверку максимальной длины
    - Разрешение символьных ссылок через realpath
    - Проверку нахождения в разрешённых директориях

    Example:
        >>> validator = PathValidator()
        >>> validator.validate("/safe/path/file.txt")
        >>> validator.validate("../etc/passwd")  # Raises ValueError

    """

    # Запрещённые символы в путях для предотвращения path traversal атак
    _FORBIDDEN_CHARS: list[str] = ["..", "~", "$", "`", "|", ";", "&", ">", "<", "\\", "\n", "\r"]

    # Максимальная длина пути для предотвращения переполнения буфера
    _MAX_PATH_LENGTH: int = MAX_PATH_LENGTH

    # Разрешённые базовые директории для записи
    _ALLOWED_BASE_DIRS: list[Path] = [
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

    def validate(self, path: str, path_name: str = "Путь") -> None:
        """Валидирует путь на безопасность.

        Args:
            path: Путь для валидации.
            path_name: Имя параметра для сообщений об ошибках.

        Raises:
            ValueError: При обнаружении небезопасного пути.
            OSError: При ошибке работы с файловой системой.

        """
        if not path:
            logger.warning("Получен пустой путь для валидации, параметр: %s", path_name)
            return

        # Проверка длины пути
        if len(path) > self._MAX_PATH_LENGTH:
            raise ValueError(
                f"{path_name} превышает максимальную длину ({len(path)} > {self._MAX_PATH_LENGTH})"
            )

        # Проверка на запрещённые символы
        for forbidden_char in self._FORBIDDEN_CHARS:
            if forbidden_char in path:
                raise ValueError(
                    f"{path_name} содержит запрещённый символ: {forbidden_char!r}. "
                    "Path traversal атака обнаружена."
                )

        # Разрешаем путь через realpath для предотвращения symlink атак
        try:
            resolved_path = Path(path).resolve()
        except (OSError, RuntimeError) as fs_error:
            raise OSError(f"Ошибка разрешения {path_name}: {fs_error}") from fs_error

        # Проверка что путь находится в разрешённой директории
        is_allowed = any(
            str(resolved_path).startswith(str(allowed_dir))
            for allowed_dir in self._allowed_base_dirs
        )

        if not is_allowed:
            # Разрешаем запись в текущую рабочую директорию и её поддиректории
            if str(resolved_path).startswith(str(Path.cwd())):
                return

            raise ValueError(
                f"{path_name} должен находиться в одной из разрешённых директорий: "
                f"{[str(d) for d in self._allowed_base_dirs]}"
            )

    def validate_multiple(self, paths: dict[str, str]) -> None:
        """Валидирует несколько путей одновременно.

        Args:
            paths: Словарь {имя_пути: значение_пути}.

        Raises:
            ValueError: При обнаружении небезопасного пути.
            OSError: При ошибке работы с файловой системой.

        Example:
            >>> validator = PathValidator()
            >>> validator.validate_multiple({
            ...     "output_path": "/safe/output.csv",
            ...     "chrome_binary": "/usr/bin/google-chrome",
            ... })

        """
        for path_name, path_value in paths.items():
            if path_value:
                self.validate(path_value, path_name)


# Singleton экземпляр для глобального использования
_path_validator: PathValidator | None = None


def get_path_validator() -> PathValidator:
    """Получает глобальный экземпляр PathValidator.

    Returns:
        Экземпляр PathValidator для валидации путей.

    Example:
        >>> validator = get_path_validator()
        >>> validator.validate("/safe/path/file.txt")

    """
    global _path_validator
    if _path_validator is None:
        _path_validator = PathValidator()
    return _path_validator


def validate_path(path: str, path_name: str = "Путь") -> None:
    """Валидирует путь на безопасность.

    Функция-обёртка для удобной валидации путей.

    Args:
        path: Путь для валидации.
        path_name: Имя параметра для сообщений об ошибках.

    Raises:
        ValueError: При обнаружении небезопасного пути.
        OSError: При ошибке работы с файловой системой.

    Example:
        >>> validate_path("/safe/output.csv", "output_path")

    """
    validator = get_path_validator()
    validator.validate(path, path_name)


__all__ = ["PathValidator", "get_path_validator", "validate_path"]
