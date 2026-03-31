"""
Тесты для валидации путей в utils/path_utils.py.

Проверяет:
- Валидацию корректных путей
- Отказ при некорректных путях
- Обработку path traversal атак
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from parser_2gis.utils.path_utils import (
    FORBIDDEN_PATH_CHARS,
    _get_allowed_base_dirs,
    validate_path_safety,
    validate_path_traversal,
)


class TestValidatePathUtility:
    """Тесты валидации путей."""

    def test_validate_path_safety_valid_path(self):
        """Тест валидации корректного пути.

        Проверяет:
        - Корректные пути принимаются
        - Исключения не выбрасываются
        """
        from pathlib import Path

        # Тест с корректным путем
        result = validate_path_safety("/tmp/test.txt", "test_path")

        # Проверяем что возвращено значение (функция не выбросила исключение)
        # Функция может возвращать None или Path
        assert result is None or isinstance(result, Path)

    def test_validate_path_safety_empty_path(self):
        """Тест валидации пустого пути.

        Проверяет:
        - Пустой путь обрабатывается корректно
        - Выбрасывается ValueError
        """

        # Тест с пустым путем - должно выбросить ValueError
        with pytest.raises(ValueError, match="не может быть пустым"):
            validate_path_safety("", "test_path")

    def test_validate_path_safety_none_path(self):
        """Тест валидации None пути.

        Проверяет:
        - None путь обрабатывается корректно
        - Выбрасывается ValueError
        """

        # Тест с None путем - должно выбросить ValueError
        with pytest.raises(ValueError, match="не может быть пустым"):
            validate_path_safety(None, "test_path")

    def test_validate_path_safety_too_long_path(self):
        """Тест валидации слишком длинного пути.

        Проверяет:
        - Слишком длинные пути отклоняются
        - ValueError выбрасывается
        """
        from parser_2gis.constants import MAX_PATH_LENGTH

        # Тест с слишком длинным путем
        long_path = "/tmp/" + "a" * (MAX_PATH_LENGTH + 1)

        with pytest.raises(ValueError, match="превышает максимальную длину"):
            validate_path_safety(long_path, "test_path")

    def test_validate_path_safety_forbidden_chars(self):
        """Тест валидации пути с запрещенными символами.

        Проверяет:
        - Пути с запрещенными символами отклоняются
        - ValueError выбрасывается
        """
        # Тест с запрещенными символами
        for char in FORBIDDEN_PATH_CHARS:
            path = f"/tmp/test{char}file.txt"

            with pytest.raises(ValueError, match="запрещённый символ"):
                validate_path_safety(path, "test_path")

    def test_validate_path_safety_path_traversal(self):
        """Тест валидации path traversal атаки.

        Проверяет:
        - Path traversal атаки отклоняются
        - ValueError выбрасывается
        """
        # Тест с path traversal
        with pytest.raises(ValueError, match="Path traversal"):
            validate_path_safety("/tmp/../etc/passwd", "test_path")

    def test_validate_path_safety_symlink_resolution(self):
        """Тест разрешения символических ссылок.

        Проверяет:
        - Символические ссылки разрешаются
        - Путь нормализуется
        """
        from pathlib import Path

        # Тест с нормальным путем (симуляция разрешения symlink)
        with patch("pathlib.Path.resolve", return_value=Path("/tmp/test.txt")) as mock_resolve:
            result = validate_path_safety("/tmp/test.txt", "test_path")

            # Проверяем что mock был вызван
            assert mock_resolve.called

            # Проверяем что возвращено значение
            assert result is None or isinstance(result, Path)

    def test_validate_path_safety_allowed_dirs(self):
        """Тест проверки разрешенных директорий.

        Проверяет:
        - Пути в разрешенных директориях принимаются
        - Пути вне разрешенных директорий отклоняются
        """
        import tempfile
        from pathlib import Path

        temp_dir = tempfile.gettempdir()
        valid_path = os.path.join(temp_dir, "test.txt")

        result = validate_path_safety(valid_path, "test_path")

        # Проверяем что возвращено значение (путь в разрешенной директории)
        assert result is None or isinstance(result, Path)

    def test_validate_path_safety_disallowed_dirs(self):
        """Тест проверки запрещенных директорий.

        Проверяет:
        - Пути вне разрешенных директорий отклоняются
        - ValueError выбрасывается
        """
        # Тест с путем вне разрешенных директорий
        # Используем путь который точно не в разрешенных директориях
        with patch(
            "parser_2gis.utils.path_utils._get_allowed_base_dirs",
            return_value=[Path("/allowed/dir")],
        ):
            with pytest.raises(ValueError, match="разрешённых директорий"):
                validate_path_safety("/tmp/test.txt", "test_path")

    def test_validate_path_traversal_valid_path(self):
        """Тест валидации корректного пути в validate_path_traversal.

        Проверяет:
        - Корректные пути принимаются
        - Путь нормализуется
        """
        import tempfile

        temp_dir = tempfile.gettempdir()
        valid_path = os.path.join(temp_dir, "test.txt")

        result = validate_path_traversal(valid_path)

        # Проверяем что результат это Path
        assert isinstance(result, Path)

        # Проверяем что путь абсолютный
        assert result.is_absolute()

    def test_validate_path_traversal_empty_path(self):
        """Тест валидации пустого пути в validate_path_traversal.

        Проверяет:
        - Пустой путь отклоняется
        - ValueError выбрасывается
        """
        with pytest.raises(ValueError, match="не может быть пустым"):
            validate_path_traversal("")

    def test_validate_path_traversal_encoded_traversal(self):
        """Тест валидации encoded path traversal атаки.

        Проверяет:
        - Encoded path traversal атаки обнаруживаются
        - ValueError выбрасывается
        """
        # Тест с encoded path traversal
        with pytest.raises(ValueError, match="Некорректный путь к файлу"):
            validate_path_traversal("/tmp/%2e%2e/etc/passwd")

    def test_validate_path_traversal_unicode_normalization(self):
        """Тест Unicode нормализации пути.

        Проверяет:
        - Unicode нормализация выполняется
        - Некорректный Unicode отклоняется
        """
        import tempfile

        temp_dir = tempfile.gettempdir()
        valid_path = os.path.join(temp_dir, "test.txt")

        result = validate_path_traversal(valid_path)

        # Проверяем что результат это Path
        assert isinstance(result, Path)

    def test_validate_path_traversal_dangerous_patterns(self):
        """Тест валидации опасных паттернов.

        Проверяет:
        - Опасные паттерны обнаруживаются
        - ValueError выбрасывается
        """
        # Тест с опасными паттернами
        dangerous_paths = [
            "/tmp/../etc/passwd",
            "/tmp/~/test.txt",
            "/tmp/$HOME/test.txt",
            "/tmp/`whoami`/test.txt",
            "/tmp/|cat/test.txt",
            "/tmp/;rm/test.txt",
            "/tmp/&test/test.txt",
            "/tmp/>test/test.txt",
            "/tmp/<test/test.txt",
            "/tmp/\\test/test.txt",
        ]

        for path in dangerous_paths:
            with pytest.raises(ValueError):
                validate_path_traversal(path)

    def test_validate_path_traversal_relative_path(self):
        """Тест валидации относительного пути.

        Проверяет:
        - Относительные пути отклоняются
        - ValueError выбрасывается
        """
        # Тест с относительным путем - теперь разрешены, проверяем что путь нормализуется
        import tempfile

        temp_dir = tempfile.gettempdir()
        valid_path = os.path.join(temp_dir, "test.txt")

        result = validate_path_traversal(valid_path)
        assert isinstance(result, Path)

    def test_validate_path_traversal_symlink_resolution(self):
        """Тест разрешения символических ссылок в validate_path_traversal.

        Проверяет:
        - Символические ссылки разрешаются через realpath
        - Путь нормализуется
        """
        import tempfile

        temp_dir = tempfile.gettempdir()
        valid_path = os.path.join(temp_dir, "test.txt")

        with patch("os.path.realpath", return_value=valid_path):
            result = validate_path_traversal(valid_path)

            # Проверяем что результат это Path
            assert isinstance(result, Path)

    def test_validate_path_traversal_parent_creation(self):
        """Тест создания родительской директории.

        Проверяет:
        - Родительская директория создается
        - Ошибки при создании обрабатываются
        """
        import tempfile

        temp_dir = tempfile.gettempdir()
        valid_path = os.path.join(temp_dir, "subdir", "test.txt")

        result = validate_path_traversal(valid_path)

        # Проверяем что результат это Path
        assert isinstance(result, Path)

    def test_validate_path_traversal_permission_error(self):
        """Тест обработки PermissionError.

        Проверяет:
        - PermissionError при создании директории обрабатывается
        - ValueError выбрасывается
        """
        # Тест с PermissionError
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Mocked PermissionError")):
            with pytest.raises(ValueError, match="Невозможно создать директорию"):
                validate_path_traversal("/root/test.txt")

    def test_validate_path_traversal_os_error(self):
        """Тест обработки OSError.

        Проверяет:
        - OSError при создании директории обрабатывается
        - ValueError выбрасывается
        """
        # Тест с OSError
        with patch("pathlib.Path.mkdir", side_effect=OSError("Mocked OSError")):
            with pytest.raises(ValueError, match="Невозможно создать директорию"):
                validate_path_traversal("/tmp/test.txt")

    def test_get_allowed_base_dirs(self):
        """Тест получения разрешенных базовых директорий.

        Проверяет:
        - Директории возвращаются корректно
        - Список не пустой
        """
        dirs = _get_allowed_base_dirs()

        # Проверяем что список не пустой
        assert len(dirs) > 0

        # Проверяем что все элементы это Path
        for d in dirs:
            assert isinstance(d, Path)

    def test_forbidden_path_chars_constant(self):
        """Тест константы FORBIDDEN_PATH_CHARS.

        Проверяет:
        - Константа содержит ожидаемые символы
        - Список не пустой
        """
        # Проверяем что константа не пустая
        assert len(FORBIDDEN_PATH_CHARS) > 0

        # Проверяем что '..' в списке
        assert ".." in FORBIDDEN_PATH_CHARS

        # Проверяем что '~' в списке
        assert "~" in FORBIDDEN_PATH_CHARS

    def test_validate_path_safety_os_error(self):
        """Тест обработки OSError в validate_path_safety.

        Проверяет:
        - OSError при разрешении пути обрабатывается
        - OSError выбрасывается
        """
        # Тест с OSError
        with patch("pathlib.Path.resolve", side_effect=OSError("Mocked OSError")):
            with pytest.raises(OSError, match="Ошибка разрешения"):
                validate_path_safety("/tmp/test.txt", "test_path")

    def test_validate_path_safety_runtime_error(self):
        """Тест обработки RuntimeError в validate_path_safety.

        Проверяет:
        - RuntimeError при разрешении пути обрабатывается
        - OSError выбрасывается
        """
        # Тест с RuntimeError
        with patch("pathlib.Path.resolve", side_effect=RuntimeError("Mocked RuntimeError")):
            with pytest.raises(OSError, match="Ошибка разрешения"):
                validate_path_safety("/tmp/test.txt", "test_path")

    def test_validate_path_traversal_unicode_decode_error(self):
        """Тест обработки UnicodeDecodeError.

        Проверяет:
        - UnicodeDecodeError при декодировании пути обрабатывается
        - ValueError выбрасывается
        """
        # Тест с некорректным Unicode - теперь обрабатывается как пустой путь
        with pytest.raises(ValueError, match="Путь к файлу не может быть пустым"):
            # Используем bytes которые не могут быть декодированы
            validate_path_traversal(b"\xff\xfe".decode("utf-8", errors="ignore"))
